import React, { useState } from 'react';
import { login, registerDoctor, registerPatient } from '../services/api';

export default function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState('patient');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const changeMode = (nextMode) => {
    setMode(nextMode);
    setError('');
    setPassword('');
    setShowPassword(false);
  };

  const isRegistering = mode === 'register';
  const isDoctorRegistering = mode === 'doctor-register';
  const isCreatingAccount = isRegistering || isDoctorRegistering;
  const isDoctorLogin = mode === 'doctor';

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const user = isCreatingAccount
        ? isDoctorRegistering
          ? await registerDoctor({ name, email, password })
          : await registerPatient({ name, email, password })
        : await login(email, password);
      if (!isCreatingAccount && user.role !== (isDoctorLogin ? 'doctor' : 'patient')) {
        throw new Error(
          isDoctorLogin
            ? 'This is a patient account. Choose Patient sign in instead.'
            : 'This is a doctor account. Choose Doctor sign in instead.',
        );
      }
      onAuthenticated(user);
    } catch (err) {
      setError(err.message || 'Unable to authenticate.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-page">
      <section className="auth-layout" aria-label="CardioSense account access">
        <div className="auth-intro">
          <a className="auth-brand" href="/" aria-label="CardioSense home">
            <span className="auth-brand-mark" aria-hidden="true">
              <svg viewBox="0 0 36 36" fill="none">
                <path d="M3 19h7l4-10 7 19 5-12 3 3h4" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <span>CardioSense</span>
          </a>
          <div className="auth-intro-copy">
            <p className="auth-kicker">CONNECTED HEART SOUND MONITOR</p>
            <h1>Listen closer.<br />Stay informed.</h1>
            <p className="auth-intro-description">
              A learning project for exploring live heart-sound signals, recordings, and connected devices.
            </p>
            <div className="auth-feature">
              <span className="auth-feature-icon" aria-hidden="true">01</span>
              <span><strong>Live sound monitoring</strong><small>View the signal from your connected device.</small></span>
            </div>
            <div className="auth-feature">
              <span className="auth-feature-icon" aria-hidden="true">02</span>
              <span><strong>Private recording access</strong><small>Choose when to share recordings with a doctor.</small></span>
            </div>
          </div>
          <div className="auth-intro-footer">
            <span className="auth-status-dot" aria-hidden="true" />
            Educational prototype · Not a medical device
          </div>
          <svg className="auth-decoration" viewBox="0 0 500 220" fill="none" aria-hidden="true">
            <path d="M0 130h88l23-47 43 104 49-140 42 111 26-55 20 27h209" stroke="currentColor" strokeWidth="2" />
            <path d="M0 168h500" stroke="currentColor" strokeWidth="1" strokeDasharray="4 9" />
          </svg>
        </div>

        <div className="auth-content">
          <div className="auth-form-wrap">
            <p className="auth-mobile-brand">CardioSense <span>· Learning prototype</span></p>
            <p className="auth-eyebrow">
              {isDoctorRegistering ? 'DOCTOR REGISTRATION' : isRegistering ? 'GET STARTED' : isDoctorLogin ? 'DOCTOR ACCESS' : 'PATIENT ACCESS'}
            </p>
            <h2>{isCreatingAccount ? 'Create your account' : 'Welcome back'}</h2>
            <p className="auth-subtitle">
              {isDoctorRegistering
                ? 'Create a doctor account to access the doctor dashboard.'
                : isRegistering
                ? 'Create a patient account to get started.'
                : isDoctorLogin
                  ? 'Sign in with your doctor account or create one below.'
                  : 'Sign in to continue to your patient dashboard.'}
            </p>

            {!isCreatingAccount && (
              <div className="auth-tabs" aria-label="Account access">
              <button
                type="button"
                className={mode === 'patient' ? 'selected' : ''}
                aria-pressed={mode === 'patient'}
                onClick={() => changeMode('patient')}
              >
                Patient
              </button>
              <button
                type="button"
                className={isDoctorLogin ? 'selected' : ''}
                aria-pressed={isDoctorLogin}
                onClick={() => changeMode('doctor')}
              >
                Doctor
              </button>
              </div>
            )}

            <form className="auth-form" onSubmit={submit}>
              {isCreatingAccount && (
                <label className="auth-field">
                  <span>Full name</span>
                  <input
                    required
                    autoComplete="name"
                    maxLength={120}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    placeholder="Your name"
                    disabled={busy}
                  />
                </label>
              )}
              <label className="auth-field">
                <span>Email address</span>
                <input
                  required
                  type="email"
                  autoComplete="email"
                  maxLength={254}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  disabled={busy}
                />
              </label>
              <label className="auth-field">
                <span>Password</span>
                <span className="auth-password-wrap">
                  <input
                    required
                    type={showPassword ? 'text' : 'password'}
                    autoComplete={isCreatingAccount ? 'new-password' : 'current-password'}
                    minLength={isCreatingAccount ? 12 : 1}
                    maxLength={256}
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder={isCreatingAccount ? 'At least 12 characters' : 'Enter your password'}
                    disabled={busy}
                  />
                  <button
                    className="auth-password-toggle"
                    type="button"
                    onClick={() => setShowPassword((visible) => !visible)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    aria-pressed={showPassword}
                    disabled={busy}
                  >
                    {showPassword ? (
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M3 3l18 18M10.6 10.7a2 2 0 002.7 2.7M9.9 5.2A10.8 10.8 0 0112 5c5.2 0 8.7 4.6 9.8 6.5a1 1 0 010 1 16 16 0 01-3.1 3.8M6.2 6.2A16 16 0 002.2 11.5a1 1 0 000 1C3.3 14.4 6.8 19 12 19a10.5 10.5 0 004-.8" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M2.2 11.5C3.3 9.6 6.8 5 12 5s8.7 4.6 9.8 6.5a1 1 0 010 1C20.7 14.4 17.2 19 12 19s-8.7-4.6-9.8-6.5a1 1 0 010-1z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    )}
                  </button>
                </span>
              </label>
              {error && <div className="error-banner" role="alert">{error}</div>}
              <button type="submit" className="btn btn-primary auth-submit" disabled={busy}>
                {busy
                  ? 'Please wait…'
                  : isDoctorRegistering
                    ? 'Create doctor account'
                    : isRegistering
                      ? 'Create patient account'
                      : isDoctorLogin
                        ? 'Sign in as doctor'
                        : 'Sign in as patient'}
                {!busy && <span aria-hidden="true">→</span>}
              </button>
            </form>

            {isDoctorRegistering ? (
              <p className="auth-role-note">
                Already have a doctor account?{' '}
                <button className="auth-inline-link" type="button" onClick={() => changeMode('doctor')}>
                  Doctor sign in
                </button>
              </p>
            ) : isRegistering ? (
              <p className="auth-role-note">
                Already registered?{' '}
                <button className="auth-inline-link" type="button" onClick={() => changeMode('patient')}>
                  Sign in
                </button>
                .
              </p>
            ) : isDoctorLogin ? (
              <p className="auth-role-note">
                New doctor?{' '}
                <button className="auth-inline-link" type="button" onClick={() => changeMode('doctor-register')}>
                  Create a doctor account
                </button>
              </p>
            ) : (
              <p className="auth-role-note">
                New to CardioSense?{' '}
                <button className="auth-inline-link" type="button" onClick={() => changeMode('register')}>
                  Create a patient account
                </button>
              </p>
            )}
            <p className="auth-disclaimer">
              Educational prototype only. Not for diagnosis, emergency use, or clinical decisions.
            </p>
          </div>
          <footer className="auth-content-footer">
            <span>CardioSense</span>
            <span>For learning and demonstration</span>
          </footer>
        </div>
      </section>
    </main>
  );
}
