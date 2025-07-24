from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class Manager(Base):
    __tablename__ = "managers"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=True)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    auditors = relationship("Auditor", back_populates="manager")
    counsellors = relationship("Counsellor", back_populates="manager")
    calls = relationship("Call", back_populates="manager")
    audit_reports = relationship("AuditReport", back_populates="manager")
    leads = relationship("Lead", back_populates="manager")


class Auditor(Base):
    __tablename__ = "auditors"

    id = Column(String, primary_key=True, default=generate_uuid)
    manager_id = Column(String, ForeignKey("managers.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=True)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    manager = relationship("Manager", back_populates="auditors")
    counsellors = relationship(
        "Counsellor", back_populates="auditor", cascade="all, delete-orphan"
    )
    calls = relationship(
        "Call",
        back_populates="auditor",
        cascade="all, delete-orphan",  # ensures ORM-level cascade
        passive_deletes=True,  # defers to database to handle deletes
    )
    audit_reports = relationship("AuditReport", back_populates="auditor")
    leads = relationship("Lead", back_populates="auditor")


class Counsellor(Base):
    __tablename__ = "counsellors"

    id = Column(String, primary_key=True, default=generate_uuid)
    auditor_id = Column(
        String, ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False
    )
    manager_id = Column(String, ForeignKey("managers.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    auditor = relationship("Auditor", back_populates="counsellors")
    manager = relationship("Manager", back_populates="counsellors")
    calls = relationship(
        "Call",
        back_populates="counsellor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    leads = relationship(
        "Lead",
        back_populates="counsellor",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Call(Base):
    __tablename__ = "calls"

    id = Column(String, primary_key=True, default=generate_uuid)
    counsellor_id = Column(
        String, ForeignKey("counsellors.id", ondelete="CASCADE"), nullable=False
    )
    auditor_id = Column(
        String, ForeignKey("auditors.id", ondelete="CASCADE"), nullable=False
    )
    manager_id = Column(String, ForeignKey("managers.id"), nullable=False)
    call_start = Column(DateTime, nullable=False)
    call_end = Column(DateTime)
    duration = Column(Integer)  # Duration in seconds
    call_type = Column(String, nullable=True)
    client_number = Column(String, nullable=False)
    recording_url = Column(String)
    is_audited = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    audit_score = Column(Float, default=0.0)
    tags = Column(String, default="")  # JSON string or comma-separated values
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    counsellor = relationship("Counsellor", back_populates="calls")
    auditor = relationship("Auditor", back_populates="calls")
    manager = relationship("Manager", back_populates="calls")
    call_analysis = relationship("CallAnalysis", back_populates="call", uselist=False)
    audit_reports = relationship("AuditReport", back_populates="call")


class CallAnalysis(Base):
    __tablename__ = "call_analysis"

    id = Column(String, primary_key=True, default=generate_uuid)
    call_id = Column(String, ForeignKey("calls.id"), nullable=False, unique=True)
    sentiment_score = Column(Float, default=0.0)
    transcript = Column(Text, nullable=True)
    summary = Column(Text)
    anomalies = Column(Text, nullable=True)
    keywords = Column(String, default="")  # JSON string or comma-separated values
    ai_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    call = relationship("Call", back_populates="call_analysis")


class AuditReport(Base):
    __tablename__ = "audit_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    call_id = Column(String, ForeignKey("calls.id"), nullable=False)
    auditor_id = Column(String, ForeignKey("auditors.id"), nullable=False)
    manager_id = Column(String, ForeignKey("managers.id"), nullable=False)
    score = Column(Float, nullable=False)
    comments = Column(Text, nullable=True)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    call = relationship("Call", back_populates="audit_reports")
    auditor = relationship("Auditor", back_populates="audit_reports")
    manager = relationship("Manager", back_populates="audit_reports")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=generate_uuid)
    counsellor_id = Column(
        String, ForeignKey("counsellors.id", ondelete="CASCADE"), nullable=False
    )
    auditor_id = Column(String, ForeignKey("auditors.id"), nullable=False)
    manager_id = Column(String, ForeignKey("managers.id"), nullable=False)
    client_name = Column(String, nullable=True)
    client_number = Column(String, nullable=True)
    status = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships

    counsellor = relationship("Counsellor", back_populates="leads")
    auditor = relationship("Auditor", back_populates="leads")
    manager = relationship("Manager", back_populates="leads")
