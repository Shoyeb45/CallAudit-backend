import logging
from sqlalchemy.orm import Session
from typing import Optional
from models import Auditor

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
