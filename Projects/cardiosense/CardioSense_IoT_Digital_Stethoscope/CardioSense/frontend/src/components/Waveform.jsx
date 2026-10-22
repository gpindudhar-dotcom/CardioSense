import React, { useEffect, useRef } from 'react';

/**
 * Live phonocardiogram canvas — renders actual sample ring buffer contents.
 */
export default function Waveform({
  getSamples,
  paused,
  sampleRate = 4000,
  windowSec = 2,
  autoScale = true,
}) {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const scaleRef = useRef(500);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.parentElement.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    const draw = () => {
      const parent = canvas.parentElement;
      const w = parent.clientWidth;
      const h = parent.clientHeight;
      ctx.clearRect(0, 0, w, h);

      // Grid
      ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--line') || '#ccc';
      ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i += 1) {
        const y = (h / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }
      for (let i = 0; i <= 8; i += 1) {
        const x = (w / 8) * i;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }

      const samples = getSamples?.() || new Float32Array(0);
      const needed = Math.floor(sampleRate * windowSec);
      const view =
        samples.length > needed ? samples.subarray(samples.length - needed) : samples;

      if (view.length > 1) {
        let peak = 1;
        if (autoScale) {
          for (let i = 0; i < view.length; i += 1) {
            const a = Math.abs(view[i]);
            if (a > peak) peak = a;
          }
          const target = Math.max(40, peak * 1.15);
          scaleRef.current = scaleRef.current * 0.9 + target * 0.1;
        }
        const scale = scaleRef.current || 1;
        const mid = h / 2;
        const accent = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#0e7c86';
        ctx.strokeStyle = accent;
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let i = 0; i < view.length; i += 1) {
          const x = (i / (view.length - 1)) * w;
          const y = mid - (view[i] / scale) * (h * 0.42);
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      } else {
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#888';
        ctx.font = '14px IBM Plex Sans, sans-serif';
        ctx.fillText('Waiting for live samples…', 16, h / 2);
      }

      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#888';
      ctx.font = '12px IBM Plex Sans, sans-serif';
      ctx.fillText(`${windowSec.toFixed(1)}s window · ${sampleRate} Hz`, 12, h - 12);

      if (!paused) rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [getSamples, paused, sampleRate, windowSec, autoScale]);

  return (
    <div className="canvas-wrap" aria-label="Live phonocardiogram waveform">
      <canvas ref={canvasRef} />
    </div>
  );
}
