# src/dependecy.py
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db  # your SessionLocal generator
from features.auditor.repository import AuditorRepository
from features.auditor.services import AuditorService


def get_auditor_repository(db: Session = Depends(get_db)):
    return AuditorRepository(db)


def get_auditor_service(repo: AuditorRepository = Depends(get_auditor_repository)):
    return AuditorService(repo)
