from fastapi import APIRouter, Form, Depends, Response
from database import get_db
from sqlalchemy.orm import Session
import logging

from dependecy import get_current_user
from features.auditor.schemas import LoginSchema
from features.auditor.dependency import get_auditor_service
from features.auditor.services import AuditorService
from models import Auditor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auditor", tags=["auditor"])


# # API endpoint for logging in
# @router.post(
#     "/login",
#     description="API endpoint for loggin in for auditor",
#     response_model=LoginSchema,
# )
# def login_auditor(
#     response: Response,
#     email: str = Form(...),
#     password: str = Form(...),
#     service: AuditorService = Depends(get_auditor_service),
# ):
#     return service.login_auditor(email, password, response)


@router.get(
    "/calls",
    description="API endpoint to get all the calls belongs to the current auditor",
)
def get_calls(auditor: Auditor = Depends(get_current_user)):

    if not isinstance(auditor, Auditor):
        return {"wr": "yes"}
    return {"s": "fd"}
