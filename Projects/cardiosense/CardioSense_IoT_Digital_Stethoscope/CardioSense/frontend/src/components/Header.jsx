import React from 'react';

export default function Header({ title, subtitle, theme, onToggleTheme, connectionLabel, online }) {
  return (
    <div className="topbar">
      <div>
        <h2>{title}</h2>
        <p className="sub">{subtitle}</p>
      </div>
      <div className="row">
        <span className={`status-pill ${online ? 'online' : 'offline'}`} aria-live="polite">
          <span className="dot" />
          {connectionLabel}
        </span>
        <button type="button" className="theme-toggle" onClick={onToggleTheme} aria-label="Toggle theme">
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </div>
    </div>
  );
}
