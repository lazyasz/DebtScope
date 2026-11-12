import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Login page — Google OAuth sign-in entry point.
 * Redirects to /dashboard if already authenticated.
 */
export default function Login() {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);
  const [sandboxMode, setSandboxMode] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Check for error in query string (from OAuth redirect)
    const params = new URLSearchParams(window.location.search);
    const err = params.get('error');
    if (err) {
      const messages = {
        google_denied: 'Google sign-in was cancelled.',
        state_mismatch: 'Security check failed. Please try again.',
        auth_failed: 'Authentication failed. Please try again.',
        server_error: 'Server error during sign-in. Please try again.',
      };
      setError(messages[err] || 'Sign-in failed. Please try again.');
    }

    // Check if already logged in
    fetch('/api/v1/auth/me', { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => {
        if (data?.status === 'authenticated') {
          navigate('/dashboard', { replace: true });
        } else {
          setSandboxMode(data?.sandbox_mode === true);
          setChecking(false);
        }
      })
      .catch(() => setChecking(false));
  }, [navigate]);

  const handleGoogleLogin = () => {
    // Backend redirects to Google consent screen (server-side Authorization Code Flow)
    window.location.href = '/api/v1/auth/google/login';
  };

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="animate-pulse text-gray-400 text-sm">Checking session…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 px-4">
      {/* Sandbox banner inside login page */}
      {sandboxMode && (
        <div className="fixed top-0 left-0 right-0 bg-amber-500 text-amber-950 text-xs font-semibold text-center py-1.5 z-50">
          ⚠️ <strong>DEV SANDBOX AUTH ACTIVE</strong> — Clicking sign in will auto-login with the sandbox profile.
        </div>
      )}

      {/* Logo */}
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-white tracking-tight">
          Debt<span className="text-emerald-400">Scope</span>
        </h1>
        <p className="mt-2 text-gray-400 text-sm">Predictive Engineering Intelligence</p>
      </div>

      {/* Card */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 w-full max-w-sm shadow-2xl">
        <h2 className="text-lg font-semibold text-white mb-1">Sign in</h2>
        <p className="text-gray-400 text-sm mb-6">
          Connect your Google account to get started.
        </p>

        {error && (
          <div className="mb-4 px-3 py-2 rounded-lg bg-red-900/40 border border-red-700/60 text-red-300 text-xs">
            ⚠️ {error}
          </div>
        )}

        <button
          onClick={handleGoogleLogin}
          className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-100 text-gray-800 font-medium rounded-lg px-4 py-3 transition-colors text-sm cursor-pointer"
        >
          {/* Google G icon */}
          <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true">
            <path fill="#EA4335" d="M24 9.5c3.14 0 5.95 1.08 8.17 2.86l6.1-6.1C34.48 3.14 29.54 1 24 1 14.73 1 6.78 6.48 3.14 14.37l7.1 5.52C12.03 13.57 17.54 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.52 24.5c0-1.56-.14-3.07-.4-4.5H24v8.52h12.68c-.55 2.94-2.2 5.44-4.68 7.12l7.18 5.57C43.44 37.44 46.52 31.5 46.52 24.5z"/>
            <path fill="#FBBC05" d="M10.24 28.11A14.6 14.6 0 019.5 24c0-1.43.2-2.82.56-4.11l-7.1-5.52A23.95 23.95 0 001 24c0 3.87.93 7.53 2.57 10.77l6.67-6.66z"/>
            <path fill="#34A853" d="M24 47c5.54 0 10.19-1.84 13.59-4.98l-7.18-5.57c-1.84 1.23-4.19 1.95-6.41 1.95-6.46 0-11.97-4.07-13.76-9.69l-6.67 6.66C6.78 41.52 14.73 47 24 47z"/>
          </svg>
          {sandboxMode ? 'Continue (Sandbox Auto-Login)' : 'Continue with Google'}
        </button>
      </div>

      <p className="mt-6 text-gray-600 text-xs">Academic project — PBL 2026</p>
    </div>
  );
}
