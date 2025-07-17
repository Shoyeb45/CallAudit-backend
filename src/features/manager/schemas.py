from pydantic import BaseModel
from datetime import datetime
from typing import List


class BaseResponse(BaseModel):
    success: bool
    message: str


# manager analysis
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

class OneDayAuditData(BaseModel):
    date: datetime
    audited_calls: int
    
class ManagerAnalyticsResponse(BaseResponse):
    total_assigned_leads: int
    total_audited_calls: int
    flagged_calls: int
    latest_flagged_audit: List[AuditFlaggedResponse]
    last_7_days_data: List[OneDayAuditData]


# Auditor analysis
class AuditorResponse(BaseModel):
    id: str
    name: str
    total_assigned_leads: int
    total_audited_leads: int
    
class AuditorAnalyticsResponse(BaseResponse):
    number_of_auditors: int
    total_audited_calls: int
    auditors: List[AuditorResponse]
    
    
# counsellor analysis
class CounsellorResponse(BaseModel):
    id: str
    name: str
    email: str
    total_calls: int

class CounsellorAnalysisResponse(BaseResponse):
    total_counsellors: int
    total_calls_made: int
    counsellors: List[CounsellorResponse] 