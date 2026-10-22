"""Backend API tests."""

from __future__ import annotations

import math
import struct
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.main import app
from app.websocket import AudioHub, PACKET_MAGIC, hub
from app.auth import hash_password
from app.database import SessionLocal
from app.models import User


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("RECORDINGS_DIR", str(rec_dir))

    # Re-init engine/db for test isolation
    from app import database
    from app.models import Base

    database.engine = database.create_db_engine()
    database.SessionLocal.configure(bind=database.engine)
    Base.metadata.drop_all(bind=database.engine)
    Base.metadata.create_all(bind=database.engine)

    hub.state.packets_received = 0
    hub.state.connected = False
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "not a medical" in body["notice"].lower()


def test_device_status(client):
    register_patient(client)
    r = client.get("/api/device/status")
    assert r.status_code == 200
    assert "signal_quality" in r.json()


def register_patient(client, email="patient@example.test"):
    response = client.post(
        "/api/auth/register",
        json={"name": "Test Patient", "email": email, "password": "test-password-123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_recordings_crud(client):
    register_patient(client)
    sr = 4000
    t = np.arange(0, 1.0, 1 / sr)
    samples = (100 * np.sin(2 * np.pi * 80 * t)).tolist()
    created = client.post(
        "/api/recordings",
        json={
            "device_id": "test-device",
            "sample_rate": sr,
            "samples": samples,
            "signal_quality": "Fair",
        },
    )
    assert created.status_code == 200, created.text
    rec = created.json()
    rid = rec["id"]

    listed = client.get("/api/recordings")
    assert listed.status_code == 200
    assert any(x["id"] == rid for x in listed.json())

    got = client.get(f"/api/recordings/{rid}")
    assert got.status_code == 200

    dl = client.get(f"/api/recordings/{rid}/download")
    assert dl.status_code == 200
    assert dl.content[:4] == b"RIFF"

    deleted = client.delete(f"/api/recordings/{rid}")
    assert deleted.status_code == 200


def test_authentication_and_patient_doctor_sharing(client):
    patient = register_patient(client)
    sr = 4000
    samples = (100 * np.sin(2 * np.pi * 80 * np.arange(0, 1.0, 1 / sr))).tolist()
    recording = client.post(
        "/api/recordings",
        json={"sample_rate": sr, "samples": samples, "signal_quality": "Fair"},
    )
    assert recording.status_code == 200

    code_response = client.post("/api/shares")
    assert code_response.status_code == 200
    code = code_response.json()["code"]

    db = SessionLocal()
    try:
        db.add(User(email="doctor@example.test", name="Test Doctor", role="doctor", password_hash=hash_password("doctor-password-123")))
        db.commit()
    finally:
        db.close()

    assert client.post("/api/auth/logout").status_code == 200
    doctor_login = client.post("/api/auth/login", json={"email": "doctor@example.test", "password": "doctor-password-123"})
    assert doctor_login.status_code == 200
    assert doctor_login.json()["role"] == "doctor"
    assert client.post("/api/shares/redeem", json={"code": code}).status_code == 200
    patients = client.get("/api/doctor/patients").json()
    assert [entry["id"] for entry in patients] == [patient["id"]]

    visible = client.get(f"/api/doctor/patients/{patient['id']}/recordings")
    assert visible.status_code == 200
    assert [entry["id"] for entry in visible.json()] == [recording.json()["id"]]
    assert client.get(f"/api/recordings/{recording.json()['id']}/download").status_code == 200

    assert client.post("/api/auth/logout").status_code == 200
    patient_login = client.post(
        "/api/auth/login",
        json={"email": "patient@example.test", "password": "test-password-123"},
    )
    assert patient_login.status_code == 200
    new_recording = client.post(
        "/api/recordings",
        json={"sample_rate": sr, "samples": samples, "signal_quality": "Fair"},
    )
    assert new_recording.status_code == 200
    assert client.post("/api/auth/logout").status_code == 200

    doctor_login = client.post("/api/auth/login", json={"email": "doctor@example.test", "password": "doctor-password-123"})
    assert doctor_login.status_code == 200
    notifications = client.get("/api/doctor/notifications")
    assert notifications.status_code == 200
    assert len(notifications.json()) == 1
    notification = notifications.json()[0]
    assert notification["kind"] == "new_recording"
    assert notification["read"] is False
    assert client.put(f"/api/doctor/notifications/{notification['id']}/read").status_code == 200
    assert client.get("/api/doctor/notifications").json()[0]["read"] is True

    assert client.post("/api/auth/logout").status_code == 200
    patient_login = client.post(
        "/api/auth/login",
        json={"email": "patient@example.test", "password": "test-password-123"},
    )
    assert patient_login.status_code == 200
    assert client.delete(f"/api/shares/{doctor_login.json()['id']}").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200

    doctor_login = client.post("/api/auth/login", json={"email": "doctor@example.test", "password": "doctor-password-123"})
    assert doctor_login.status_code == 200
    notifications = client.get("/api/doctor/notifications").json()
    assert notifications[0]["kind"] == "access_revoked"
    assert client.get(f"/api/doctor/patients/{patient['id']}/recordings").status_code == 403

    assert client.post("/api/auth/logout").status_code == 200
    other = client.post("/api/auth/register", json={
        "name": "Other Patient",
        "email": "other@example.test",
        "password": "other-password-123",
    })
    assert other.status_code == 201
    assert client.get(f"/api/recordings/{recording.json()['id']}").status_code == 403


def test_doctor_can_register_from_login_page(client):
    response = client.post(
        "/api/auth/register/doctor",
        json={
            "name": "New Doctor",
            "email": "new-doctor@example.test",
            "password": "doctor-password-123",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "doctor"
    assert client.get("/api/auth/me").json()["role"] == "doctor"
    assert client.get("/api/doctor/patients").status_code == 200


def test_private_routes_require_authentication(client):
    assert client.get("/api/device/status").status_code == 401
    assert client.get("/api/recordings").status_code == 401
    assert client.post("/api/analyze", json={"samples": [0.0], "sample_rate": 4000}).status_code == 401


def test_websocket_audio_packet(client):
    register_patient(client)
    count = 64
    samples = [int(100 * math.sin(i / 5.0)) for i in range(count)]
    header = bytearray(32)
    struct.pack_into("<I", header, 0, PACKET_MAGIC)
    header[4] = 1
    header[5] = 1
    struct.pack_into("<H", header, 6, count)
    struct.pack_into("<I", header, 8, 7)
    struct.pack_into("<f", header, 12, 4000.0)
    struct.pack_into("<f", header, 16, 12.0)
    struct.pack_into("<f", header, 20, 40.0)
    struct.pack_into("<f", header, 24, float("nan"))
    header[28] = 2
    payload = bytes(header) + struct.pack(f"<{count}h", *samples)

    with client.websocket_connect("/ws/audio") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        _ = ws.receive_json()  # device_status
        ws.send_bytes(payload)
        msg = ws.receive_json()
        assert msg["type"] == "audio"
        assert len(msg["samples"]) == count
        assert msg["sequence"] == 7


@pytest.mark.asyncio
async def test_legacy_json_sample_is_forwarded():
    audio_hub = AudioHub()
    messages = []

    async def capture(message):
        messages.append(message)

    audio_hub.broadcast = capture
    await audio_hub.handle_legacy_sample(
        {"sample": 8, "rms": 20.6, "peak": 61.0, "bpm": 67.9, "quality": "Fair"}
    )

    assert audio_hub.state.connected
    assert audio_hub.state.packets_received == 1
    assert messages[0]["type"] == "audio"
    assert messages[0]["samples"] == [8.0]
    assert messages[0]["bpm"] == 67.9
