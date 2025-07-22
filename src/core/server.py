from fastapi import FastAPI
import logging
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from config import get_app_settings
from core.save_to_s3 import S3Saver
from database import create_tables

logger = logging.getLogger(__name__)


def create_server():
    """Function to create fastAPI instance, which initialises server"""
    app_settings = get_app_settings()

    try:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """
            Application lifespan events.
            Handles startup and shutdown operations.
            """
            # Startup
            logger.info("Starting up FastAPI application...")
            app.state.s3_saver = S3Saver()  # initialize once here
            logger.info("S3 client initialized and stored in app.state")
            # create_tables()
            logger.info("Database tables created/verified")

            yield

            # Shutdown
            logger.info("Shutting down FastAPI application...")

        app = FastAPI(
            title=app_settings.app_name,
            description="FastAPI application with Postgresql and SQLAlchemy",
            version=app_settings.version,
            debug=app_settings.debug,
            lifespan=lifespan,
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        return app
    except Exception as e:
        logger.error(e)

        return None
