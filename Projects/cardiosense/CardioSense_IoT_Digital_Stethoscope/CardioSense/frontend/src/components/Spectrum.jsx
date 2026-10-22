import React, { useEffect, useRef } from 'react';

export default function Spectrum({ freqs = [], magnitude = [] }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const parent = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const w = parent.clientWidth;
    const h = parent.clientHeight;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--line') || '#ccc';
    for (let i = 0; i <= 4; i += 1) {
      const y = (h / 4) * i;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    if (!magnitude.length) {
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#888';
      ctx.font = '14px IBM Plex Sans, sans-serif';
      ctx.fillText('Spectrum unavailable — waiting for signal.', 16, h / 2);
      return;
    }

    const max = Math.max(...magnitude, 1e-6);
    const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent-2').trim() || '#1a9b8e';
    ctx.fillStyle = accent;
    const n = magnitude.length;
    const barW = Math.max(1, w / n);
    for (let i = 0; i < n; i += 1) {
      const val = magnitude[i] / max;
      const bh = val * (h * 0.85);
      ctx.globalAlpha = 0.85;
      ctx.fillRect(i * barW, h - bh, Math.max(1, barW - 0.5), bh);
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#888';
    ctx.font = '12px IBM Plex Sans, sans-serif';
    const fMax = freqs.length ? freqs[freqs.length - 1] : 0;
    ctx.fillText(`0 – ${fMax.toFixed(0)} Hz`, 12, h - 12);
  }, [freqs, magnitude]);

  return (
    <div className="panel">
      <h3>FFT / Frequency Spectrum</h3>
      <div className="canvas-wrap" style={{ height: 220 }}>
        <canvas ref={canvasRef} aria-label="Frequency spectrum" />
      </div>
    </div>
  );
}
