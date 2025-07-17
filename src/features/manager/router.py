from fastapi import APIRouter, Response, Form, Depends
import logging

from dependecy import get_current_user
from features.auditor.schemas import LoginSchema
from features.manager.schemas import AuditorAnalyticsResponse, ManagerAnalyticsResponse
from features.manager.dependency import get_manager_service
from features.manager.services import ManagerService
from models import Manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/manager", tags=["manager"])


@router.get(
    "/",
    description="API endpoint to get flagged audits which comes under current logged in manager",
    response_model=ManagerAnalyticsResponse,
)
def get_manager_analytics(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.get_manager_analytics(manager)


@router.get(
    "/auditors",
    description="Get auditors analysis",
    response_model=AuditorAnalyticsResponse
)
def get_auditor_analytics(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service),
):
    return service.get_auditors_analytics(manager)


@router.get(
    "/counsellor",
    description="Get counsellors analysis",
    # response_model=AuditorAnalyticsResponse   
)
def get_counsellor_analysis(
    manager: Manager = Depends(get_current_user),
    service: ManagerService = Depends(get_manager_service)
):
    return service.get_counsellor_analysis(manager)