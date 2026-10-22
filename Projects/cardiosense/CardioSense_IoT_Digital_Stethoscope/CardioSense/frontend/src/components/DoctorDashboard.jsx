import React, { useEffect, useState } from 'react';
import {
  downloadUrl,
  listDoctorNotifications,
  listDoctorPatients,
  listPatientRecordings,
  markDoctorNotificationRead,
  redeemShareCode,
} from '../services/api';

export default function DoctorDashboard() {
  const [patients, setPatients] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [selected, setSelected] = useState(null);
  const [recordings, setRecordings] = useState([]);
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [notificationError, setNotificationError] = useState('');
  const [busy, setBusy] = useState(false);
  const [notificationsBusy, setNotificationsBusy] = useState(false);

  const refreshPatients = async () => {
    try {
      const rows = await listDoctorPatients();
      setPatients(rows);
      if (selected && !rows.some((patient) => patient.id === selected.id)) {
        setSelected(null);
        setRecordings([]);
      }
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  const refreshNotifications = async () => {
    setNotificationsBusy(true);
    try {
      setNotifications(await listDoctorNotifications());
      setNotificationError('');
    } catch (err) {
      setNotificationError(err.message);
    } finally {
      setNotificationsBusy(false);
    }
  };

  useEffect(() => {
    refreshPatients();
    refreshNotifications();
    const timer = setInterval(refreshNotifications, 30000);
    return () => clearInterval(timer);
  }, []);

  const markAsRead = async (notificationId) => {
    try {
      await markDoctorNotificationRead(notificationId);
      setNotifications((current) => current.map((item) => (
        item.id === notificationId ? { ...item, read: true } : item
      )));
      setNotificationError('');
    } catch (err) {
      setNotificationError(err.message);
    }
  };

  const unreadCount = notifications.filter((item) => !item.read).length;

  const selectPatient = async (patient) => {
    setSelected(patient);
    setBusy(true);
    setError('');
    try {
      setRecordings(await listPatientRecordings(patient.id));
    } catch (err) {
      setError(err.message);
      setRecordings([]);
    } finally {
      setBusy(false);
    }
  };

  const addPatient = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await redeemShareCode(code.trim());
      setCode('');
      await refreshPatients();
      await selectPatient(result.patient);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="doctor-dashboard">
      <section className="panel notifications-panel" aria-labelledby="notifications-title">
        <div className="notifications-heading">
          <div>
            <h3 id="notifications-title">
              <svg className="notification-bell" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M18 9a6 6 0 00-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />
              </svg>
              Notifications
              {unreadCount > 0 && <span className="notification-count">{unreadCount} new</span>}
            </h3>
            <p className="muted">Updates when patients share recordings or revoke access.</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={refreshNotifications}
            disabled={notificationsBusy}
          >
            {notificationsBusy ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
        {notificationError && <div className="error-banner" role="alert">{notificationError}</div>}
        {notifications.length === 0 ? (
          <p className="notification-empty">You’re all caught up. New patient updates will appear here.</p>
        ) : (
          <ul className="notifications-list" aria-live="polite">
            {notifications.map((notification) => (
              <li key={notification.id} className={notification.read ? 'notification-item' : 'notification-item unread'}>
                <span className="notification-indicator" aria-hidden="true" />
                <div className="notification-content">
                  <strong>{notification.message}</strong>
                  <time dateTime={notification.created_at}>
                    {new Date(notification.created_at).toLocaleString()}
                  </time>
                </div>
                {!notification.read && (
                  <button
                    type="button"
                    className="notification-read"
                    onClick={() => markAsRead(notification.id)}
                    aria-label={`Mark as read: ${notification.message}`}
                  >
                    Mark read
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h3>Patient access</h3>
        <p className="muted">A patient must share a one-time code with you before their recordings appear here.</p>
        <form className="row" onSubmit={addPatient}>
          <input value={code} onChange={(event) => setCode(event.target.value)} placeholder="Enter patient share code" aria-label="Patient share code" required />
          <button type="submit" className="btn btn-primary" disabled={busy}>Add patient</button>
        </form>
      </section>

      <section className="layout-2">
        <div className="panel">
          <h3>Shared patients</h3>
          {patients.length === 0 ? <p className="muted">No patients have shared access yet.</p> : (
            <ul className="patient-list">
              {patients.map((patient) => (
                <li key={patient.id}>
                  <button type="button" className={selected?.id === patient.id ? 'patient-choice selected' : 'patient-choice'} onClick={() => selectPatient(patient)} disabled={busy}>
                    <strong>{patient.name}</strong><span>{patient.email}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="panel">
          <h3>{selected ? `Recordings · ${selected.name}` : 'Patient recordings'}</h3>
          {!selected ? <p className="muted">Select a patient to view recordings shared with you.</p> : (
            <div className="table-scroll">
              <table className="table">
                <thead><tr><th>Recorded</th><th>Duration</th><th>Prototype BPM</th><th>Signal quality</th><th>Audio</th></tr></thead>
                <tbody>
                  {recordings.length === 0 ? <tr><td colSpan={5} className="muted">No recordings available.</td></tr> : recordings.map((recording) => (
                    <tr key={recording.id}>
                      <td>{new Date(recording.created_at).toLocaleString()}</td>
                      <td>{recording.duration_sec.toFixed(1)}s</td>
                      <td>{recording.estimated_bpm != null ? Math.round(recording.estimated_bpm) : '--'}</td>
                      <td>{recording.signal_quality}</td>
                      <td><a className="btn btn-secondary" href={downloadUrl(recording.id)} download={recording.filename}>Download</a></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <p className="muted">Measurements are prototype estimates only; this dashboard is not a clinical decision tool.</p>
    </div>
  );
}
