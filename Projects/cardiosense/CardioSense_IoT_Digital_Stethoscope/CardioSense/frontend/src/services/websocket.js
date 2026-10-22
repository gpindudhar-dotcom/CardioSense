const WS_BASE = import.meta.env.VITE_WS_BASE || 'ws://127.0.0.1:8000';

export function getWsUrl(path = '/ws/audio') {
  return `${WS_BASE}${path}`;
}

export function createAudioSocket({ onMessage, onOpen, onClose, onError } = {}) {
  let ws = null;
  let closedByUser = false;
  let retry = 0;
  let retryTimer = null;

  const connect = () => {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    try {
      ws = new WebSocket(getWsUrl('/ws/audio'));
    } catch (err) {
      onError?.(err);
      scheduleReconnect();
      return;
    }
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      retry = 0;
      onOpen?.();
      safeSend({ type: 'get_status' });
    };

    ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        try {
          const msg = JSON.parse(ev.data);
          onMessage?.(msg);
        } catch {
          onError?.(new Error('Malformed JSON from backend WebSocket.'));
        }
        return;
      }
      // Binary from ESP32 bridged through backend — backend normally rebroadcasts JSON.
      onMessage?.({ type: 'binary', data: ev.data });
    };

    ws.onerror = () => {
      onError?.(new Error('WebSocket error. Check backend / ESP32 connection.'));
    };

    ws.onclose = () => {
      onClose?.();
      if (!closedByUser) scheduleReconnect();
    };
  };

  const scheduleReconnect = () => {
    if (closedByUser) return;
    const delay = Math.min(8000, 500 * 2 ** retry);
    retry += 1;
    clearTimeout(retryTimer);
    retryTimer = setTimeout(connect, delay);
  };

  const safeSend = (obj) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(obj));
    }
  };

  return {
    connect,
    disconnect() {
      closedByUser = true;
      clearTimeout(retryTimer);
      if (ws) ws.close();
      ws = null;
    },
    send: safeSend,
    ping() {
      safeSend({ type: 'ping' });
    },
    requestSpectrum() {
      safeSend({ type: 'get_spectrum' });
    },
    get readyState() {
      return ws ? ws.readyState : WebSocket.CLOSED;
    },
  };
}

/** Ring buffer for live waveform samples (actual stream data, not fake animation). */
export class SampleRingBuffer {
  constructor(capacity = 8000) {
    this.capacity = capacity;
    this.buffer = new Float32Array(capacity);
    this.write = 0;
    this.length = 0;
  }

  push(samples) {
    if (!samples || !samples.length) return;
    for (let i = 0; i < samples.length; i += 1) {
      const v = Number(samples[i]);
      if (!Number.isFinite(v)) continue;
      this.buffer[this.write] = v;
      this.write = (this.write + 1) % this.capacity;
      if (this.length < this.capacity) this.length += 1;
    }
  }

  clear() {
    this.write = 0;
    this.length = 0;
    this.buffer.fill(0);
  }

  toArray() {
    const out = new Float32Array(this.length);
    const start = this.length === this.capacity ? this.write : 0;
    for (let i = 0; i < this.length; i += 1) {
      out[i] = this.buffer[(start + i) % this.capacity];
    }
    return out;
  }
}
