from fastapi import APIRouter, Form, Depends, Response
from database import get_db
from sqlalchemy.orm import Session
import logging

from dependecy import get_current_user
from features.auditor.schemas import (
    CallsResponseSchema,
    DashboardAnalysisResponse,
    LoginSchema,
)
from features.auditor.dependency import get_auditor_service
from features.auditor.services import AuditorService
from models import Auditor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auditor", tags=["API Endpoints for auditor"])


@router.get(
    "/",
    description="API endpoint to get audito's dashboard data",
    response_model=DashboardAnalysisResponse,
)
def get_dashboard_data(
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    return service.get_dashboard_data(auditor)


@router.get(
    "/calls",
    description="API endpoint to get all the calls belongs to the current auditor",
    response_model=CallsResponseSchema,
)
def get_calls(
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    return service.get_calls(auditor)
