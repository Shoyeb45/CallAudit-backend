from typing import Optional
from fastapi import APIRouter, Form, Depends, Response
from database import get_db
from sqlalchemy.orm import Session
import logging

from dependecy import get_current_user
from features.auditor.schemas import (
    BaseResponse,
    CallsResponseSchema,
    DashboardAnalysisResponse,
    LoginSchema,
)
from features.auditor.dependency import get_auditor_service
from features.auditor.services import AuditorService
from features.manager.schemas import FlaggedAuditsResponse
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


@router.post(
    "/approve-audit",
    description="API endpoint to approve lead",
    response_model=BaseResponse,
)
def approve_lead(
    call_id: str = Form(...),
    comments: Optional[str] = Form(None),
    is_flag: Optional[bool] = Form(False),
    flag_reasons: Optional[str] = Form(None),
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    return service.approve_lead(
        {
            "call_id": call_id,
            "comments": comments,
            "is_flag": is_flag,
            "flag_reasons": flag_reasons,
        },
        auditor,
    )


@router.get(
    "/unflag",
    description="API endpoint to unflag any flagged audit report",
    response_model=BaseResponse,
)
def unflag_flagged_audit(
    audit_id: str,
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    return service.unflag_flagged_audit(auditor, audit_id)


@router.get(
    "/flagged-audits",
    description="API endpoint to get total flagged audits.",
    response_model=FlaggedAuditsResponse,
)
def get_flagged_audits(
    auditor: Auditor = Depends(get_current_user),
    service: AuditorService = Depends(get_auditor_service),
):
    return service.get_flagged_audits(auditor)
