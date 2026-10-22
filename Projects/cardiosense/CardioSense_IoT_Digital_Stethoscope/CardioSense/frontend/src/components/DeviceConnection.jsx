import React, { useEffect, useState } from 'react';
import { connectDevice, disconnectDevice } from '../services/api';

function isValidIpOrHost(value) {
  if (!value || typeof value !== 'string') return false;
  const v = value.trim();
  if (v.length < 3 || v.length > 253) return false;
  const ipv4 = /^(?:\d{1,3}\.){3}\d{1,3}$/;
  const host = /^(?:[a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+$/;
  if (ipv4.test(v)) {
    return v.split('.').every((part) => {
      const number = Number(part);
      return number >= 0 && number <= 255;
    });
  }
  return host.test(v) || v === 'localhost';
}

export default function DeviceConnection({
  backendApiOnline,
  backendOnline,
  backendConnecting,
  deviceOnline,
  streamStatus,
  deviceIp,
  onConnectBackend,
  onDisconnectBackend,
  onSetDeviceIp,
  error,
}) {
  const [ip, setIp] = useState(deviceIp || '');
  const [localError, setLocalError] = useState('');
  const [deviceBusy, setDeviceBusy] = useState(false);
  const [bridgeRequested, setBridgeRequested] = useState(deviceOnline);

  useEffect(() => {
    if (deviceOnline) setBridgeRequested(true);
  }, [deviceOnline]);

  useEffect(() => {
    if (!backendOnline) setBridgeRequested(false);
  }, [backendOnline]);

  const saveAndBridge = async () => {
    if (!isValidIpOrHost(ip)) {
      setLocalError('Enter a valid IP address or hostname, for example 192.168.1.50.');
      return;
    }

    setLocalError('');
    onSetDeviceIp(ip.trim());
    setDeviceBusy(true);
    try {
      await connectDevice(ip.trim(), 81);
      setBridgeRequested(true);
    } catch (err) {
      setLocalError(err.message || 'Unable to connect to the ESP32.');
    } finally {
      setDeviceBusy(false);
    }
  };

  const stopBridge = async () => {
    setDeviceBusy(true);
    setLocalError('');
    try {
      await disconnectDevice();
      setBridgeRequested(false);
    } catch (err) {
      setLocalError(err.message || 'Unable to disconnect the ESP32.');
    } finally {
      setDeviceBusy(false);
    }
  };

  return (
    <section className="connection-panel panel" aria-labelledby="connection-title">
      <div className="connection-panel-heading">
        <div>
          <h3 id="connection-title">Connections</h3>
          <p className="muted">Connect the backend first, then connect your ESP32 device.</p>
        </div>
      </div>

      <div className="connection-grid">
        <section className="connection-card" aria-labelledby="backend-connection-title">
          <div className="connection-card-heading">
            <div>
              <span className="connection-step">STEP 1</span>
              <h4 id="backend-connection-title">Backend server</h4>
            </div>
            <span className={`connection-status ${backendApiOnline ? 'online' : 'offline'}`} role="status">
              <span className="connection-status-dot" />
              {backendApiOnline ? 'API available' : 'API unavailable'}
            </span>
          </div>
          <p className="muted">
            {backendOnline
              ? 'The dashboard audio link is connected to the backend.'
              : backendApiOnline
                ? 'The API is reachable. Connect the dashboard audio link to receive live data.'
                : 'The backend API cannot be reached. Start the backend server first.'}
          </p>
          <div className={`connection-link-state ${backendOnline ? 'connected' : ''}`} role="status">
            <span className="connection-status-dot" />
            Dashboard audio link: {backendOnline ? 'Connected' : backendConnecting ? 'Connecting' : 'Disconnected'}
          </div>
          <div className="connection-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={onConnectBackend}
              disabled={!backendApiOnline || backendOnline || backendConnecting}
            >
              {backendConnecting ? 'Connecting…' : 'Connect Backend'}
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={onDisconnectBackend}
              disabled={!backendOnline || backendConnecting}
            >
              Disconnect Backend
            </button>
          </div>
        </section>

        <section className="connection-card" aria-labelledby="esp-connection-title">
          <div className="connection-card-heading">
            <div>
              <span className="connection-step">STEP 2</span>
              <h4 id="esp-connection-title">ESP32 device</h4>
            </div>
            <span className={`connection-status ${deviceOnline ? 'online' : 'offline'}`} role="status">
              <span className="connection-status-dot" />
              {deviceOnline
                ? 'Streaming'
                : !backendApiOnline
                  ? 'Backend unavailable'
                  : streamStatus === 'Stream delayed'
                    ? 'Signal delayed'
                    : streamStatus === 'No recent audio'
                      ? 'No recent audio'
                      : bridgeRequested
                        ? 'Awaiting audio'
                        : 'Not connected'}
            </span>
          </div>
          <p className="muted">Enter the ESP32 IP address. Audio uses WebSocket port 81.</p>
          <label className="connection-ip-label" htmlFor="esp32-ip">Device IP address</label>
          <form
            className="connection-device-form"
            onSubmit={(event) => {
              event.preventDefault();
              saveAndBridge();
            }}
          >
            <input
              id="esp32-ip"
              type="text"
              value={ip}
              onChange={(event) => {
                setIp(event.target.value);
                setLocalError('');
              }}
              placeholder="e.g. 192.168.1.50"
              disabled={!backendApiOnline || !backendOnline || deviceBusy}
            />
            <div className="connection-actions">
              <button
                type="submit"
                className="btn btn-primary"
                disabled={!backendApiOnline || !backendOnline || deviceBusy || deviceOnline}
              >
                {deviceBusy && !bridgeRequested ? 'Connecting…' : 'Connect ESP32'}
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={stopBridge}
                disabled={!backendApiOnline || !backendOnline || deviceBusy || (!bridgeRequested && !deviceOnline)}
              >
                {deviceBusy && bridgeRequested ? 'Disconnecting…' : 'Disconnect ESP32'}
              </button>
            </div>
          </form>
          {(!backendApiOnline || !backendOnline) && (
            <p className="connection-hint">The backend API and dashboard audio link must both be connected first.</p>
          )}
        </section>
      </div>

      {(localError || error) && <div className="error-banner" role="alert">{localError || error}</div>}
    </section>
  );
}
