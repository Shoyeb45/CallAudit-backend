from datetime import datetime, timedelta
import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Date, cast, func
from typing import Any, Dict, List, Optional
from features.auditor.schemas import CallResponse, CallStats, LatestCallResponse
from features.manager.schemas import AuditFlaggedResponse, OneDayAuditData
from models import AuditReport, Auditor, Call, CallAnalysis, Counsellor
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, desc

logger = logging.getLogger(__name__)


class AuditorRepository:
    def __init__(self, db: Session):
        self.db = db

    # reading methods
    def get_auditor(
        self, id: Optional[str] = None, email: Optional[str] = None
    ) -> Auditor | None:
        try:
            if id:
                return self.db.query(Auditor).filter(Auditor.id == id).first()

            return self.db.query(Auditor).filter(Auditor.email == email).first()
        except Exception as e:
            logger.error(f"Failed to get auditor, error: {str(e)}")
            return None

    def get_calls(self, auditor_id: str) -> List[CallResponse] | None:
        try:
            results = (
                self.db.query(
                    Call.id,
                    Call.client_number,
                    Call.duration,
                    Call.tags,
                    CallAnalysis.ai_confidence,
                    Call.recording_url,
                    CallAnalysis.summary,
                    CallAnalysis.sentiment_score,
                    CallAnalysis.anomalies,
                )
                .outerjoin(CallAnalysis, CallAnalysis.call_id == Call.id)
                .filter(Call.auditor_id == auditor_id)
                .order_by(CallAnalysis.ai_confidence.asc())
                .all()
            )

            final_response: List[CallResponse] = []

            for result in results:
                final_response.append(
                    CallResponse(
                        id=result.id,
                        client_number=result.client_number,
                        duration=result.duration,
                        tags=result.tags,
                        ai_confidence=result.ai_confidence or 0,
                        recording_url=result.recording_url,
                        summary=result.summary or "no_summary",
                        sentiment_score=int(result.sentiment_score or 0),
                        anomalies=result.anomalies or "no_anomalies",
                    )
                )

            return final_response
        except Exception as e:
            logger.error(f"Failed to fetch calls from database, error: {str(e)}")
            return None

    def get_call_stats(self, auditor_id: str) -> Dict[str, Any] | None:
        try:
            stats = (
                self.db.query(
                    func.count().filter(Call.is_audited.is_(True)).label("audited"),
                    func.count().filter(Call.is_audited.is_(False)).label("unaudited"),
                    func.count().filter(Call.is_flagged.is_(True)).label("flagged"),
                )
                .filter(Call.auditor_id == auditor_id)
                .one()
            )

            return {
                "audited": stats.audited,
                "unaudited": stats.unaudited,
                "flagged": stats.flagged,
            }

        except Exception as e:
            logger.error(f"Failed to fetch stats from database, error: {str(e)}")
            return None

    def get_latest_calls(self, auditor_id: str) -> List[LatestCallResponse]:
        try:
            results = (
                self.db.query(
                    Call.id,
                    Call.call_start,
                    Call.client_number,
                )
                .filter(Call.auditor_id == auditor_id, Call.is_audited.is_(True))
                .order_by(Call.call_start.desc())
                .all()
            )

            final_response: List[LatestCallResponse] = []

            for result in results:
                final_response.append(
                    LatestCallResponse(
                        id=result.id,
                        call_start=result.call_start,
                        client_number=result.client_number,
                    )
                )

            return final_response
        except Exception as e:
            logger.error(f"Failed to fetch latest calls from database, error: {str(e)}")
            return None

    def get_last_7_days_data(self, auditor_id: str) -> List[OneDayAuditData] | None:
        try:
            # Step 1: Generate last 7 days
            today = datetime.utcnow().date()
            date_range = [
                (today - timedelta(days=i)) for i in reversed(range(7))
            ]  # oldest to newest

            # Step 2: Fetch counts from DB
            raw_results = (
                self.db.query(
                    cast(AuditReport.created_at, Date).label("date"),
                    func.count(AuditReport.id).label("completed_audits"),
                )
                .filter(
                    AuditReport.auditor_id == auditor_id,
                    cast(AuditReport.created_at, Date) >= date_range[0],
                )
                .group_by(cast(AuditReport.created_at, Date))
                .all()
            )

            # Step 3: Build dict from raw results
            audit_dict = {row.date: row.completed_audits for row in raw_results}

            # Step 4: Fill missing dates with 0
            final_result = [
                OneDayAuditData(
                    date=date.isoformat(), audited_calls=audit_dict.get(date, 0)
                )
                for date in date_range
            ]

            return final_result
        except Exception as e:
            logger.error(f"Failed to fetch latest calls from database, error: {str(e)}")
            return None

    def approve_lead_and_update_db(self, data: Dict[str, Any], auditor_id: str):
        try:
            call_id = data.get("call_id")
            comments = data.get("comments")
            is_flag = data.get("is_flag")
            flag_reasons = data.get("flag_reasons")

            if not call_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Call ID is required.",
                )

            # Update Call table
            call = (
                self.db.query(Call)
                .filter(Call.id == call_id, Call.auditor_id == auditor_id)
                .first()
            )
            if not call:
                logger.error("Call not found for the given auditor.")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Call not found for the given auditor.",
                )

            call.is_audited = True  # always mark as audited

            # Update is_flagged if is_flag is not None
            if is_flag is not None:
                call.is_flagged = is_flag

            # Update AuditReport
            audit_report = (
                self.db.query(AuditReport)
                .filter(
                    AuditReport.call_id == call_id, AuditReport.auditor_id == auditor_id
                )
                .first()
            )

            if audit_report:
                # Update existing report
                if comments is not None:
                    audit_report.comments = comments
                if is_flag is not None:
                    audit_report.is_flagged = is_flag
                if flag_reasons is not None:
                    audit_report.flag_reason = flag_reasons
                audit_report.updated_at = datetime.utcnow()
            else:
                # Create new report
                logger.error("Audit report not found creating new one.")
                new_report = AuditReport(
                    call_id=call_id,
                    auditor_id=auditor_id,
                    manager_id=call.manager_id,
                    score=call.audit_score or 0,  # default to 0 if not set
                    comments=comments,
                    is_flagged=is_flag if is_flag is not None else False,
                    flag_reason=flag_reasons,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                self.db.add(new_report)

            # Commit changes
            self.db.commit()
            logger.info("Database update succesfull")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"SQLAlchemy error occurred: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while updating call and audit report.",
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to approve lead and update db, error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error occurred while approving lead.",
            )

    def get_all_latest_flagged_audit(
        self, auditor_id: str
    ) -> List[AuditFlaggedResponse] | None:
        try:
            logger.info(
                f"Getting all latest flagged audits for auditor with id: {auditor_id}"
            )
            flagged_calls_query = (
                self.db.query(
                    AuditReport.id,
                    AuditReport.call_id,
                    AuditReport.auditor_id,
                    Auditor.name.label("auditor_name"),
                    AuditReport.score,
                    AuditReport.comments,
                    AuditReport.flag_reason,
                    AuditReport.updated_at,
                    AuditReport.created_at,
                    Call.client_number,
                    Counsellor.name.label("counsellor_name"),
                )
                .join(Auditor, AuditReport.auditor_id == Auditor.id)
                .join(Call, AuditReport.call_id == Call.id)
                .join(Counsellor, Call.counsellor_id == Counsellor.id)
                .filter(
                    and_(
                        AuditReport.auditor_id == auditor_id,
                        AuditReport.is_flagged.is_(True),
                    )
                )
                .order_by(desc(AuditReport.updated_at))
            )

            results = flagged_calls_query.all()

            final_response: List[AuditFlaggedResponse] = []

            if results:
                for result in results:
                    # print(result.updated_at)
                    final_response.append(
                        AuditFlaggedResponse(
                            id=result.id,
                            call_id=result.call_id,
                            auditor_id=result.auditor_id,
                            auditor_name=result.auditor_name,
                            score=int(result.score) if result.score is not None else 0,
                            comments=result.comments,
                            flag_reason=(
                                result.flag_reason
                                if result.flag_reason is not None
                                else ""
                            ),
                            updated_at=result.updated_at,
                            created_at=result.created_at,
                            client_number=result.client_number,
                            counsellor_name=result.counsellor_name,
                        )
                    )
            return final_response
        except Exception as e:
            logger.error(
                f"Failed to retrieve all latest flagged audit from database, error: {str(e)}"
            )
            return None
