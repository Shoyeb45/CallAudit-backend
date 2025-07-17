import logging
from sqlalchemy.orm import Session
from typing import Optional
from models import Manager

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
