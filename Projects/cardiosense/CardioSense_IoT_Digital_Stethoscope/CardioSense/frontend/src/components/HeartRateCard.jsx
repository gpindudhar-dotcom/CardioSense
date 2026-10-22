import React from 'react';

export default function HeartRateCard({ bpm, status }) {
  const show = Number.isFinite(bpm) && bpm > 0;
  return (
    <div className="panel metric-card">
      <h3>Heart Rate</h3>
      <p className="value">{show ? Math.round(bpm) : '--'} <span style={{ fontSize: '1rem' }}>BPM</span></p>
      <p className="hint">
        {show
          ? 'Prototype estimate – not clinically validated.'
          : status === 'warming_up'
            ? 'Warming up…'
            : 'Insufficient signal'}
      </p>
    </div>
  );
}
