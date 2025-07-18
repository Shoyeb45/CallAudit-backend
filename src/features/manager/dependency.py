# src/dependecy.py
from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db  # your SessionLocal generator
from features.manager.repository import ManagerRepository
from features.manager.services import ManagerService


def get_manager_repository(db: Session = Depends(get_db)):
    return ManagerRepository(db)


def get_manager_service(repo: ManagerRepository = Depends(get_manager_repository)):
    return ManagerService(repo)
