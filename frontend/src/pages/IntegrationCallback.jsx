import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { exchangeProviderCode } from '../services/api';
import LoadingState from '../components/ui/LoadingState';
import { callbackUrl } from './IntegrationsHub';

// The provider sends the user back here with ?code&state after they approve access.
export default function IntegrationCallback() {
  const { provider } = useParams();
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const state = params.get('state');
    const expected = sessionStorage.getItem(`oauth_state_${provider}`);
    sessionStorage.removeItem(`oauth_state_${provider}`);

    if (params.get('error')) return setError(`${provider} sign-in was cancelled.`);
    if (!code) return setError('No authorization code was returned.');
    if (!expected || expected !== state) return setError('This sign-in link expired or was tampered with. Please try again.');

    exchangeProviderCode(provider, code, state, callbackUrl(provider))
      .then(() => navigate('/integrations', { replace: true }))
      .catch((e) => setError(e?.response?.data?.detail || 'Connecting failed.'));
  }, [provider, navigate]);

  if (!error) return <LoadingState message={`Connecting your ${provider} account...`} />;
  return (
    <div className="max-w-md mx-auto py-16 px-4 text-center space-y-3">
      <p className="text-sm font-semibold text-[#161e10]">Couldn't connect {provider}</p>
      <p className="text-xs text-[#45483e]">{error}</p>
      <button onClick={() => navigate('/integrations')} className="text-xs font-bold text-[#43562b] hover:underline cursor-pointer">
        Back to Integrations
      </button>
    </div>
  );
}
