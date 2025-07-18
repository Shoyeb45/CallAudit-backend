from sqlalchemy.orm import Session
from database import get_db
from fastapi import Depends

from features.counsellor.repository import CounsellorRepository
from features.counsellor.services import CounsellorService


def get_counsellor_repository(db: Session = Depends(get_db)) -> CounsellorRepository:
    return CounsellorRepository(db)


def get_counsellor_service(
    repo: CounsellorRepository = Depends(get_counsellor_repository),
) -> CounsellorService:
    return CounsellorService(repo)
