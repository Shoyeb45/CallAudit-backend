import logging

from fastapi import HTTPException, status, Response
from core.jwt_util import get_jwt_util
from features.manager.repository import ManagerRepository
from config import get_jwt_settings
from features.auditor.schemas import LoginSchema

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
