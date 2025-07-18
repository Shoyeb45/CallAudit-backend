from sqlalchemy.orm import Session


class CounsellorRepository:
    def __init__(self, db: Session):
        self.db = db
