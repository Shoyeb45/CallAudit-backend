import logging

from fastapi import HTTPException, status, Response
from core.jwt_util import get_jwt_util
from features.manager.repository import ManagerRepository
from config import get_jwt_settings
from features.auditor.schemas import LoginSchema
from features.manager.schemas import (
    AuditorAnalyticsResponse,
    CounsellorAnalysisResponse,
    ManagerAnalyticsResponse,
)
from models import Manager

logger = logging.getLogger(__name__)


class ManagerService:
    def __init__(self, repo: ManagerRepository):
        self.repo = repo
        self.jwt_util = get_jwt_util()

    def login_manager(
        self, email: str, password: str, response: Response
    ) -> LoginSchema:
        try:
            # find if auditor exists
            manager = self.repo.get_manager(email=email)
            if not manager:
                logger.error("No manager found with given email")
                raise HTTPException(
                    detail=f"No manager found with given email",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # compare password
            if manager.password != password:
                logger.error("Password not matched")
                raise HTTPException(
                    detail=f"Password not matched",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # generate jwt
            token = self.jwt_util.create_jwt_token(
                {
                    "id": manager.id,
                    "name": manager.name,
                    "email": manager.email,
                    "role": "manager",
                }
            )

            if not token:
                logger.error("Failed to generate JWT token")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate JWT token",
                )

            response.set_cookie(
                key="token",
                value=token,
                httponly=True,
                secure=False,  # Set True if HTTPS
                samesite="lax",  # or 'strict' or 'none'
                max_age=self.jwt_util.access_token_expire_minutes,
            )

            return LoginSchema(success=True, message="Manager logged in succesfully.")

        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to login for manager, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while manager login",
            )

    def get_manager_analytics(self, manager: Manager):
        try:
            if not isinstance(manager, Manager):
                logger.error("Current user is not manager")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Current user is not authorized as manager",
                )

            leads = self.repo.get_all_leads(manager_id=manager.id)
            audits = self.repo.get_all_audit(manager_id=manager.id)
            flagged_calls = self.repo.get_all_flagged_call(manager_id=manager.id)
            latest_flagged_audit = self.repo.get_all_latest_flagged_audit(manager.id)
            last_7_days_data = self.repo.get_last_7_days_audited_calls(manager.id)

            if any(
                x is None
                for x in [
                    leads,
                    audits,
                    flagged_calls,
                    latest_flagged_audit,
                    last_7_days_data,
                ]
            ):
                logger.error("leads/audits/flagged_calls/latest_flagged_audit is None")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error while fetching data from database",
                )

            return ManagerAnalyticsResponse(
                success=True,
                message="Succesfully analyzed audits for manager",
                total_assigned_leads=leads,
                total_audited_calls=audits,
                flagged_calls=flagged_calls,
                latest_flagged_audit=latest_flagged_audit,
                last_7_days_data=last_7_days_data,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to get manager analysis for manager, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting manager analysis for manager",
            )

    def get_auditors_analytics(self, manager: Manager) -> AuditorAnalyticsResponse:
        try:
            auditors_data = self.repo.get_auditor_and_audited_call_counts(
                manager_id=manager.id
            )
            auditors = self.repo.get_auditors(manager.id)

            if not auditors_data or not auditors:
                logger.error("Auditors data or auditors is None")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while  getting auditors data",
                )

            return AuditorAnalyticsResponse(
                success=True,
                message="Succesfully got the auditors data under manager",
                number_of_auditors=auditors_data["number_of_auditors"],
                total_audited_calls=auditors_data["total_audited_calls"],
                auditors=auditors,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(
                f"Failed to get auditors analysis for manager, error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting audit analysis.",
            )

    def get_counsellor_analysis(self, manager: Manager) -> CounsellorAnalysisResponse:
        try:
            counsellor_data = self.repo.get_counsellor_data(manager.id)
            counsellors = self.repo.get_counsellors(manager.id)

            if not counsellors or not counsellor_data:
                logger.error("counsellor_data or counsellors is none")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal sever error occurred while fetching counsellor data",
                )

            return CounsellorAnalysisResponse(
                success=True,
                message="Succesfully retrieved counsellors data",
                total_counsellors=counsellor_data["total_counsellors"],
                total_calls_made=counsellor_data["total_counsellors"],
                counsellors=counsellors,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(
                f"Failed to get counsellor analysis for manager, error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting counsellor analysis.",
            )
