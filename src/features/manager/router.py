from fastapi import APIRouter, Response, Form, Depends
import logging

from features.auditor.schemas import LoginSchema
from features.manager.dependency import get_manager_service
from features.manager.services import ManagerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager", tags=["manager"])


# API endpoint for manger login
@router.post(
    "/login", description="API Endpoint for manager login", response_model=LoginSchema
)
def login_manager(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    service: ManagerService = Depends(get_manager_service),
):
    return service.login_manager(email, password, response)
