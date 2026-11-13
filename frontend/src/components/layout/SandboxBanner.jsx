import { useEffect, useState } from 'react';

/**
 * SandboxBanner
 *
 * Renders a persistent amber banner when any simulated mode is active:
 * - DEV_SANDBOX_AUTH
 * - JIRA_SIMULATION_MODE
 * - NOTION_SIMULATION_MODE
 *
 * Refuses ENVIRONMENT=production on backend. Never visible in live production.
 */
export default function SandboxBanner() {
  const [show, setShow] = useState(false);
  const [activeModes, setActiveModes] = useState([]);

  useEffect(() => {
    fetch('/api/v1/auth/me', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.sandbox_mode === true || data?.active_simulations) {
          const modes = [];
          if (data?.sandbox_mode || data?.active_simulations?.auth) {
            modes.push('DEV_SANDBOX_AUTH');
          }
          if (data?.active_simulations?.jira) {
            modes.push('JIRA_SIMULATION');
          }
          if (data?.active_simulations?.notion) {
            modes.push('NOTION_SIMULATION');
          }
          if (modes.length > 0) {
            setActiveModes(modes);
            setShow(true);
          }
        }
      })
      .catch(() => {});
  }, []);

  if (!show) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="w-full bg-amber-500 text-amber-950 text-xs font-semibold text-center px-4 py-1.5 z-50 select-none shadow-sm"
    >
      ⚠️{' '}
      <strong>SIMULATED MODES ACTIVE:</strong>{' '}
      {activeModes.map((m) => (
        <span
          key={m}
          className="inline-block mx-1 font-mono bg-amber-400 px-1.5 py-0.5 rounded text-amber-950 font-bold"
        >
          {m}
        </span>
      ))}
      {' — '}
      Simulated telemetry & test identities. All simulation modes strictly refuse{' '}
      <code className="font-mono bg-amber-400 px-1 rounded">ENVIRONMENT=production</code>.
    </div>
  );
}
