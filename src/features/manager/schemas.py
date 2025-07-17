from pydantic import BaseModel
from datetime import datetime
from typing import List


class BaseResponse(BaseModel):
    success: bool
    message: str


class AuditFlaggedResponse(BaseModel):
    id: str
    call_id: str
    auditor_id: str
    auditor_name: str
    score: int
    comments: str
    flag_reason: str
    client_number: str
    counsellor_name: str
    updated_at: datetime
    created_at: datetime


class ManagerAnalyticsResponse(BaseResponse):
    total_assigned_leads: int
    total_audited_calls: int
    flagged_calls: int
    latest_flagged_audit: List[AuditFlaggedResponse]


class AuditorResponse(BaseModel):
    id: str
    name: str
    total_assigned_leads: int
    total_audited_leads: int
    
class AuditorAnalyticsResponse(BaseResponse):
    number_of_auditors: int
    total_audited_calls: int
    auditors: List[AuditorResponse]