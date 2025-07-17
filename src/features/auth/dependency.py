from features.auth.repository import AuthRepository
from features.auth.services import AuthService
from sqlalchemy.orm import Session
from database import get_db
from fastapi import Depends


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_auth_repository(db: Session = Depends(get_db)) -> AuthRepository:
    return AuthRepository(db)
