from core.logging import setup_logging
from dotenv import load_dotenv

setup_logging(
    log_level="INFO",
    log_file="logs/app.log",
    max_file_size=8 * 1024 * 1024,  # 8MB per file
    backup_count=3,  # Keep 3 old log files
)
load_dotenv()

from core.server import create_server
from sqlalchemy.orm import Session
import uvicorn
import logging
from database import get_db
from fastapi import HTTPException, Request, responses, Form, Depends
import os

# import routers
from features.auditor.router import router as auditor_router
from features.manager.router import router as manager_router
from features.counsellor.router import router as counsellor_router
from features.auth.router import router as auth_router


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_server()


# Include routers
app.include_router(auditor_router, prefix="/api/v1")
app.include_router(manager_router, prefix="/api/v1")
app.include_router(counsellor_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


# Register global error
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return responses.JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "code": exc.status_code},
    )


@app.get("/")
async def root():
    return {"message": "QC backend app is running!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


def main():
    logger.info(
        f"Environment variables loaded successfully, test env: {os.getenv('TEST')}"
    )
    uvicorn.run("main:app")


if __name__ == "__main__":
    main()
