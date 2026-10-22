import React from 'react';

export default function SafetyNotice() {
  return (
    <div className="safety" role="note">
      <strong>Educational prototype — not a medical diagnostic device.</strong>
      {' '}
      CardioSense does not diagnose heart disease, murmurs, arrhythmia, or lung disease.
      Not for emergency use. Not clinically validated. Observe ADC voltage limits, isolation,
      and battery safety when wiring hardware.
    </div>
  );
}
