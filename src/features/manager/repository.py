import logging
from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select, func, cast, Date
from sqlalchemy.orm import Session
from typing import Optional
from models import Counsellor, Manager, Lead, AuditReport, Call, Auditor
from features.manager.schemas import (
    AuditFlaggedResponse,
    AuditorResponse,
    CounsellorResponse,
    OneDayAuditData,
)
from typing import List, Dict, Any
from sqlalchemy import func
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ManagerRepository:
    """Repository class for handling manager-related database operations.

    This class provides methods for retrieving and manipulating data related to
    managers, auditors, counsellors, calls, and audit reports.
    """

    def __init__(self, db: Session):
        """Initialize the ManagerRepository with a database session.

        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db

    # reading methods
    def get_manager(
        self, id: Optional[str] = None, email: Optional[str] = None
    ) -> Manager | None:
        """Retrieve a manager by ID or email.

        Args:
            id (Optional[str]): Manager ID to search for
            email (Optional[str]): Manager email to search for

        Returns:


            Manager | None: Manager object if found, None otherwise
        """
        try:
            if id:
                return self.db.query(Manager).filter(Manager.id == id).first()
            return self.db.query(Manager).filter(Manager.email == email).first()
        except Exception as e:
            logger.error(f"Failed to get auditor, error: {str(e)}")
            return None

    def get_all_leads(self, manager_id: str) -> int:
        """Get the total count of calls for a manager.

        Args:
            manager_id (str): ID of the manager

        Returns:


            int: Total count of calls, or None if an error occurs
        """
        try:
            logger.info(f"Getting all leads for manager with id: {manager_id}")
            count = (
                self.db.query(func.count(Call.id))
                .filter(Call.manager_id == manager_id)
                .scalar()
            )
            return count
        except Exception as e:
            logger.error(f"Failed to get all leads, error: {str(e)}")
            return None

    def get_all_audit(self, manager_id: str) -> int:
        """Get the total count of distinct audit reports for a manager.

        Args:
            manager_id (str): ID of the manager

        Returns:


            int: Total count of distinct audit reports, or None if an error occurs
        """
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
        """Get the total count of flagged calls for a manager.

        Args:
            manager_id (str): ID of the manager

        Returns:


            int: Total count of flagged calls, or None if an error occurs
        """
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

    def get_all_latest_flagged_audit(
        self, manager_id: str
    ) -> List[AuditFlaggedResponse] | None:
        """Get all latest flagged audit reports for a manager.

        Args:
            manager_id (str): ID of the manager

        Returns:


            List[AuditFlaggedResponse] | None: List of flagged audit responses, or None if an error occurs
        """
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
                        flag_reason=(
                            result.flag_reason if result.flag_reason is not None else ""
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

    def get_auditor_and_audited_call_counts(self, manager_id: str):
        """Get counts of auditors and audited calls for a manager.

        Args:
            manager_id (str): ID of the manager

        Returns:


            dict | None: Dictionary containing 'number_of_auditors' and 'total_audited_calls' counts, or None if an error occurs
        """
        try:
            logger.info("Getting auditor and audited calls count")
            result = (
                self.db.query(
                    func.count(func.distinct(Auditor.id)).label("number_of_auditors"),
                    func.count(func.distinct(Call.id))
                    .filter(Call.is_audited.is_(True))
                    .label("total_audited_calls"),
                )
                .join(Call, Auditor.id == Call.auditor_id, isouter=True)
                .filter(Auditor.manager_id == manager_id)
                .one()
            )
            return {
                "number_of_auditors": result.number_of_auditors,
                "total_audited_calls": result.total_audited_calls,
            }
        except Exception as e:
            logger.error(f"Failed to get auditor and call counts, Error: {e}")
            return None

    def get_last_7_days_audited_calls(
        self, manager_id: str
    ) -> Optional[List[OneDayAuditData]]:
        """Get audited call counts for the last 7 days for a manager.

        Args:
            manager_id (str): ID of the manager

        Returns:

            Optional[List[OneDayAuditData]]: List of daily audit data for the last 7 days, or None if an error occurs
        """
        try:
            logger.info("Getting last 7 days audited data")
            today = datetime.utcnow().date()
            date_range = [
                (today - timedelta(days=i)) for i in reversed(range(7))
            ]  # 7 days including today
            # Query for actual audit counts
            results = (
                self.db.query(
                    cast(Call.call_start, Date).label("date"),
                    func.count(Call.id).label("audited_calls"),
                )
                .filter(
                    Call.manager_id == manager_id,
                    Call.is_audited.is_(True),
                    cast(Call.call_start, Date) >= date_range[0],
                )
                .group_by(cast(Call.call_start, Date))
                .order_by(cast(Call.call_start, Date))
                .all()
            )
            # Build a lookup dictionary
            result_map = {row.date: row.audited_calls for row in results}
            # Merge with fixed 7-day range
            final_response = [
                OneDayAuditData(date=day, audited_calls=result_map.get(day, 0))
                for day in date_range
            ]
            return final_response
        except Exception as e:
            logger.error(f"Failed to get auditor and call counts, Error: {e}")
            return None

    def get_auditors(self, manager_id: str) -> List[AuditorResponse] | None:
        """Get all auditors for a manager with their statistics.

        Args:
            manager_id (str): ID of the manager

        Returns:

            List[AuditorResponse] | None: List of auditor responses with statistics, or None if an error occurs
        """
        try:
            logger.info("Getting auditors")
            results = (
                self.db.query(
                    Auditor.id,
                    Auditor.name,
                    Auditor.is_active,
                    func.count(func.distinct(Lead.id)).label("total_assigned_leads"),
                    func.count(func.distinct(AuditReport.id)).label(
                        "total_audited_leads"
                    ),
                )
                .outerjoin(Lead, Lead.auditor_id == Auditor.id)
                .outerjoin(AuditReport, AuditReport.auditor_id == Auditor.id)
                .filter(Auditor.manager_id == manager_id)
                .group_by(Auditor.id, Auditor.name)
                .all()
            )
            final_response: List[AuditorResponse] = []
            for result in results:
                final_response.append(
                    AuditorResponse(
                        id=result.id,
                        name=result.name,
                        is_active=result.is_active,
                        total_assigned_leads=result.total_assigned_leads,
                        total_audited_leads=result.total_audited_leads,
                    )
                )
            return final_response
        except Exception as e:
            print(f"Failed to get auditor and call counts, Error: {e}")
            return None

    def get_counsellor_data(self, manager_id: str) -> Dict[str, Any] | None:
        """Get counsellor data including total counsellors and calls made.

        Args:
            manager_id (str): ID of the manager

        Returns:

            Dict[str, Any] | None: Dictionary containing 'total_counsellors' and 'total_calls_made' counts, or None if an error occurs
        """
        try:
            logger.info("Getting counsellor data...")
            result = self.db.query(
                select(func.count())
                .select_from(Counsellor)
                .filter(Counsellor.manager_id == manager_id)
                .scalar_subquery()
                .label("total_counsellors"),
                select(func.count())
                .select_from(Call)
                .filter(Call.manager_id == manager_id)
                .scalar_subquery()
                .label("total_calls_made"),
            ).one()
            return {
                "total_counsellors": result.total_counsellors,
                "total_calls_made": result.total_calls_made,
            }
        except Exception as e:
            logger.error(f"Failed to get counsellor analysis, Error: {e}")
            return None

    def get_counsellors(self, manager_id: str) -> List[CounsellorResponse] | None:
        """Get all counsellors for a manager with their call statistics.

        Args:
            manager_id (str): ID of the manager

        Returns:

            List[CounsellorResponse] | None: List of counsellor responses with call statistics, or None if an error occurs
        """
        try:
            logger.info("Getting counsellors...")
            counsellors = (
                self.db.query(
                    Counsellor.id,
                    Counsellor.name,
                    Counsellor.email,
                    Counsellor.is_active,
                    func.count(Call.id).label("total_calls"),
                )
                .outerjoin(Call, Call.counsellor_id == Counsellor.id)
                .filter(Counsellor.manager_id == manager_id)
                .group_by(Counsellor.id, Counsellor.name, Counsellor.email)
                .all()
            )
            final_response: List[CounsellorResponse] = []
            for counsellor in counsellors:
                final_response.append(
                    CounsellorResponse(
                        id=counsellor.id,
                        name=counsellor.name,
                        is_active=counsellor.is_active,
                        email=counsellor.email,
                        total_calls=counsellor.total_calls,
                    )
                )
            return final_response
        except Exception as e:
            print(f"Failed to get counsellors, Error: {e}")
            return None

    def create_auditor(self, auditor_data) -> bool:
        """Create a new auditor.

        Args:
            auditor_data (dict): Data for creating the new auditor

        Returns:

            bool: True if successful, False otherwise
        """
        try:
            auditor = Auditor(**auditor_data)
            self.db.add(auditor)
            self.db.commit()
            self.db.refresh(auditor)
            logger.info("Succesfully created new auditor in database")
            return True
        except Exception as e:
            logger.error(f"Failed to create new auditor in database, error: {str(e)}")
            return False

    def create_counsellor(self, counsellor_data) -> bool:
        """Create a new counsellor.

        Args:
            counsellor_data (dict): Data for creating the new counsellor

        Returns:

            bool: True if successful, False otherwise
        """
        try:
            counsellor = Counsellor(**counsellor_data)
            self.db.add(counsellor)
            self.db.commit()
            self.db.refresh(counsellor)
            logger.info("Succesfully created new counsellor in database")
            return True
        except Exception as e:
            logger.error(
                f"Failed to create new counsellor in database, error: {str(e)}"
            )
            return False

    def deactivate_auditor(self, auditor_id: str) -> bool:
        """Deactivate an auditor.

        Args:
            auditor_id (str): ID of the auditor to deactivate

        Returns:

            bool: True if successful, False otherwise
        """
        try:
            auditor = self.db.query(Auditor).filter_by(id=auditor_id).first()
            if not auditor:
                logger.warning(f"Auditor with ID {auditor_id} does not exist.")
                return False
            logger.debug(
                f"Deactivating auditor: {auditor.id} (current status: {auditor.is_active})"
            )
            auditor.is_active = False
            auditor.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(auditor)
            logger.info(f"Successfully deactivated auditor with ID {auditor_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate auditor, error: {str(e)}")
            return False

    def deactivate_counsellor(self, counsellor_id: str) -> bool:
        """Deactivate a counsellor.

        Args:
            counsellor_id (str): ID of the counsellor to deactivate

        Returns:

            bool: True if successful, False otherwise
        """
        try:
            counsellor = self.db.query(Counsellor).filter_by(id=counsellor_id).first()
            if not counsellor:
                logger.warning(f"Counsellor with ID {counsellor_id} does not exist.")
                return False
            logger.debug(
                f"Deactivating counsellor: {counsellor.id} (current status: {counsellor.is_active})"
            )
            counsellor.updated_at = datetime.utcnow()
            counsellor.is_active = False
            self.db.commit()
            self.db.refresh(counsellor)
            logger.info(f"Successfully deactivated counsellor with ID {counsellor_id}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to deactivate counsellor from database, error: {str(e)}"
            )
            return False

    def activate_auditor(self, auditor_id: str) -> bool:
        """Activate an auditor.

        Args:
            auditor_id (str): ID of the auditor to activate

        Returns:

            bool: True if successful, False otherwise
        """
        try:
            auditor = self.db.query(Auditor).filter_by(id=auditor_id).first()
            if not auditor:
                logger.warning(f"Auditor with ID {auditor_id} does not exist.")
                return False
            logger.debug(
                f"Activating auditor: {auditor.id} (current status: {auditor.is_active})"
            )
            auditor.is_active = True
            auditor.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(auditor)
            logger.info(f"Successfully activated auditor with ID {auditor_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to activate auditor, error: {str(e)}")
            return False

    def activate_counsellor(self, counsellor_id: str) -> bool:
        """Activate a counsellor.

        Args:
            counsellor_id (str): ID of the counsellor to activate

        Returns:

            bool: True if successful, False otherwise
        """
        try:
            counsellor = self.db.query(Counsellor).filter_by(id=counsellor_id).first()
            if not counsellor:
                logger.warning(f"Counsellor with ID {counsellor_id} does not exist.")
                return False
            logger.debug(
                f"Activating counsellor: {counsellor.id} (current status: {counsellor.is_active})"
            )
            counsellor.updated_at = datetime.utcnow()
            counsellor.is_active = True
            self.db.commit()
            self.db.refresh(counsellor)
            logger.info(f"Successfully activated counsellor with ID {counsellor_id}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to activate counsellor from database, error: {str(e)}"
            )
            return False

    def unflag_audit(self, audit_id) -> bool:
        """Unflag an audit report and its associated call.

        Args:
            audit_id (str): ID of the audit report to unflag

        Returns:

            bool: True if successful, False otherwise

        Raises:
            HTTPException: If audit report or call is not found
        """
        try:
            report = (
                self.db.query(AuditReport).filter(AuditReport.id == audit_id).first()
            )
            if not report:
                logger.error("No audit report found for given call id")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No audit report found with given audit id",
                )
            report.is_flagged = False
            report.flag_reason = "Call unflagged"
            report.updated_at = datetime.utcnow()
            # Sync with Call
            call = self.db.query(Call).filter(Call.id == report.call_id).first()
            if not call:
                logger.error("No call found with given audit id")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No call found  with given audit id",
                )
            call.is_flagged = False
            call.updated_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Succesfully unflagged audit with audit id: {audit_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unflag audit, error: {str(e)}")
            return False
