from fastapi import APIRouter, Response, Form, Depends
import logging

from dependecy import get_current_user
from features.auditor.schemas import LoginSchema
from features.manager.dependency import get_manager_service
from features.manager.services import ManagerService
from models import Manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager", tags=["manager"])


# API endpoint for manger login
# @router.post(
#     "/login", description="API Endpoint for manager login", response_model=LoginSchema
# )
# def login_manager(
#     response: Response,
#     email: str = Form(...),
#     password: str = Form(...),
#     service: ManagerService = Depends(get_manager_service),
# ):
#     return service.login_manager(email, password, response)


@router.get(
    "/flagged-audits",
    description="API endpoint to get flagged audits which comes under current logged in manager",
)
def get_flagged_manager(manager: Manager = Depends(get_current_user)):
    if not isinstance(manager, Manager):
        return {"ok": False}

    logger.info(manager.name)
    return {"ok": True}
