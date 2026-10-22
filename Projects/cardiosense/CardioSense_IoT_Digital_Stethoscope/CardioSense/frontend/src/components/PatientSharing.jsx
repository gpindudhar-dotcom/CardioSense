import React, { useEffect, useState } from 'react';
import { createShareCode, listSharedDoctors, revokeDoctorAccess } from '../services/api';

export default function PatientSharing() {
  const [doctors, setDoctors] = useState([]);
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    try {
      setDoctors(await listSharedDoctors());
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => { refresh(); }, []);

  const generateCode = async () => {
    setBusy(true);
    setError('');
    try {
      const result = await createShareCode();
      setCode(result.code);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (doctor) => {
    setBusy(true);
    try {
      await revokeDoctorAccess(doctor.id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel layout-stack">
      <div>
        <h3>Share recordings with a doctor</h3>
        <p className="muted">
          Generate a one-time code and give it directly to your doctor. It expires after 15 minutes.
          You can revoke access at any time.
        </p>
      </div>
      <div className="toolbar">
        <button type="button" className="btn btn-primary" onClick={generateCode} disabled={busy}>Generate one-time code</button>
      </div>
      {code && (
        <div className="share-code" aria-live="polite">
          <span>Share this code with your doctor (shown only once)</span>
          <strong>{code}</strong>
          <span className="muted">Valid for 15 minutes.</span>
        </div>
      )}
      {error && <div className="error-banner" role="alert">{error}</div>}
      <div>
        <h3>Doctors with access</h3>
        {doctors.length === 0 ? <p className="muted">No doctors currently have access.</p> : (
          <ul className="sharing-list">
            {doctors.map((doctor) => (
              <li key={doctor.id}>
                <span><strong>{doctor.name}</strong><small>{doctor.email}</small></span>
                <button type="button" className="btn btn-danger" onClick={() => revoke(doctor)} disabled={busy}>Revoke</button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
