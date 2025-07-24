from sqlalchemy.orm import Session
from fastapi import Request, Response, HTTPException, status
from features.auditor.schemas import BaseResponse, LoginSchema
from features.manager.dependency import get_manager_service, get_manager_repository
from features.auditor.dependency import get_auditor_service, get_auditor_repository
import logging

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.repo = db
        self.manager_service = get_manager_service(get_manager_repository(db))
        self.auditor_service = get_auditor_service(get_auditor_repository(db))

    def login(
        self, email: str, password: str, role: str, response: Response
    ) -> LoginSchema:
        try:
            if role == "manager":
                return self.manager_service.login_manager(email, password, response)
            elif role == "auditor":
                return self.auditor_service.login_auditor(email, password, response)

            logger.error("Invalid user role")
            raise HTTPException(
                detail="Invalid user role",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Error occurred while logging in, error: {str(e)}")
            raise HTTPException(
                detail="Internal server error while logging in",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def logout(self, request: Request, response: Response) -> BaseResponse:
        try:
            token = request.cookies.get("token")

            if not token:
                logger.error("Token not found")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
                )

            response.delete_cookie("token")
            return BaseResponse(
                success=True,
                message="Succesfully logged out",
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Failed to logout user, error: {str(e)}")
            raise HTTPException(
                detail="Failed to logout user",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
