import logging
import random
import string
from typing import Any, Dict

from fastapi import HTTPException, status, Response
from core.jwt_util import get_jwt_util
from features.auditor.repository import AuditorRepository
from config import get_jwt_settings
from features.auditor.schemas import (
    BaseResponse,
    CallStats,
    CallsResponseSchema,
    DashboardAnalysisResponse,
    LoginSchema,
    User,
)
from models import Auditor


logger = logging.getLogger(__name__)


class AuditorService:
    def __init__(self, repo: AuditorRepository):
        self.repo = repo
        self.jwt_util = get_jwt_util()

    def login_auditor(
        self, email: str, password: str, response: Response
    ) -> LoginSchema:
        try:
            # find if auditor exists
            auditor = self.repo.get_auditor(email=email)
            if not auditor:
                logger.error("No auditor found with given email")
                raise HTTPException(
                    detail=f"No auditor found with given email",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            # compare password
            if auditor.password != password:
                logger.error("Password not matched")
                raise HTTPException(
                    detail=f"Password not matched",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            # generate jwt
            token = self.jwt_util.create_jwt_token(
                {
                    "id": auditor.id,
                    "name": auditor.name,
                    "email": auditor.email,
                    "role": "auditor",
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
                message="Auditor logged in succesfully.",
                user=User(
                    id=auditor.id,
                    name=auditor.name,
                    email=auditor.email,
                    role="auditor",
                ),
            )

        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to login for auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while auditor login",
            )

    def get_calls(self, auditor: Auditor) -> CallsResponseSchema:
        try:
            if not isinstance(auditor, Auditor):
                logger.error("Current user is not auditor")
                raise HTTPException(
                    detail="Unauthorised access, current user is not auditor.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            calls = self.repo.get_calls(auditor.id)
            call_stats = self.repo.get_call_stats(auditor.id)

            if not calls or not call_stats:
                logger.error("calls or call_stats is None")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while fetching call data.",
                )

            return CallsResponseSchema(
                success=True,
                message="Succesfully retrieved calls for auditor",
                calls=calls,
                call_stats=CallStats(
                    audited=call_stats["audited"],
                    unaudited=call_stats["unaudited"],
                    flagged=call_stats["flagged"],
                ),
            )
        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to get calls for auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while fetching calls",
            )

    def get_dashboard_data(self, auditor: Auditor) -> DashboardAnalysisResponse:
        try:
            if not isinstance(auditor, Auditor):
                logger.error("Current user is not auditor")
                raise HTTPException(
                    detail="Unauthorised access, current user is not auditor.",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            call_stats = self.repo.get_call_stats(auditor.id)
            latest_calls = self.repo.get_latest_calls(auditor.id)
            last_7_days_data = self.repo.get_last_7_days_data(auditor.id)

            if not call_stats or not latest_calls or not last_7_days_data:
                logger.error("call stats or latest_calls not last_7_days_data is None")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error occurred while fetching dashboard data",
                )

            return DashboardAnalysisResponse(
                success=True,
                message="Succesfully retrieved dashboard data",
                total_assigned_leads=call_stats["audited"] + call_stats["unaudited"],
                total_audited_calls=call_stats["audited"],
                flagged_calls=call_stats["flagged"],
                latest_calls=latest_calls,
                last_7_days_data=last_7_days_data,
            )
        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to get calls for auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while fetching calls",
            )

    def approve_lead(self, data: Dict[str, Any], auditor: Auditor) -> BaseResponse:
        try:
            logger.info("Approve lead api called")
            self.repo.approve_lead_and_update_db(data, auditor.id)
            return BaseResponse(success=True, message="Succesfully approved audit")
        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to approve leads, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while approving leads",
            )
