from fastapi import APIRouter, Form, Depends, Response
from database import get_db
from sqlalchemy.orm import Session
import logging

from features.auditor.schemas import LoginSchema
from features.auditor.dependency import get_auditor_service
from features.auditor.services import AuditorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auditor", tags=["auditor"])


# API endpoint for logging in
@router.post(
    "/login",
    description="API endpoint for loggin in for auditor",
    response_model=LoginSchema,
)
def login_auditor(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    service: AuditorService = Depends(get_auditor_service),
):
    return service.login_auditor(email, password, response)
