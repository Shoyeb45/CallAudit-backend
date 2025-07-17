import logging

from fastapi import HTTPException, status, Response
from core.jwt_util import get_jwt_util
from features.auditor.repository import AuditorRepository
from config import get_jwt_settings
from features.auditor.schemas import LoginSchema

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
                { "id": auditor.id, "name": auditor.name, "email": auditor.email, "role": "auditor" }
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

            return LoginSchema(success=True, message="Auditor logged in succesfully.")

        except HTTPException as http_exception:
            raise http_exception
        except Exception as e:
            logger.error(f"Failed to login for auditor, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error occurred while auditor login",
            )
