import React from 'react';

export default function DeviceStatus({ status }) {
  const s = status || {};
  return (
    <div className="panel">
      <h3>Device Status</h3>
      <div className="kv">
        <span>Device ID</span>
        <strong>{s.device_id || 'unknown'}</strong>
        <span>Wi-Fi</span>
        <strong>{s.wifi_connected ? 'Connected' : 'Disconnected'}</strong>
        <span>IP</span>
        <strong>{s.ip || '—'}</strong>
        <span>RSSI</span>
        <strong>{s.rssi != null ? `${s.rssi} dBm` : '—'}</strong>
        <span>Packets received</span>
        <strong>{s.packets_received ?? 0}</strong>
        <span>Sample rate</span>
        <strong>{s.sample_rate ?? 4000} Hz</strong>
        <span>Last seen</span>
        <strong>{s.last_seen ? new Date(s.last_seen).toLocaleTimeString() : '—'}</strong>
      </div>
    </div>
  );
}
