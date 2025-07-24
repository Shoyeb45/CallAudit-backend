from fastapi import Depends
from sqlalchemy.orm import Session
from database import get_db
from features.manager.repository import ManagerRepository
from features.manager.services import ManagerService


def get_manager_repository(db: Session = Depends(get_db)):
    """
    Dependency that provides a ManagerRepository instance.

    This function creates and returns a ManagerRepository instance using the
    database session provided by the FastAPI dependency injection system.

    Args:
        db (Session): Database session dependency injected by FastAPI

    Returns:
        ManagerRepository: Repository instance for manager-related database operations
    """
    return ManagerRepository(db)


def get_manager_service(repo: ManagerRepository = Depends(get_manager_repository)):
    """
    Dependency that provides a ManagerService instance.

    This function creates and returns a ManagerService instance using the
    ManagerRepository dependency provided by the FastAPI dependency injection system.

    Args:
        repo (ManagerRepository): Manager repository dependency injected by FastAPI

    Returns:
        ManagerService: Service instance for manager-related business logic
    """
    return ManagerService(repo)
