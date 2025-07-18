from datetime import datetime
from pydantic import BaseModel
from typing import List

from features.manager.schemas import OneDayAuditData


class User(BaseModel):
    id: str
    name: str
    email: str
    role: str


class LoginSchema(BaseModel):
    success: bool
    message: str
    user: User


class BaseResponse(BaseModel):
    success: bool
    message: str


class CallStats(BaseModel):
    audited: int
    unaudited: int
    flagged: int


class CallResponse(BaseModel):
    id: str
    client_number: str
    duration: int
    tags: str
    ai_confidence: float
    recording_url: str
    summary: str
    sentiment_score: int
    anomalies: str


class CallsResponseSchema(BaseResponse):
    calls: List[CallResponse]
    call_stats: CallStats


class LatestCallResponse(BaseModel):
    id: str
    call_start: datetime
    client_number: str


class DashboardAnalysisResponse(BaseResponse):
    total_assigned_leads: int
    total_audited_calls: int
    flagged_calls: int
    latest_calls: List[LatestCallResponse]
    last_7_days_data: List[OneDayAuditData]
