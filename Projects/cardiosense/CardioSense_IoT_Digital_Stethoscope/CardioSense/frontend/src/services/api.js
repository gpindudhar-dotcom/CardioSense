const API_BASE = import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? '' : 'http://127.0.0.1:8000');

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs || 10000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    if (res.status === 204) return null;
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) return res.json();
    return res;
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Backend request timed out. Is the API running?');
    }
    if (err.message?.includes('Failed to fetch')) {
      throw new Error('Backend unavailable. Start the FastAPI server on port 8000.');
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export function getApiBase() {
  return API_BASE;
}

export function getHealth() {
  return request('/health');
}

export function getCurrentUser() {
  return request('/api/auth/me');
}

export function login(email, password) {
  return request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
}

export function registerPatient(payload) {
  return request('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) });
}

export function registerDoctor(payload) {
  return request('/api/auth/register/doctor', { method: 'POST', body: JSON.stringify(payload) });
}

export function logout() {
  return request('/api/auth/logout', { method: 'POST', body: '{}' });
}

export function createShareCode() {
  return request('/api/shares', { method: 'POST', body: '{}' });
}

export function listSharedDoctors() {
  return request('/api/shares');
}

export function revokeDoctorAccess(doctorId) {
  return request(`/api/shares/${doctorId}`, { method: 'DELETE' });
}

export function listDoctorPatients() {
  return request('/api/doctor/patients');
}

export function listDoctorNotifications() {
  return request('/api/doctor/notifications');
}

export function markDoctorNotificationRead(notificationId) {
  return request(`/api/doctor/notifications/${notificationId}/read`, { method: 'PUT' });
}

export function redeemShareCode(code) {
  return request('/api/shares/redeem', { method: 'POST', body: JSON.stringify({ code }) });
}

export function listPatientRecordings(patientId) {
  return request(`/api/doctor/patients/${patientId}/recordings`);
}

export function getDeviceStatus() {
  return request('/api/device/status');
}

export function listRecordings() {
  return request('/api/recordings');
}

export function createRecording(payload) {
  return request('/api/recordings', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function deleteRecording(id) {
  return request(`/api/recordings/${id}`, { method: 'DELETE' });
}

export function downloadUrl(id) {
  return `${API_BASE}/api/recordings/${id}/download`;
}

export function connectDevice(host, port = 81) {
  return request('/api/device/connect', {
    method: 'POST',
    body: JSON.stringify({ host, port, path: '/' }),
  });
}

export function disconnectDevice() {
  return request('/api/device/disconnect', { method: 'POST', body: '{}' });
}

export function analyzeSamples(payload) {
  return request('/api/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
