import logging
import random
import string
from typing import Any, Dict

from fastapi import HTTPException, status, Response
from core.jwt_util import get_jwt_util
from features.manager.repository import ManagerRepository
from config import get_jwt_settings
from features.auditor.schemas import LoginSchema, User
from features.manager.schemas import (
    AuditorAnalyticsResponse,
    BaseResponse,
    CounsellorAnalysisResponse,
    FlaggedAuditsResponse,
    ManagerAnalyticsResponse,
    NewUserCreatedSchema,
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

            return LoginSchema(
                success=True,
                message="Manager logged in succesfully.",
                user=User(
                    id=manager.id,
                    name=manager.name,
                    email=manager.email,
                    role="manager",
                ),
            )

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

    def get_flagged_audits(self, manager: Manager) -> FlaggedAuditsResponse:
        try:
            logger.info("API endpoint called for getting flagged audits")

            flagged_audits = self.repo.get_all_latest_flagged_audit(manager.id)

            if flagged_audits == []:
                return FlaggedAuditsResponse(
                    success=True,
                    message="Succesfully retrieved the flagged audits",
                    flagged_audits=flagged_audits,
                )

            if not flagged_audits:
                logger.error("Failed to get flagged audits")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while fetching flagged audits.",
                )

            return FlaggedAuditsResponse(
                success=True,
                message="Succesfully retrieved the flagged audits",
                flagged_audits=flagged_audits,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to get flagged audits for manager, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting flagged audits.",
            )

    def add_new_user(
        self,
        role: str,
        name: str,
        email: str,
        phone: str,
        auditor_id: str,
        manager_id: str,
    ):
        try:
            if role == "auditor":
                return self.create_new_auditor(
                    {
                        "email": email,
                        "name": name,
                        "phone": phone,
                        "manager_id": manager_id,
                    }
                )
            elif role == "counsellor":
                return self.create_new_counsellor(
                    {
                        "email": email,
                        "name": name,
                        "phone": phone,
                        "manager_id": manager_id,
                        "auditor_id": auditor_id,
                    }
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No matching role to add, the role should be auditor or counsellor",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to create new auditor or counsellor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while creating new auditor or counsellor",
            )

    def create_new_auditor(self, auditor_data: Dict[str, Any]) -> NewUserCreatedSchema:
        try:
            auditor_data["password"] = self.__generate_strong_password()
            is_auditor_created = self.repo.create_auditor(auditor_data)
            if not is_auditor_created:
                logger.info("Failed to create new auditor")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while creating new auditor",
                )

            return NewUserCreatedSchema(
                success=True,
                message="Auditor created succesfully",
                password=auditor_data["password"],
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to create new auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while creating new auditor",
            )

    def create_new_counsellor(
        self, counsellor_data: Dict[str, Any]
    ) -> NewUserCreatedSchema:
        try:
            if not counsellor_data["auditor_id"]:
                logger.error("No auditor id found for counsellor")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Auditor ID needed for creating counsellor",
                )

            is_counsellor_created = self.repo.create_counsellor(counsellor_data)
            if not is_counsellor_created:
                logger.info("Failed to create new counsellor")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while creating new counsellor",
                )
            return NewUserCreatedSchema(
                success=True,
                message="Counsellor created succesfully",
                password="Not needed",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to create new counsellor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while creating new counsellor",
            )

    def __generate_strong_password(self, length=10):
        if length < 4:
            raise ValueError(
                "Password length should be at least 4 to include all character types."
            )

        # Ensure at least one of each character type
        password = [
            random.choice(string.ascii_lowercase),
            random.choice(string.ascii_uppercase),
            random.choice(string.digits),
            random.choice(string.punctuation),
        ]

        # Fill the rest with random choices from all allowed characters
        all_chars = string.ascii_letters + string.digits + string.punctuation
        password += random.choices(all_chars, k=length - 4)

        # Shuffle to prevent predictable sequences
        random.shuffle(password)

        return "".join(password)

    def deactivate_auditor(self, auditor_id) -> BaseResponse:
        try:
            if not auditor_id:
                logger.error("Auditor id not found")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Auditor id not found",
                )

            is_auditor_deleted = self.repo.deactivate_auditor(auditor_id)
            if not is_auditor_deleted:
                logger.error("Failed to deactivate auditor")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while deactivating auditor",
                )

            return BaseResponse(
                success=True,
                message=f"Succesfully deactivated auditor with id: {auditor_id}",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to deactivate auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while deactivating auditor",
            )

    def activate_auditor(self, auditor_id) -> BaseResponse:
        try:
            if not auditor_id:
                logger.error("Auditor id not found")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Auditor id not found",
                )

            is_auditor_deleted = self.repo.activate_auditor(auditor_id)
            if not is_auditor_deleted:
                logger.error("Failed to activate auditor")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while activating auditor",
                )

            return BaseResponse(
                success=True,
                message=f"Succesfully activated auditor with id: {auditor_id}",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed toeactivate auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while activating auditor",
            )

    def deactivate_counsellor(self, counsellor_id: str) -> BaseResponse:
        try:
            if not counsellor_id:
                logger.error("Counsellor id not found")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Counsellor id not found",
                )

            is_counsellor_deleted = self.repo.deactivate_counsellor(counsellor_id)

            if not is_counsellor_deleted:
                logger.error("Failed to deactivate counsellor")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while deactivate counsellor",
                )

            return BaseResponse(
                success=True,
                message=f"Succesfully deactivate counsellor with id: {counsellor_id}",
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to deactivate counsellor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while deactivating counsellor",
            )

    def activate_counsellor(self, counsellor_id: str) -> BaseResponse:
        try:
            if not counsellor_id:
                logger.error("Counsellor id not found")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Counsellor id not found",
                )

            is_counsellor_deleted = self.repo.activate_counsellor(counsellor_id)

            if not is_counsellor_deleted:
                logger.error("Failed to activate counsellor")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while activate counsellor",
                )

            return BaseResponse(
                success=True,
                message=f"Succesfully activated counsellor with id: {counsellor_id}",
            )

        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to activate counsellor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while activating counsellor",
            )

    def deactivate_auditor_or_counsellor(
        self, counsellor_id, auditor_id, role
    ) -> BaseResponse:
        try:
            if role == "auditor":
                return self.deactivate_auditor(auditor_id)
            elif role == "counsellor":
                return self.deactivate_counsellor(counsellor_id)
            logger.error("No valid role")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid role to deactivate",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to deactivate auditor or counsellor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while deactivating auditor or counsellor",
            )

    def activate_auditor_or_counsellor(
        self, counsellor_id, auditor_id, role
    ) -> BaseResponse:
        try:
            if role == "auditor":
                return self.activate_auditor(auditor_id)
            elif role == "counsellor":
                return self.activate_counsellor(counsellor_id)

            logger.error("No valid role")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid role to activate",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to activate auditor or counsellor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while activating auditor or counsellor",
            )

    def unflag_flagged_audit(self, manager: Manager, audit_id: str) -> BaseResponse:
        try:
            if not isinstance(manager, Manager):
                logger.error("User is not manager")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorised access, user is not manager.",
                )

            is_unflagged = self.repo.unflag_audit(audit_id)

            if not is_unflagged:
                logger.error("Failed to unflag audit")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while unflagging audit",
                )
            return BaseResponse(
                success=True,
                message=f"Succesfully unflagged given audit with id: {audit_id}",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to unflag audit, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while unflagging audit",
            )
