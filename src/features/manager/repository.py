import logging
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session
from typing import Optional
from models import Counsellor, Manager, Lead, AuditReport, Call, Auditor
from features.manager.schemas import AuditFlaggedResponse, AuditorResponse
from typing import List
from sqlalchemy import func

logger = logging.getLogger(__name__)


class ManagerRepository:
    def __init__(self, db: Session):
        self.db = db

    # reading methods
    def get_manager(
        self, id: Optional[str] = None, email: Optional[str] = None
    ) -> Manager | None:
        try:
            if id:
                return self.db.query(Manager).filter(Manager.id == id).first()

            return self.db.query(Manager).filter(Manager.email == email).first()
        except Exception as e:
            logger.error(f"Failed to get auditor, error: {str(e)}")
            return None

    def get_all_leads(self, manager_id: str) -> int:
        try:
            logger.info(f"Getting all leads for manager with id: {manager_id}")
            count = (
                self.db.query(func.count(Lead.id))
                .filter(Lead.manager_id == manager_id)
                .scalar()
            )

            return count
        except Exception as e:
            logger.error(f"Failed to get all leads, error: {str(e)}")
            return None

    def get_all_audit(self, manager_id: str) -> int:
        try:
            logger.info(f"Getting all audits for manager with id: {manager_id}")
            reports = (
                self.db.query(func.count(func.distinct(AuditReport.id)))
                .filter(AuditReport.manager_id == manager_id)
                .scalar()
            )

            return reports
        except Exception as e:
            logger.error(f"Failed to get total audited calls, error: {str(e)}")
            return None

    def get_all_flagged_call(self, manager_id: str) -> int:
        try:
            logger.info(f"Getting all flagged calls for manager with id: {manager_id}")
            count = (
                self.db.query(func.count(func.distinct(Call.id)))
                .filter(Call.manager_id == manager_id, Call.is_flagged.is_(True))
                .scalar()
            )

            return count
        except Exception as e:
            logger.error(f"Failed to get total audited calls, error: {str(e)}")
            return None

    # TODO: also get client_number and counsellor
    def get_all_latest_flagged_audit(
        self, manager_id: str
    ) -> List[AuditFlaggedResponse] | None:
        try:
            logger.info(
                f"Getting all latest flagged audits for manager with id: {manager_id}"
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
                        AuditReport.manager_id == manager_id,
                        AuditReport.is_flagged.is_(True),
                    )
                )
                .order_by(desc(AuditReport.updated_at))
            )
            
            results = flagged_calls_query.all()
            final_response: List[AuditFlaggedResponse] = []

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
                        flag_reason=result.flag_reason if result.flag_reason is not None else "",
                        updated_at=result.updated_at,
                        created_at=result.created_at,
                        client_number=result.client_number,
                        counsellor_name=result.counsellor_name
                    )
                )

            return final_response
        except Exception as e:
            logger.error(
                f"Failed to retrieve all latest flagged audit from database, error: {str(e)}"
            )
            return None

    def get_auditor_and_audited_call_counts(self, manager_id: str):
        try:
            logger.info("Getting auditor and audited calls count")
            result = self.db.query(
                func.count(func.distinct(Auditor.id)).label("number_of_auditors"),
                func.count(func.distinct(Call.id)).filter(Call.is_audited.is_(True)).label("total_audited_calls")
            ).join(
                Call, Auditor.id == Call.auditor_id, isouter=True
            ).filter(
                Auditor.manager_id == manager_id
            ).one()

            return {
                "number_of_auditors": result.number_of_auditors,
                "total_audited_calls": result.total_audited_calls
            }
        except Exception as e:
            print(f"Failed to get auditor and call counts, Error: {e}")
            return None
        
    def get_auditors(self, manager_id: str) -> List[AuditorResponse] | None:
        try:
            logger.info("Getting auditors")
            results = self.db.query(
                Auditor.id,
                Auditor.name,
                func.count(func.distinct(Lead.id)).label("total_assigned_leads"),
                func.count(func.distinct(AuditReport.id)).label("total_audited_leads")
            ).outerjoin(
                Lead, Lead.auditor_id == Auditor.id
            ).outerjoin(
                AuditReport, AuditReport.auditor_id == Auditor.id
            ).filter(
                Auditor.manager_id == manager_id
            ).group_by(
                Auditor.id, Auditor.name
            ).all()
            
            final_response: List[AuditorResponse] = []
            
            for result in results:
                final_response.append(AuditorResponse(
                    id=result.id,
                    name=result.name,
                    total_assigned_leads=result.total_assigned_leads,
                    total_audited_leads=result.total_audited_leads
                ))
                
            return final_response
        except Exception as e:
            print(f"Failed to get auditor and call counts, Error: {e}")
            return None
        
        