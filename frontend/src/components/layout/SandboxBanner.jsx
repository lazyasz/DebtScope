import { useEffect, useState } from 'react';

/**
 * SandboxBanner
 *
 * Renders a persistent amber banner when DEV_SANDBOX_AUTH is active on the backend.
 * Detected by /api/v1/auth/me returning sandbox_mode: true.
 * Never visible in production.
 */
export default function SandboxBanner() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    fetch('/api/v1/auth/me', { credentials: 'include' })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.sandbox_mode === true) setShow(true);
      })
      .catch(() => {});
  }, []);

  if (!show) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="w-full bg-amber-500 text-amber-950 text-xs font-semibold text-center px-4 py-1.5 z-50 select-none"
    >
      ⚠️{' '}
      <strong>DEV SANDBOX AUTH ACTIVE</strong>
      {' — '}
      Using simulated identities. Disable{' '}
      <code className="font-mono bg-amber-400 px-1 rounded">DEV_SANDBOX_AUTH</code>
      {' '}for production.
    </div>
  );
}
