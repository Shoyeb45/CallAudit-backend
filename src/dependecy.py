from fastapi import Request, HTTPException, Depends, status
from sqlalchemy.orm import Session
import logging
from config import get_jwt_settings
from database import get_db
from jose import jwt

from features.auditor.repository import AuditorRepository
from features.manager.repository import ManagerRepository

logger = logging.getLogger(__name__)


def get_current_user(req: Request, db: Session = Depends(get_db)):
    """Dependency for verifying user and getting current user

    Args:
        req (Request): HTTP request object which contains cookies
        db (Session, optional): Current db session. Defaults to Depends(get_db).

    Returns:
        Auditor or Manager: if the user is auditor then `Auditor`, and if the role is manager then `Manager` else throws `HTTPException`
    """
    try:
        jwt_settings = get_jwt_settings()
        token = req.cookies.get("token", None)

        if not token:
            logger.error("Token not found in cookies")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is missing",
            )

        payload = jwt.decode(
            token, jwt_settings.jwt_secret, algorithms=[jwt_settings.algorithm]
        )
        email, role = payload.get("email"), payload.get("role")

        if email is None or role is None:
            logger.error("Email or role not found")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        if role == "manager":
            repo = ManagerRepository(db)
            manager = repo.get_manager(email=email)
            if manager is None:
                logger.error("Manager not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Manager not found",
                )

            return manager
        elif role == "auditor":
            repo = AuditorRepository(db)
            auditor = repo.get_auditor(email=email)
            if auditor is None:
                logger.error("Auditor not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Auditor not found",
                )

            return auditor
        logger.error("User is not auditor or manager, unauthorised access")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user, user is not manager or auditor",
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Failed to verify user, error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
