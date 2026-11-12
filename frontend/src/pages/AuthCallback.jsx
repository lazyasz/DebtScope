import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ShieldCheck } from 'lucide-react';

/**
 * AuthCallback — handles Google OAuth redirect.
 *
 * New flow (P1): backend sets httpOnly cookie and redirects to / (or /auth/callback).
 * We just verify the session via /api/v1/auth/me and navigate to /dashboard.
 *
 * Legacy flow: also handles #token=... fragment for backward compat with old popup flow.
 */
export default function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const handleCallback = async () => {
      // 1. Check for error query param
      const params = new URLSearchParams(window.location.search);
      if (params.get('error')) {
        console.warn('[AuthCallback] OAuth error:', params.get('error'));
        navigate('/login?error=' + params.get('error'), { replace: true });
        return;
      }

      // 2. Try session cookie (new P1 flow — backend already set it)
      try {
        const res = await fetch('/api/v1/auth/me', { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          if (data?.status === 'authenticated') {
            navigate('/dashboard', { replace: true });
            return;
          }
        }
      } catch (e) {
        console.warn('[AuthCallback] /auth/me failed:', e);
      }

      // 3. Legacy: JWT fragment (#token=...)
      const hash = window.location.hash;
      const hashParams = new URLSearchParams(hash.replace('#', '?'));
      const token = hashParams.get('token');
      if (token) {
        // Store in localStorage for legacy AuthContext compatibility
        localStorage.setItem('pei_jwt_token', token);
        navigate('/dashboard', { replace: true });
        return;
      }

      // 4. No session found — back to login
      navigate('/login', { replace: true });
    };

    handleCallback();
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 text-white p-4">
      <div className="text-center space-y-4 max-w-sm p-6 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl">
        <div className="w-12 h-12 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto border border-emerald-500/30">
          <ShieldCheck className="h-6 w-6" />
        </div>
        <h3 className="text-base font-bold">Completing Sign In</h3>
        <p className="text-xs text-slate-400">
          Verifying your Google credentials and establishing a secure session…
        </p>
        <div className="flex justify-center pt-2">
          <Loader2 className="h-5 w-5 animate-spin text-emerald-400" />
        </div>
      </div>
    </div>
  );
}
