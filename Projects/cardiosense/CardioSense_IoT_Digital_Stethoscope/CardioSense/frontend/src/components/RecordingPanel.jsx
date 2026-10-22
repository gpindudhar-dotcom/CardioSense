import React, { useEffect, useState } from 'react';
import { createRecording, deleteRecording, downloadUrl, listRecordings } from '../services/api';

export default function RecordingPanel({
  isRecording,
  onStart,
  onStop,
  getRecordedSamples,
  sampleRate,
  deviceId,
  bpm,
  quality,
}) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [audioUrl, setAudioUrl] = useState(null);

  const refresh = async () => {
    try {
      const rows = await listRecordings();
      setItems(rows);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    refresh();
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleStopAndSave = async () => {
    const samples = getRecordedSamples?.() || [];
    onStop?.();
    if (!samples.length) {
      setError('Recording stopped with no samples.');
      return;
    }
    setBusy(true);
    try {
      await createRecording({
        device_id: deviceId || 'unknown',
        sample_rate: sampleRate,
        samples,
        estimated_bpm: Number.isFinite(bpm) ? bpm : null,
        signal_quality: quality || 'Unknown',
      });
      await refresh();
      setError('');
    } catch (err) {
      setError(err.message || 'Recording failure');
    } finally {
      setBusy(false);
    }
  };

  const play = async (id) => {
    try {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      const res = await fetch(downloadUrl(id), { credentials: 'include' });
      if (!res.ok) throw new Error('Unable to download recording for playback.');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (err) {
      setError(err.message);
    }
  };

  const remove = async (id) => {
    setBusy(true);
    try {
      await deleteRecording(id);
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel">
      <h3>Recording</h3>
      <div className="toolbar">
        <button type="button" className="btn btn-primary" disabled={isRecording || busy} onClick={onStart}>
          Start Recording
        </button>
        <button type="button" className="btn btn-secondary" disabled={!isRecording || busy} onClick={handleStopAndSave}>
          Stop Recording
        </button>
        <button type="button" className="btn btn-secondary" onClick={refresh} disabled={busy}>
          Refresh
        </button>
      </div>
      {isRecording && <p className="muted">Capturing live samples…</p>}
      {error && <div className="error-banner" role="alert">{error}</div>}
      {audioUrl && (
        <audio controls src={audioUrl} style={{ width: '100%', marginTop: '0.5rem' }}>
          Your browser does not support audio playback.
        </audio>
      )}
      <div style={{ overflowX: 'auto', marginTop: '0.75rem' }}>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Time</th>
              <th>Duration</th>
              <th>BPM*</th>
              <th>Quality</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">No recordings yet.</td>
              </tr>
            )}
            {items.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>{r.duration_sec.toFixed(1)}s</td>
                <td>{r.estimated_bpm != null ? Math.round(r.estimated_bpm) : '--'}</td>
                <td>{r.signal_quality}</td>
                <td>
                  <div className="row">
                    <button type="button" className="btn btn-secondary" onClick={() => play(r.id)}>Play</button>
                    <a className="btn btn-secondary" href={downloadUrl(r.id)} download={r.filename}>Download</a>
                    <button type="button" className="btn btn-danger" onClick={() => remove(r.id)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted" style={{ marginBottom: 0 }}>* Prototype estimate – not clinically validated.</p>
    </div>
  );
}
