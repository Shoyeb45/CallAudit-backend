from fastapi import APIRouter, Form, Request, Response, Depends
import logging

from dependecy import get_current_user
from features.auditor.schemas import LoginSchema
from features.auth.dependency import get_auth_service
from features.auth.services import AuthService

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
    response_model=LoginSchema,
)
def logout(
    request: Request,
    response: Response,
    user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    return service.logout(request, response)
