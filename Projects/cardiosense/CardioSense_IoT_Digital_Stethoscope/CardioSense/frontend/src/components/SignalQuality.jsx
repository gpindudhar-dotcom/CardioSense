import React from 'react';

const LEVELS = {
  'No Signal': 0,
  Poor: 25,
  Fair: 50,
  Good: 75,
  Excellent: 100,
};

export default function SignalQuality({ quality, rms, peak }) {
  const label = quality || 'No Signal';
  const pct = LEVELS[label] ?? 0;
  return (
    <div className="panel metric-card">
      <h3>Signal Quality</h3>
      <p className="value" style={{ fontSize: '1.45rem' }}>{label}</p>
      <div className="quality-bar" aria-hidden="true">
        <i style={{ width: `${pct}%` }} />
      </div>
      <p className="hint">RMS {Number(rms || 0).toFixed(1)} · Peak {Number(peak || 0).toFixed(1)}</p>
    </div>
  );
}
