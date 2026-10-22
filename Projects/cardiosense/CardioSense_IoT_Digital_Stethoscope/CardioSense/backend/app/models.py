from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    duration_sec: Mapped[float] = mapped_column(Float, default=0.0)
    sample_rate: Mapped[int] = mapped_column(Integer, default=4000)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    device_id: Mapped[str] = mapped_column(String(128), default="unknown")
    estimated_bpm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    signal_quality: Mapped[str] = mapped_column(String(32), default="No Signal")
    filename: Mapped[str] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(16))
    password_hash: Mapped[str] = mapped_column(String(256))


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class PatientDoctorGrant(Base):
    __tablename__ = "patient_doctor_grants"
    __table_args__ = (UniqueConstraint("patient_id", "doctor_id", name="uq_patient_doctor_grant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class PatientShareCode(Base):
    __tablename__ = "patient_share_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class DoctorNotification(Base):
    __tablename__ = "doctor_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    patient_id: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class RecordingCreate(BaseModel):
    device_id: str = "unknown"
    sample_rate: int = 4000
    samples: list[float] = Field(default_factory=list)
    estimated_bpm: Optional[float] = None
    signal_quality: str = "Unknown"
    notes: Optional[str] = None


class RecordingOut(BaseModel):
    id: int
    created_at: datetime
    duration_sec: float
    sample_rate: int
    sample_count: int
    device_id: str
    estimated_bpm: Optional[float]
    signal_quality: str
    filename: str
    notes: Optional[str] = None
    download_url: str

    model_config = {"from_attributes": True}


class DeviceStatus(BaseModel):
    connected: bool = False
    device_id: str = "unknown"
    ip: Optional[str] = None
    rssi: Optional[int] = None
    sample_rate: int = 4000
    packets_received: int = 0
    last_seen: Optional[datetime] = None
    wifi_connected: bool = False
    bpm: Optional[float] = None
    signal_quality: str = "No Signal"
    notice: str = "Educational prototype — not a medical diagnostic device."


class HealthOut(BaseModel):
    status: str
    service: str
    version: str
    notice: str
