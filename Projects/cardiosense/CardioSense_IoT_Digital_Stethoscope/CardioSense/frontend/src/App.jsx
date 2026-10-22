import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Header from './components/Header';
import DeviceConnection from './components/DeviceConnection';
import HeartRateCard from './components/HeartRateCard';
import Waveform from './components/Waveform';
import SignalQuality from './components/SignalQuality';
import RecordingPanel from './components/RecordingPanel';
import Spectrum from './components/Spectrum';
import DeviceStatus from './components/DeviceStatus';
import SafetyNotice from './components/SafetyNotice';
import AuthScreen from './components/AuthScreen';
import DoctorDashboard from './components/DoctorDashboard';
import PatientSharing from './components/PatientSharing';
import { disconnectDevice, getCurrentUser, getDeviceStatus, getHealth, logout } from './services/api';
import { SampleRingBuffer, createAudioSocket } from './services/websocket';

const PATIENT_NAV = [
  { id: 'live', label: 'Live Monitor' },
  { id: 'recordings', label: 'Recordings' },
  { id: 'analysis', label: 'Signal Analysis' },
  { id: 'sharing', label: 'Doctor Access' },
  { id: 'settings', label: 'Settings' },
];
const DOCTOR_NAV = [{ id: 'patients', label: 'Shared Patients' }];

function formatDuration(sec) {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('cs-theme') || 'light');
  const [page, setPage] = useState('live');
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(false);
  const [backendConnecting, setBackendConnecting] = useState(false);
  const [backendApiOnline, setBackendApiOnline] = useState(false);
  const [error, setError] = useState('');
  const [deviceIp, setDeviceIp] = useState(() => localStorage.getItem('cs-esp-ip') || '');
  const [status, setStatus] = useState({});
  const [bpm, setBpm] = useState(null);
  const [quality, setQuality] = useState('No Signal');
  const [rms, setRms] = useState(0);
  const [peak, setPeak] = useState(0);
  const [sampleRate, setSampleRate] = useState(4000);
  const [paused, setPaused] = useState(false);
  const [autoScale, setAutoScale] = useState(true);
  const [windowSec, setWindowSec] = useState(2);
  const [isRecording, setIsRecording] = useState(false);
  const [sessionStart, setSessionStart] = useState(Date.now());
  const [now, setNow] = useState(Date.now());
  const [lastAudioAt, setLastAudioAt] = useState(null);
  const [samplesReceived, setSamplesReceived] = useState(0);
  const [packetsReceived, setPacketsReceived] = useState(0);
  const [spectrum, setSpectrum] = useState({ freqs: [], magnitude: [] });
  const [canvasTick, setCanvasTick] = useState(0);
  const isDoctor = currentUser?.role === 'doctor';
  const nav = isDoctor ? DOCTOR_NAV : PATIENT_NAV;

  const ringRef = useRef(new SampleRingBuffer(12000));
  const recordRef = useRef([]);
  const socketRef = useRef(null);
  const pausedRef = useRef(false);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cs-theme', theme);
  }, [theme]);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const handleMessage = useCallback((msg) => {
    if (!msg || typeof msg !== 'object') return;
    if (msg.type === 'audio') {
      const receivedAt = Date.now();
      const sampleCount = Array.isArray(msg.samples) ? msg.samples.length : 0;
      if (!pausedRef.current) {
        ringRef.current.push(msg.samples);
        setCanvasTick((n) => n + 1);
      }
      if (recordRef.current && Array.isArray(recordRef.current) && recordRef.current.__active) {
        recordRef.current.push(...msg.samples);
      }
      setBpm(msg.bpm);
      setQuality(msg.signal_quality || 'No Signal');
      setRms(msg.rms || 0);
      setPeak(msg.peak || 0);
      setSampleRate(msg.sample_rate || 4000);
      setLastAudioAt(receivedAt);
      setSamplesReceived((count) => count + sampleCount);
      setPacketsReceived((count) => count + 1);
      setStatus((prev) => ({
        ...prev,
        connected: true,
        packets_received: msg.packets_received ?? prev.packets_received,
        sample_rate: msg.sample_rate || prev.sample_rate,
        bpm: msg.bpm,
        signal_quality: msg.signal_quality,
      }));
      setError('');
    } else if (msg.type === 'device_status') {
      setStatus(msg.data || {});
    } else if (msg.type === 'spectrum') {
      setSpectrum(msg.data || { freqs: [], magnitude: [] });
    } else if (msg.type === 'error') {
      setError(msg.message || 'WebSocket error');
    }
  }, []);

  const connectBackend = useCallback(async () => {
    if (typeof WebSocket === 'undefined') {
      setError('Browser does not support WebSocket APIs.');
      return;
    }
    setBackendConnecting(true);
    setError('');
    try {
      await getHealth();
      setBackendApiOnline(true);
    } catch (err) {
      setBackendApiOnline(false);
      setBackendConnecting(false);
      setError(err.message || 'Backend API is unavailable.');
      return;
    }

    socketRef.current?.disconnect();
    const sock = createAudioSocket({
      onOpen: () => {
        setBackendOnline(true);
        setBackendConnecting(false);
        setError('');
        setSessionStart(Date.now());
        setLastAudioAt(null);
        setSamplesReceived(0);
        setPacketsReceived(0);
        ringRef.current.clear();
        setCanvasTick((n) => n + 1);
      },
      onClose: () => {
        setBackendOnline(false);
        setBackendConnecting(false);
      },
      onError: (err) => {
        setBackendConnecting(false);
        setError(err.message || 'WebSocket disconnected');
      },
      onMessage: handleMessage,
    });
    socketRef.current = sock;
    sock.connect();
  }, [handleMessage]);

  const disconnectBackend = useCallback(async () => {
    let disconnectError = '';
    try {
      await disconnectDevice();
    } catch (err) {
      disconnectError = err.message || 'Unable to stop the ESP32 bridge.';
    }
    socketRef.current?.disconnect();
    socketRef.current = null;
    setBackendOnline(false);
    setBackendConnecting(false);
    setStatus((previous) => ({ ...previous, connected: false }));
    setLastAudioAt(null);
    if (disconnectError) setError(disconnectError);
  }, []);

  useEffect(() => {
    getCurrentUser()
      .then(setCurrentUser)
      .catch(() => setCurrentUser(null))
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    setPage(currentUser?.role === 'doctor' ? 'patients' : 'live');
    if (!currentUser || currentUser.role !== 'patient') return undefined;
    connectBackend();
    getDeviceStatus()
      .then((d) => setStatus(d))
      .catch((err) => setError(err.message));
    return () => {
      socketRef.current?.disconnect();
      socketRef.current = null;
    };
  }, [currentUser, connectBackend]);

  useEffect(() => {
    if (!currentUser || currentUser.role !== 'patient') return undefined;
    let active = true;
    const checkApi = () => {
      getHealth()
        .then(() => {
          if (active) setBackendApiOnline(true);
        })
        .catch(() => {
          if (active) setBackendApiOnline(false);
        });
    };
    checkApi();
    const timer = setInterval(checkApi, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [currentUser]);

  useEffect(() => {
    if (!backendOnline) return undefined;
    const id = setInterval(() => socketRef.current?.requestSpectrum(), 1500);
    return () => clearInterval(id);
  }, [backendOnline]);

  const getSamples = useCallback(() => {
    // canvasTick dependency forces refresh binding when data arrives
    void canvasTick;
    return ringRef.current.toArray();
  }, [canvasTick]);

  const streamFresh = lastAudioAt !== null && now - lastAudioAt <= 5000;
  const deviceOnline = Boolean(status.connected) && backendOnline && streamFresh;
  const streamStatus = !backendOnline
    ? 'Audio link disconnected'
    : streamFresh
      ? 'Live stream'
      : lastAudioAt !== null && now - lastAudioAt <= 15000
        ? 'Stream delayed'
        : lastAudioAt !== null
          ? 'No recent audio'
          : 'Waiting for device';
  const lastPacketLabel = lastAudioAt === null
    ? 'No packets yet'
    : now - lastAudioAt < 1000
      ? 'Just now'
      : `${Math.floor((now - lastAudioAt) / 1000)} sec ago`;

  const startRecording = () => {
    recordRef.current = [];
    recordRef.current.__active = true;
    setIsRecording(true);
  };

  const stopRecordingFlag = () => {
    if (recordRef.current) recordRef.current.__active = false;
    setIsRecording(false);
  };

  const getRecordedSamples = () => {
    const arr = recordRef.current || [];
    return Array.from(arr);
  };

  const sessionDuration = formatDuration((now - sessionStart) / 1000);

  const signOut = async () => {
    try {
      await disconnectBackend();
      await logout();
      setCurrentUser(null);
    } catch (err) {
      setError(err.message || 'Unable to sign out.');
    }
  };

  const settingsPanel = useMemo(
    () => (
      <div className="panel layout-stack">
        <h3>Settings</h3>
        <label className="row">
          <span>Waveform window (seconds)</span>
          <input
            type="text"
            value={String(windowSec)}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (Number.isFinite(v) && v >= 0.5 && v <= 10) setWindowSec(v);
            }}
            aria-label="Waveform time window"
          />
        </label>
        <label className="row">
          <input type="checkbox" checked={autoScale} onChange={(e) => setAutoScale(e.target.checked)} />
          Auto-scale amplitude
        </label>
        <p className="muted">
          Firmware ADC pin / sample rate are configured on the ESP32 (`ADC_PIN`, `SAMPLE_RATE`).
          Saved ESP32 IP is for reference/debugging only: <strong>{deviceIp || 'not set'}</strong>
        </p>
      </div>
    ),
    [autoScale, deviceIp, windowSec],
  );

  if (authLoading) {
    return <main className="auth-page"><p className="muted">Checking your session…</p></main>;
  }
  if (!currentUser) {
    return <AuthScreen onAuthenticated={setCurrentUser} />;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>CardioSense</h1>
          <p>IoT Digital Stethoscope</p>
        </div>
        <section className="sidebar-profile" aria-label={`${isDoctor ? 'Doctor' : 'Patient'} profile`}>
          <div className="profile-avatar" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="8" r="3.5" />
              <path d="M5.5 20c.5-3.5 2.7-5.5 6.5-5.5s6 2 6.5 5.5" />
            </svg>
          </div>
          <div className="profile-details">
            <span className="account-label">{currentUser.name}</span>
            <span className="profile-role">{isDoctor ? 'Doctor account' : 'Patient account'}</span>
          </div>
          <button
            type="button"
            className="profile-signout"
            onClick={signOut}
            aria-label="Sign out"
            title="Sign out"
          >
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M10 17l5-5-5-5M15 12H3" />
              <path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" />
            </svg>
          </button>
        </section>
        <nav className="nav" aria-label="Primary">
          {nav.map((item) => (
            <button
              key={item.id}
              type="button"
              className={page === item.id ? 'active' : ''}
              onClick={() => setPage(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <p>Educational prototype for learning IoT, DSP, and embedded systems. Not a medical device.</p>
        </div>
      </aside>

      <main className="main">
        <SafetyNotice />
        <Header
          title={isDoctor ? 'Doctor Dashboard' : 'Patient Dashboard'}
          subtitle={isDoctor ? 'Review recordings shared by your patients' : 'Your device, live monitor, and recordings'}
          theme={theme}
          onToggleTheme={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
          connectionLabel={isDoctor ? 'Patient-shared data only' : deviceOnline ? 'ESP32 streaming' : backendOnline ? 'Backend only' : 'Disconnected'}
          online={backendOnline}
        />

        {isDoctor && page === 'patients' && <DoctorDashboard />}

        {!isDoctor && (page === 'live' || page === 'settings') && (
          <DeviceConnection
            backendApiOnline={backendApiOnline}
            backendOnline={backendOnline}
            backendConnecting={backendConnecting}
            deviceOnline={deviceOnline}
            streamStatus={streamStatus}
            deviceIp={deviceIp}
            onConnectBackend={connectBackend}
            onDisconnectBackend={disconnectBackend}
            onSetDeviceIp={(ip) => {
              setDeviceIp(ip);
              localStorage.setItem('cs-esp-ip', ip);
            }}
            error={error}
          />
        )}

        {!isDoctor && page === 'live' && (
          <>
            <div className="grid-metrics">
              <HeartRateCard bpm={deviceOnline ? bpm : null} status={deviceOnline ? 'ok' : 'insufficient_signal'} />
              <SignalQuality quality={quality} rms={rms} peak={peak} />
              <div className="panel metric-card">
                <h3>Signal Peak</h3>
                <p className="value">{Number(peak || 0).toFixed(0)}</p>
                <p className="hint">Normalized ADC amplitude units</p>
              </div>
              <div className="panel metric-card">
                <h3>Samples Received</h3>
                <p className="value" style={{ fontSize: '1.6rem' }}>{samplesReceived.toLocaleString()}</p>
                <p className="hint">{packetsReceived.toLocaleString()} packets · {sampleRate} Hz</p>
              </div>
            </div>

            <div className={`stream-summary ${deviceOnline ? 'streaming' : ''}`}>
              <span className={`stream-indicator ${deviceOnline ? 'active' : ''}`} aria-hidden="true" />
              <div className="stream-summary-copy">
                <strong>{streamStatus}</strong>
                <span>
                  {deviceOnline
                    ? `${status.device_id || 'ESP32'} · ${sampleRate} Hz`
                    : backendOnline
                      ? 'Connect an ESP32 device to begin receiving samples.'
                      : 'Connect the backend to start your monitoring session.'}
                </span>
              </div>
              <div className="stream-summary-meta">
                <span>Last packet</span>
                <strong aria-live="polite">{lastPacketLabel}</strong>
              </div>
              <div className="stream-summary-meta">
                <span>Session</span>
                <strong>{sessionDuration}</strong>
              </div>
            </div>

            <div className="panel">
              <div className="toolbar">
                <h3 style={{ margin: 0, flex: 1 }}>Live Phonocardiogram</h3>
                <span className={`waveform-state ${deviceOnline ? 'active' : ''}`}>
                  <span className="dot" />
                  {paused ? 'Paused' : deviceOnline ? 'Live' : 'Waiting'}
                </span>
                <button type="button" className="btn btn-secondary" onClick={() => setPaused((p) => !p)}>
                  {paused ? 'Resume' : 'Pause'}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    ringRef.current.clear();
                    setCanvasTick((n) => n + 1);
                  }}
                >
                  Clear
                </button>
              </div>
              {paused && <p className="waveform-pause-note">Waveform display is paused. Incoming samples are still included in recordings.</p>}
              <Waveform
                getSamples={getSamples}
                paused={paused}
                sampleRate={sampleRate}
                windowSec={windowSec}
                autoScale={autoScale}
              />
            </div>

            <div className="layout-2">
              <Spectrum freqs={spectrum.freqs} magnitude={spectrum.magnitude} />
              <DeviceStatus status={status} />
            </div>

            <RecordingPanel
              isRecording={isRecording}
              onStart={startRecording}
              onStop={stopRecordingFlag}
              getRecordedSamples={getRecordedSamples}
              sampleRate={sampleRate}
              deviceId={status.device_id}
              bpm={bpm}
              quality={quality}
            />
          </>
        )}

        {!isDoctor && page === 'recordings' && (
          <RecordingPanel
            isRecording={isRecording}
            onStart={startRecording}
            onStop={stopRecordingFlag}
            getRecordedSamples={getRecordedSamples}
            sampleRate={sampleRate}
            deviceId={status.device_id}
            bpm={bpm}
            quality={quality}
          />
        )}

        {!isDoctor && page === 'analysis' && (
          <div className="layout-stack">
            <Spectrum freqs={spectrum.freqs} magnitude={spectrum.magnitude} />
            <div className="panel">
              <h3>Signal Analysis</h3>
              <p className="muted">
                Metrics are derived from received samples (RMS, peak, band energy, envelope peaks).
                BPM is a prototype estimate – not clinically validated. Insufficient quality shows -- BPM.
              </p>
              <div className="kv">
                <span>Quality</span>
                <strong>{quality}</strong>
                <span>RMS</span>
                <strong>{Number(rms).toFixed(2)}</strong>
                <span>Peak</span>
                <strong>{Number(peak).toFixed(2)}</strong>
                <span>BPM</span>
                <strong>{Number.isFinite(bpm) && bpm > 0 ? Math.round(bpm) : '--'}</strong>
              </div>
            </div>
          </div>
        )}

        {!isDoctor && page === 'sharing' && <PatientSharing />}
        {!isDoctor && page === 'settings' && settingsPanel}
      </main>
    </div>
  );
}
