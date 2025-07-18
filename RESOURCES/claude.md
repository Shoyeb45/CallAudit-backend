# requirements.txt
"""
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
"""

# config.py
"""
Configuration management for the FastAPI application.
Handles database connections, environment variables, and application settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
import os


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    # PostgreSQL connection parameters
    postgres_user: str = Field(..., env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(..., env="POSTGRES_DB")
    
    # Connection pool settings for production
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")  # 1 hour
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def database_url(self) -> str:
        """Generate database URL for SQLAlchemy."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


class AppSettings(BaseSettings):
    """Application configuration settings."""
    
    app_name: str = Field(default="FastAPI PostgreSQL App", env="APP_NAME")
    debug: bool = Field(default=False, env="DEBUG")
    version: str = Field(default="1.0.0", env="APP_VERSION")
    api_v1_prefix: str = Field(default="/api/v1", env="API_V1_PREFIX")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_database_settings() -> DatabaseSettings:
    """Get cached database settings instance."""
    return DatabaseSettings()


@lru_cache()
def get_app_settings() -> AppSettings:
    """Get cached application settings instance."""
    return AppSettings()


# database.py
"""
Database connection and session management.
Handles SQLAlchemy engine creation, session management, and connection pooling.
"""
from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging
from typing import Generator

from config import get_database_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database settings
db_settings = get_database_settings()

# Create SQLAlchemy engine with production-grade configuration
engine = create_engine(
    db_settings.database_url,
    # Connection pool settings
    poolclass=QueuePool,
    pool_size=db_settings.pool_size,
    max_overflow=db_settings.max_overflow,
    pool_timeout=db_settings.pool_timeout,
    pool_recycle=db_settings.pool_recycle,
    pool_pre_ping=True,  # Validates connections before use
    # Performance settings
    echo=False,  # Set to True for SQL query logging in development
    future=True,  # Enable SQLAlchemy 2.0 style
)

# Create SessionLocal class
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # Prevent lazy loading issues
)

# Create Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


# Event listeners for connection management
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database-specific optimizations on connection."""
    if 'postgresql' in str(dbapi_connection):
        # Set PostgreSQL-specific optimizations
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = '30s'")
            cursor.execute("SET lock_timeout = '10s'")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Provides a database session for FastAPI dependency injection.
    Automatically handles session cleanup and rollback on errors.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Use this for non-FastAPI database operations.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables():
    """Drop all database tables. Use with caution!"""
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


# models.py
"""
Database models using SQLAlchemy ORM.
Defines the database schema and relationships.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from database import Base


class TimestampMixin:
    """Mixin class to add timestamp fields to models."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class User(Base, TimestampMixin):
    """
    User model for storing user information.
    
    Attributes:
        id: Primary key
        email: Unique user email
        username: Unique username
        full_name: User's full name
        is_active: Whether the user account is active
        is_superuser: Whether the user has admin privileges
        created_at: Timestamp of record creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_username_active', 'username', 'is_active'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class Post(Base, TimestampMixin):
    """
    Post model for storing blog posts or articles.
    
    Attributes:
        id: Primary key
        title: Post title
        content: Post content
        author_id: Foreign key to User
        is_published: Whether the post is published
        created_at: Timestamp of record creation
        updated_at: Timestamp of last update
    """
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    author = relationship("User", back_populates="posts")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_posts_author_published', 'author_id', 'is_published'),
        Index('idx_posts_title_published', 'title', 'is_published'),
    )
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}', author_id={self.author_id})>"


# schemas.py
"""
Pydantic schemas for request/response validation.
Handles data serialization and validation for API endpoints.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")
    is_active: bool = Field(default=True, description="Whether the user account is active")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, description="User's password")


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    email: Optional[EmailStr] = Field(None, description="User's email address")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Unique username")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")
    is_active: Optional[bool] = Field(None, description="Whether the user account is active")


class UserResponse(UserBase):
    """Schema for user response data."""
    id: int
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PostBase(BaseModel):
    """Base post schema with common fields."""
    title: str = Field(..., min_length=1, max_length=200, description="Post title")
    content: str = Field(..., min_length=1, description="Post content")
    is_published: bool = Field(default=False, description="Whether the post is published")


class PostCreate(PostBase):
    """Schema for creating a new post."""
    pass


class PostUpdate(BaseModel):
    """Schema for updating post information."""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Post title")
    content: Optional[str] = Field(None, min_length=1, description="Post content")
    is_published: Optional[bool] = Field(None, description="Whether the post is published")


class PostResponse(PostBase):
    """Schema for post response data."""
    id: int
    author_id: int
    author: UserResponse
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserWithPosts(UserResponse):
    """Schema for user response with posts."""
    posts: List[PostResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


# crud.py
"""
CRUD operations for database models.
Handles Create, Read, Update, Delete operations with proper error handling.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_
from typing import List, Optional, Dict, Any
import logging

from models import User, Post
from schemas import UserCreate, UserUpdate, PostCreate, PostUpdate

logger = logging.getLogger(__name__)


class CRUDUser:
    """CRUD operations for User model."""
    
    def create(self, db: Session, user_data: UserCreate) -> User:
        """
        Create a new user in the database.
        
        Args:
            db: Database session
            user_data: User creation data
            
        Returns:
            Created user instance
            
        Raises:
            IntegrityError: If email or username already exists
        """
        try:
            # Hash password in production (using bcrypt or similar)
            hashed_password = f"hashed_{user_data.password}"  # Replace with actual hashing
            
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                is_active=user_data.is_active,
            )
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            logger.info(f"User created successfully: {db_user.username}")
            return db_user
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise ValueError("Email or username already exists")
    
    def get_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()
    
    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()
    
    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[User]:
        """
        Get multiple users with pagination and filtering.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            is_active: Filter by active status
            
        Returns:
            List of users
        """
        query = db.query(User)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        return query.offset(skip).limit(limit).all()
    
    def update(self, db: Session, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """
        Update user information.
        
        Args:
            db: Database session
            user_id: User ID to update
            user_data: Updated user data
            
        Returns:
            Updated user instance or None if not found
        """
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_user, field, value)
        
        try:
            db.commit()
            db.refresh(db_user)
            logger.info(f"User updated successfully: {db_user.username}")
            return db_user
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to update user: {e}")
            raise ValueError("Email or username already exists")
    
    def delete(self, db: Session, user_id: int) -> bool:
        """
        Delete user by ID.
        
        Args:
            db: Database session
            user_id: User ID to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return False
        
        db.delete(db_user)
        db.commit()
        logger.info(f"User deleted successfully: {user_id}")
        return True


class CRUDPost:
    """CRUD operations for Post model."""
    
    def create(self, db: Session, post_data: PostCreate, author_id: int) -> Post:
        """
        Create a new post in the database.
        
        Args:
            db: Database session
            post_data: Post creation data
            author_id: ID of the post author
            
        Returns:
            Created post instance
        """
        db_post = Post(
            title=post_data.title,
            content=post_data.content,
            author_id=author_id,
            is_published=post_data.is_published,
        )
        
        db.add(db_post)
        db.commit()
        db.refresh(db_post)
        
        logger.info(f"Post created successfully: {db_post.title}")
        return db_post
    
    def get_by_id(self, db: Session, post_id: int) -> Optional[Post]:
        """Get post by ID with author information."""
        return (
            db.query(Post)
            .options(joinedload(Post.author))
            .filter(Post.id == post_id)
            .first()
        )
    
    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        author_id: Optional[int] = None,
        is_published: Optional[bool] = None
    ) -> List[Post]:
        """
        Get multiple posts with pagination and filtering.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            author_id: Filter by author ID
            is_published: Filter by published status
            
        Returns:
            List of posts with author information
        """
        query = db.query(Post).options(joinedload(Post.author))
        
        if author_id is not None:
            query = query.filter(Post.author_id == author_id)
        
        if is_published is not None:
            query = query.filter(Post.is_published == is_published)
        
        return query.offset(skip).limit(limit).all()
    
    def update(self, db: Session, post_id: int, post_data: PostUpdate) -> Optional[Post]:
        """
        Update post information.
        
        Args:
            db: Database session
            post_id: Post ID to update
            post_data: Updated post data
            
        Returns:
            Updated post instance or None if not found
        """
        db_post = self.get_by_id(db, post_id)
        if not db_post:
            return None
        
        update_data = post_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_post, field, value)
        
        db.commit()
        db.refresh(db_post)
        logger.info(f"Post updated successfully: {db_post.title}")
        return db_post
    
    def delete(self, db: Session, post_id: int) -> bool:
        """
        Delete post by ID.
        
        Args:
            db: Database session
            post_id: Post ID to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        db_post = self.get_by_id(db, post_id)
        if not db_post:
            return False
        
        db.delete(db_post)
        db.commit()
        logger.info(f"Post deleted successfully: {post_id}")
        return True


# Initialize CRUD instances
user_crud = CRUDUser()
post_crud = CRUDPost()


# main.py
"""
Main FastAPI application.
Handles API routes, middleware, and application lifecycle.
"""
from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from typing import List, Optional
import logging

from database import get_db, create_tables
from schemas import (
    UserCreate, UserUpdate, UserResponse, UserWithPosts,
    PostCreate, PostUpdate, PostResponse
)
from crud import user_crud, post_crud
from config import get_app_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get app settings
app_settings = get_app_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Handles startup and shutdown operations.
    """
    # Startup
    logger.info("Starting up FastAPI application...")
    create_tables()
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application...")


# Initialize FastAPI app
app = FastAPI(
    title=app_settings.app_name,
    description="FastAPI application with PostgreSQL and SQLAlchemy",
    version=app_settings.version,
    lifespan=lifespan,
    debug=app_settings.debug,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure properly for production
)


# User endpoints
@app.post(
    f"{app_settings.api_v1_prefix}/users/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user account with email, username, and password."
)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    try:
        return user_crud.create(db=db, user_data=user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get(
    f"{app_settings.api_v1_prefix}/users/",
    response_model=List[UserResponse],
    summary="Get users",
    description="Retrieve a list of users with pagination and filtering options."
)
async def get_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    """Get multiple users with pagination."""
    return user_crud.get_multi(db=db, skip=skip, limit=limit, is_active=is_active)


@app.get(
    f"{app_settings.api_v1_prefix}/users/{{user_id}}",
    response_model=UserWithPosts,
    summary="Get user by ID",
    description="Retrieve a specific user by their ID including their posts."
)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID."""
    user = user_crud.get_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@app.put(
    f"{app_settings.api_v1_prefix}/users/{{user_id}}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user information by ID."
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """Update user by ID."""
    try:
        user = user_crud.update(db=db, user_id=user_id, user_data=user_update)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.delete(
    f"{app_settings.api_v1_prefix}/users/{{user_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user by ID."
)
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete user by ID."""
    if not user_crud.delete(db=db, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


# Post endpoints
@app.post(
    f"{app_settings.api_v1_prefix}/posts/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new post",
    description="Create a new post with title and content."
)
async def create_post(
    post: PostCreate,
    author_id: int = Query(..., description="ID of the post author"),
    db: Session = Depends(get_db)
):
    """Create a new post."""
    # Verify author exists
    author = user_crud.get_by_id(db=db, user_id=author_id)
    if not author:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Author not found"
        )
    
    return post_crud.create(db=db, post_data=post, author_id=author_id)


@app.get(
    f"{app_settings.api_v1_prefix}/posts/",
    response_model=List[PostResponse],
    summary="Get posts",
    description="Retrieve a list of posts with pagination and filtering options."
)
async def get_posts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    author_id: Optional[int] = Query(None, description="Filter by author ID"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    db: Session = Depends(get_db)
):
    """Get multiple posts with pagination."""
    return post_crud.get_multi(
        db=db, 
        skip=skip, 
        limit=limit, 
        author_id=author_id,
        is_published=is_published
    )


@app.get(
    f"{app_settings.api_v1_prefix}/posts/{{post_id}}",
    response_model=PostResponse,
    summary="Get post by ID",
    description="Retrieve a specific post by its ID."
)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get post by ID."""
    post = post_crud.get_by_id(db=db, post_id=post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post


@app.put(
    f"{app_settings.api_v1_prefix}/posts/{{post_id}}",
    response_model=PostResponse,
    summary="Update post",
    description="Update post information by ID."
)
async def update_post(
    post_id: int,
    post_update: PostUpdate,
    db: Session = Depends(get_db)
):
    """Update post by ID."""
    post = post_crud.update(db=db, post_id=post_id, post_data=post_update)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )
    return post


@app.delete(
    f"{app_settings.api_v1_prefix}/posts/{{post_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete post",
    description="Delete a post by ID."
)
async def delete_post(post_id: int, db: Session = Depends(get_db)):
    """Delete post by ID."""
    if not post_crud.delete(db=db, post_id=post_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )


# Health check endpoint
@app.get("/health", summary="Health check", description="Check application health status.")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Service is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_settings.debug,
        log_level="info"
    )


# alembic.ini
"""
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://user:password@localhost/dbname

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 79 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""


# alembic/env.py
"""
Alembic environment configuration for database migrations.
Handles migration environment setup and database connection.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from config import get_database_settings
from models import Base

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add model metadata for autogenerate support
target_metadata = Base.metadata

# Get database settings
db_settings = get_database_settings()

# Override sqlalchemy.url with environment variable
config.set_main_option("sqlalchemy.url", db_settings.database_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    This configures the context with just a URL and not an Engine.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


# middleware.py
"""
Custom middleware for the FastAPI application.
Handles request/response logging, timing, and security headers.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import uuid

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    Adds request ID, timing, and detailed logging for monitoring.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and response with logging.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler
            
        Returns:
            HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Log request details
        logger.info(
            f"Request started - ID: {request_id}, "
            f"Method: {request.method}, "
            f"URL: {request.url}, "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response details
            logger.info(
                f"Request completed - ID: {request_id}, "
                f"Status: {response.status_code}, "
                f"Time: {process_time:.4f}s"
            )
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed - ID: {request_id}, "
                f"Error: {str(e)}, "
                f"Time: {process_time:.4f}s"
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.
    Implements common security headers for production deployment.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler
            
        Returns:
            HTTP response with security headers
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


# exceptions.py
"""
Custom exception handlers for the FastAPI application.
Provides consistent error responses and logging.
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class BusinessLogicError(Exception):
    """Custom exception for business logic errors."""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


async def database_exception_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """
    Handle database-related exceptions.
    
    Args:
        request: HTTP request
        exc: Database exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(
        f"Database error - Request ID: {request_id}, "
        f"Error: {exc.message}, "
        f"Details: {exc.details}"
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database error",
            "message": "An error occurred while processing your request",
            "request_id": request_id,
            "type": "database_error"
        }
    )


async def business_logic_exception_handler(request: Request, exc: BusinessLogicError) -> JSONResponse:
    """
    Handle business logic exceptions.
    
    Args:
        request: HTTP request
        exc: Business logic exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.warning(
        f"Business logic error - Request ID: {request_id}, "
        f"Error: {exc.message}, "
        f"Code: {exc.code}"
    )
    
    return JSONResponse(
        status_code=400,
        content={
            "error": "Business logic error",
            "message": exc.message,
            "code": exc.code,
            "request_id": request_id,
            "type": "business_logic_error"
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation exceptions.
    
    Args:
        request: HTTP request
        exc: Validation exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.warning(
        f"Validation error - Request ID: {request_id}, "
        f"Errors: {exc.errors()}"
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": request_id,
            "type": "validation_error"
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions.
    
    Args:
        request: HTTP request
        exc: HTTP exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.warning(
        f"HTTP error - Request ID: {request_id}, "
        f"Status: {exc.status_code}, "
        f"Detail: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP error",
            "message": exc.detail,
            "request_id": request_id,
            "type": "http_error"
        }
    )


# utils.py
"""
Utility functions for the FastAPI application.
Contains helper functions for common operations.
"""
import hashlib
import secrets
import string
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import re


def generate_password_hash(password: str) -> str:
    """
    Generate a secure password hash.
    In production, use bcrypt or similar library.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    # This is a simplified example - use bcrypt in production
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{password_hash.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        password: Plain text password
        hashed_password: Stored password hash
        
    Returns:
        True if password matches
    """
    try:
        salt, hash_hex = hashed_password.split(':')
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_hash.hex() == hash_hex
    except ValueError:
        return False


def generate_random_string(length: int = 32) -> str:
    """
    Generate a random string for tokens or IDs.
    
    Args:
        length: Length of the string
        
    Returns:
        Random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}

    return re.match(pattern, email) is not None


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    Sanitize input string.
    
    Args:
        text: Input text
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not isinstance(text, str):
        return ""
    
    # Remove null bytes and control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def paginate_query_params(skip: int = 0, limit: int = 100) -> Dict[str, int]:
    """
    Validate and normalize pagination parameters.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records
        
    Returns:
        Normalized pagination parameters
    """
    skip = max(0, skip)
    limit = min(max(1, limit), 1000)  # Max 1000 records per page
    
    return {"skip": skip, "limit": limit}


def calculate_offset_limit(page: int, page_size: int) -> Dict[str, int]:
    """
    Calculate offset and limit from page and page_size.
    
    Args:
        page: Page number (1-based)
        page_size: Number of records per page
        
    Returns:
        Dictionary with skip and limit values
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 1000)
    skip = (page - 1) * page_size
    
    return {"skip": skip, "limit": page_size}


# .env.example
"""
# Database Configuration
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database_name

# Database Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Application Settings
APP_NAME=FastAPI PostgreSQL App
DEBUG=False
APP_VERSION=1.0.0
API_V1_PREFIX=/api/v1

# Security Settings
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
"""


# docker-compose.yml
"""
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 5

  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_HOST=db
      - POSTGRES_PORT=5432
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - ./app:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
"""


# Dockerfile
"""
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""


# tests/conftest.py
"""
Pytest configuration and fixtures for testing.
Provides database fixtures and test utilities.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os

from database import Base, get_db
from main import app


# Test database URL
TEST_DATABASE_URL = "postgresql://test_user:test_password@localhost/test_db"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client."""
    def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# tests/test_users.py
"""
Test cases for user-related endpoints.
"""
import pytest
from fastapi import status


class TestUsers:
    """Test cases for user endpoints."""
    
    def test_create_user(self, client):
        """Test user creation."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        
        response = client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "created_at" in data
    
    def test_get_users(self, client):
        """Test getting users list."""
        response = client.get("/api/v1/users/")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_user_by_id(self, client):
        """Test getting user by ID."""
        # First create a user
        user_data = {
            "email": "test2@example.com",
            "username": "testuser2",
            "password": "testpassword123",
            "full_name": "Test User 2"
        }
        
        create_response = client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]
        
        # Get the user
        response = client.get(f"/api/v1/users/{user_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == user_data["email"]
    
    def test_get_nonexistent_user(self, client):
        """Test getting non-existent user."""
        response = client.get("/api/v1/users/99999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_user(self, client):
        """Test updating user."""
        # First create a user
        user_data = {
            "email": "test3@example.com",
            "username": "testuser3",
            "password": "testpassword123",
            "full_name": "Test User 3"
        }
        
        create_response = client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]
        
        # Update the user
        update_data = {"full_name": "Updated Name"}
        response = client.put(f"/api/v1/users/{user_id}", json=update_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Updated Name"
    
    def test_delete_user(self, client):
        """Test deleting user."""
        # First create a user
        user_data = {
            "email": "test4@example.com",
            "username": "testuser4",
            "password": "testpassword123",
            "full_name": "Test User 4"
        }
        
        create_response = client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]
        
        # Delete the user
        response = client.delete(f"/api/v1/users/{user_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify user is deleted
        get_response = client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND


# Makefile
"""
.PHONY: install dev test clean migrate upgrade downgrade

install:
	pip install -r requirements.txt

dev:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=. --cov-report=html

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

migrate:
	alembic revision --autogenerate -m "$(message)"

upgrade:
	alembic upgrade head

downgrade:
	alembic downgrade -1

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

format:
	black .
	isort .

lint:
	flake8 .
	mypy .
"""