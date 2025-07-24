from fastapi import APIRouter, Form, HTTPException, Request, Response, Depends, status
import logging

from dependecy import get_current_user
from features.auditor.schemas import BaseResponse, LoginSchema, User
from features.auth.dependency import get_auth_service
from features.auth.services import AuthService
from models import Auditor, Manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["API endpoints for auth"])


@router.post(
    "/login",
    description="API endpoint for both manager and auditor",
    response_model=LoginSchema,
)
def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    service: AuthService = Depends(get_auth_service),
):
    return service.login(email, password, role, response)


@router.get(
    "/logout",
    description="API endpoint to log out the user",
    response_model=BaseResponse,
)
def logout(
    request: Request,
    response: Response,
    user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    return service.logout(request, response)


@router.get(
    "/check-auth",
    description="API endpoint to get the user details",
    response_model=LoginSchema,
)
def check_auth(user=Depends(get_current_user)):
    role = None
    if isinstance(user, Auditor):
        role = "auditor"
    elif isinstance(user, Manager):
        role = "manager"

    if not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorised access, user is not auditor or manager.",
        )

    return LoginSchema(
        success=True,
        message="User is authenticated",
        user=User(id=user.id, name=user.name, email=user.email, role=role),
    )
