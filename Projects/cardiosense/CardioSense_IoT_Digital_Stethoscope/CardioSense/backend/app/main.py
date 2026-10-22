"""
CardioSense FastAPI backend.

Educational prototype — not a medical diagnostic device.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import List, Optional
from datetime import timedelta

from dotenv import load_dotenv
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import __version__
from .bridge import bridge
from .auth import (
    SESSION_COOKIE,
    clear_session,
    create_session,
    get_current_user,
    get_user_for_token,
    hash_password,
    require_role,
    token_digest,
    verify_password,
)
from .database import SessionLocal, get_db, init_db, recordings_dir
from .models import (
    DeviceStatus,
    DoctorNotification,
    HealthOut,
    PatientDoctorGrant,
    PatientShareCode,
    Recording,
    RecordingCreate,
    RecordingOut,
    User,
    utc_now,
)
from .recordings import write_wav
from .signal_processing import assess_signal_quality, estimate_bpm, process_pipeline, spectrum
from .websocket import audio_websocket_endpoint, hub

load_dotenv()

NOTICE = "Educational prototype — not a medical diagnostic device."

app = FastAPI(
    title="CardioSense API",
    description=(
        "IoT digital stethoscope backend (educational prototype). "
        "Not for diagnosis, emergency use, or clinical decision-making."
    ),
    version=__version__,
)

origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,"
        "http://localhost:5174,http://127.0.0.1:5175,http://localhost:5175",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    recordings_dir()


# Note: lifespan migration optional; on_event kept for broad FastAPI compatibility.


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        service="cardiosense-backend",
        version=__version__,
        notice=NOTICE,
    )


class RegisterIn(BaseModel):
    email: str
    name: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class RedeemShareIn(BaseModel):
    code: str


def _public_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@app.post("/api/auth/register", status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    return _register_user(body, response, db, role="patient")


@app.post("/api/auth/register/doctor", status_code=201)
def register_doctor(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    return _register_user(body, response, db, role="doctor")


def _register_user(body: RegisterIn, response: Response, db: Session, role: str):
    email = body.email.strip().lower()
    name = body.name.strip()
    if len(email) > 254 or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if not name or len(name) > 120:
        raise HTTPException(status_code=422, detail="Name must be between 1 and 120 characters.")
    if len(body.password) < 12 or len(body.password) > 256:
        raise HTTPException(status_code=422, detail="Password must be between 12 and 256 characters.")
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=email, name=name, role=role, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    create_session(db, user, response)
    return _public_user(user)


@app.post("/api/auth/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    create_session(db, user, response)
    return _public_user(user)


@app.post("/api/auth/logout")
def logout(
    response: Response,
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
):
    clear_session(db, token, response)
    return {"ok": True}


@app.get("/api/auth/me")
def current_user(user: User = Depends(get_current_user)):
    return _public_user(user)


@app.get("/api/device/status", response_model=DeviceStatus)
def device_status(user: User = Depends(get_current_user)) -> DeviceStatus:
    d = hub.state.to_dict()
    return DeviceStatus(**{k: v for k, v in d.items() if k in DeviceStatus.model_fields})


class DeviceConnectIn(BaseModel):
    host: str
    port: int = 81
    path: str = "/"


@app.post("/api/device/connect")
async def connect_device(body: DeviceConnectIn, user: User = Depends(get_current_user)):
    """Connect backend bridge to ESP32 WebSocket server (default port 81)."""
    host = body.host.strip()
    if not host or len(host) > 253:
        raise HTTPException(status_code=400, detail="Invalid IP or hostname.")
    try:
        url = await bridge.start(host, body.port, body.path or "/")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to start bridge: {exc}") from exc
    return {"ok": True, "url": url, "active": bridge.active, "notice": NOTICE}


@app.post("/api/device/disconnect")
async def disconnect_device(user: User = Depends(get_current_user)):
    await bridge.stop()
    hub.state.connected = False
    return {"ok": True, "active": False}


@app.websocket("/ws/audio")
async def ws_audio(websocket: WebSocket) -> None:
    token = websocket.cookies.get(SESSION_COOKIE)
    db = SessionLocal()
    try:
        user = get_user_for_token(db, token)
    finally:
        db.close()
    if not user:
        await websocket.close(code=4401, reason="Sign in required.")
        return
    if user.role != "patient":
        await websocket.close(code=4403, reason="Patient live-monitor access only.")
        return
    await audio_websocket_endpoint(websocket)


def _recording_out(rec: Recording) -> RecordingOut:
    return RecordingOut(
        id=rec.id,
        created_at=rec.created_at,
        duration_sec=rec.duration_sec,
        sample_rate=rec.sample_rate,
        sample_count=rec.sample_count,
        device_id=rec.device_id,
        estimated_bpm=rec.estimated_bpm,
        signal_quality=rec.signal_quality,
        filename=rec.filename,
        notes=rec.notes,
        download_url=f"/api/recordings/{rec.id}/download",
    )


@app.post("/api/recordings", response_model=RecordingOut)
def create_recording(
    body: RecordingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecordingOut:
    if not body.samples:
        raise HTTPException(status_code=400, detail="No samples provided.")
    if body.sample_rate <= 0 or body.sample_rate > 96000:
        raise HTTPException(status_code=400, detail="Invalid sample rate.")

    try:
        quality = assess_signal_quality(body.samples, float(body.sample_rate))
        hr = estimate_bpm(body.samples, float(body.sample_rate))
        bpm = body.estimated_bpm if body.estimated_bpm is not None else (hr.bpm if hr.valid else None)
        qlabel = body.signal_quality if body.signal_quality not in ("Unknown", "") else quality.label

        # Temporary name; finalize after DB id
        tmp_name = f"tmp_{os.getpid()}.wav"
        meta = write_wav(recordings_dir() / tmp_name, body.samples, body.sample_rate)

        rec = Recording(
            duration_sec=meta["duration_sec"],
            sample_rate=body.sample_rate,
            sample_count=meta["sample_count"],
            device_id=body.device_id or "unknown",
            estimated_bpm=bpm,
            signal_quality=qlabel,
            filename=tmp_name,
            notes=body.notes,
            owner_user_id=user.id,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        final_name = f"recording_{rec.id}.wav"
        final_path = recordings_dir() / final_name
        Path(meta["path"]).replace(final_path)
        rec.filename = final_name
        db.add(rec)
        shared_grants = db.query(PatientDoctorGrant).filter_by(patient_id=user.id).all()
        for grant in shared_grants:
            db.add(
                DoctorNotification(
                    doctor_id=grant.doctor_id,
                    patient_id=user.id,
                    kind="new_recording",
                    message=f"{user.name} shared a new recording with you.",
                )
            )
        db.commit()
        db.refresh(rec)
        return _recording_out(rec)
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Recording failure: {exc}") from exc


@app.get("/api/recordings", response_model=List[RecordingOut])
def list_recordings(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> List[RecordingOut]:
    rows = (
        db.query(Recording)
        .filter(Recording.owner_user_id == user.id)
        .order_by(Recording.created_at.desc())
        .all()
    )
    return [_recording_out(r) for r in rows]


def _can_view_recording(db: Session, user: User, rec: Recording) -> bool:
    if rec.owner_user_id == user.id:
        return True
    if user.role != "doctor" or rec.owner_user_id is None:
        return False
    return (
        db.query(PatientDoctorGrant)
        .filter_by(patient_id=rec.owner_user_id, doctor_id=user.id)
        .first()
        is not None
    )


@app.get("/api/recordings/{recording_id}", response_model=RecordingOut)
def get_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecordingOut:
    rec = db.get(Recording, recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found.")
    if not _can_view_recording(db, user, rec):
        raise HTTPException(status_code=403, detail="You do not have access to this recording.")
    return _recording_out(rec)


@app.get("/api/recordings/{recording_id}/download")
def download_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.get(Recording, recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found.")
    if not _can_view_recording(db, user, rec):
        raise HTTPException(status_code=403, detail="You do not have access to this recording.")
    path = recordings_dir() / rec.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="WAV file missing on disk.")
    return FileResponse(path, media_type="audio/wav", filename=rec.filename)


@app.delete("/api/recordings/{recording_id}")
def delete_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.get(Recording, recording_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found.")
    if rec.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the recording owner can delete it.")
    path = recordings_dir() / rec.filename
    try:
        if path.exists():
            path.unlink()
        db.delete(rec)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}") from exc
    return {"ok": True, "id": recording_id}


@app.post("/api/analyze")
def analyze(body: RecordingCreate, user: User = Depends(get_current_user)):
    if not body.samples:
        raise HTTPException(status_code=400, detail="No samples provided.")
    result = process_pipeline(body.samples, float(body.sample_rate))
    spec = spectrum(body.samples, float(body.sample_rate))
    return {"analysis": result, "spectrum": spec, "notice": NOTICE}


@app.post("/api/shares")
def create_share_code(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_role(user, "patient")
    code = secrets.token_urlsafe(9)
    db.add(
        PatientShareCode(
            patient_id=user.id,
            code_hash=token_digest(code),
            expires_at=utc_now() + timedelta(minutes=15),
        )
    )
    db.commit()
    return {"code": code, "expires_in_seconds": 900}


@app.post("/api/shares/redeem")
def redeem_share_code(
    body: RedeemShareIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_role(user, "doctor")
    share = (
        db.query(PatientShareCode)
        .filter_by(code_hash=token_digest(body.code.strip()), used_at=None)
        .first()
    )
    if not share or share.expires_at <= utc_now():
        raise HTTPException(status_code=400, detail="Share code is invalid or expired.")
    share.used_at = utc_now()
    if not db.query(PatientDoctorGrant).filter_by(patient_id=share.patient_id, doctor_id=user.id).first():
        db.add(PatientDoctorGrant(patient_id=share.patient_id, doctor_id=user.id))
    db.commit()
    patient = db.get(User, share.patient_id)
    return {"patient": _public_user(patient)}


@app.get("/api/shares")
def list_patient_shares(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_role(user, "patient")
    grants = db.query(PatientDoctorGrant).filter_by(patient_id=user.id).all()
    doctors = [db.get(User, grant.doctor_id) for grant in grants]
    return [_public_user(doctor) for doctor in doctors if doctor]


@app.delete("/api/shares/{doctor_id}")
def revoke_patient_share(
    doctor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_role(user, "patient")
    grant = db.query(PatientDoctorGrant).filter_by(patient_id=user.id, doctor_id=doctor_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Doctor access not found.")
    db.add(
        DoctorNotification(
            doctor_id=doctor_id,
            patient_id=user.id,
            kind="access_revoked",
            message=f"{user.name} revoked your access to their recordings.",
        )
    )
    db.delete(grant)
    db.commit()
    return {"ok": True}


@app.get("/api/doctor/patients")
def doctor_patients(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_role(user, "doctor")
    grants = db.query(PatientDoctorGrant).filter_by(doctor_id=user.id).all()
    patients = [db.get(User, grant.patient_id) for grant in grants]
    return [_public_user(patient) for patient in patients if patient]


@app.get("/api/doctor/notifications")
def doctor_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_role(user, "doctor")
    rows = (
        db.query(DoctorNotification)
        .filter_by(doctor_id=user.id)
        .order_by(DoctorNotification.created_at.desc(), DoctorNotification.id.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": row.id,
            "patient_id": row.patient_id,
            "kind": row.kind,
            "message": row.message,
            "created_at": row.created_at,
            "read": row.read_at is not None,
        }
        for row in rows
    ]


@app.put("/api/doctor/notifications/{notification_id}/read")
def mark_doctor_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_role(user, "doctor")
    notification = (
        db.query(DoctorNotification)
        .filter_by(id=notification_id, doctor_id=user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if notification.read_at is None:
        notification.read_at = utc_now()
        db.commit()
    return {"ok": True, "id": notification_id}


@app.get("/api/doctor/patients/{patient_id}/recordings", response_model=List[RecordingOut])
def doctor_patient_recordings(
    patient_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_role(user, "doctor")
    grant = db.query(PatientDoctorGrant).filter_by(patient_id=patient_id, doctor_id=user.id).first()
    if not grant:
        raise HTTPException(status_code=403, detail="The patient has not shared recordings with you.")
    rows = (
        db.query(Recording)
        .filter(Recording.owner_user_id == patient_id)
        .order_by(Recording.created_at.desc())
        .all()
    )
    return [_recording_out(row) for row in rows]


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Backend error", "message": str(exc), "notice": NOTICE},
    )
