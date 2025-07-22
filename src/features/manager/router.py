from typing import Optional
from fastapi import APIRouter, Response, Form, Depends
import logging

from dependecy import get_current_user
from features.auditor.schemas import LoginSchema
from features.manager.schemas import (
    AuditorAnalyticsResponse,
    BaseResponse,
    CounsellorAnalysisResponse,
    FlaggedAuditsResponse,
    ManagerAnalyticsResponse,
    NewUserCreatedSchema,
)
from features.manager.dependency import get_manager_service
from features.manager.services import ManagerService
from models import Manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager", tags=["API Endpoints for manager"])


@router.get(
    "/",
    description="API endpoint to get dashboard data for manager",
    response_model=ManagerAnalyticsResponse,
)
def get_dashboard_data_for_manager(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.get_manager_analytics(manager)


@router.get(
    "/flagged-audits",
    description="API endpoint to get total flagged audits.",
    response_model=FlaggedAuditsResponse,
)
def get_flagged_audits(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.get_flagged_audits(manager)


@router.get(
    "/auditors",
    description="Get auditors analysis under the manager",
    response_model=AuditorAnalyticsResponse,
)
def get_auditor_analytics(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.get_auditors_analytics(manager)


@router.get(
    "/counsellor",
    description="Get counsellors analysis",
    response_model=CounsellorAnalysisResponse,
)
def get_counsellor_analysis(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.get_counsellor_analysis(manager)


@router.post(
    "/add",
    description="API endpoint to add new auditor or new counsellor",
    response_model=NewUserCreatedSchema,
)
def add_auditor_or_counsellor(
    role: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    auditor_id: Optional[str] = Form(None),
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.add_new_user(role, name, email, phone, auditor_id, manager.id)


@router.post(
    "/deactivate",
    description="API endpoint to add new auditor",
    response_model=BaseResponse,
)
def delete_auditor_or_counsellor(
    role: str = Form(...),
    counsellor_id: Optional[str] = Form(None),
    auditor_id: Optional[str] = Form(None),
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.deactivate_auditor_or_counsellor(counsellor_id, auditor_id, role)

@router.post(
    "/activate",
    description="API endpoint to add new auditor",
    response_model=BaseResponse,
)
def delete_auditor_or_counsellor(
    role: str = Form(...),
    counsellor_id: Optional[str] = Form(None),
    auditor_id: Optional[str] = Form(None),
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.activate_auditor_or_counsellor(counsellor_id, auditor_id, role)


@router.get(
    "/unflag",
    description="API endpoint to unflag any flagged audit report",
    response_model=BaseResponse
)
def unflag_flagged_audit(
    audit_id: str,
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service)
):
    return service.unflag_flagged_audit(audit_id)