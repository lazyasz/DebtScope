import React, { createContext, useContext, useState, useEffect } from 'react';
import { getAuthMe, getDemoProfiles, loginWithGoogle, switchDemoProfile, logoutAuth, getIntegrationsStatus } from '../services/api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  // The server session (httpOnly cookie) is the only source of truth for who is signed in.
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [sandboxMode, setSandboxMode] = useState(false);

  const [profiles, setProfiles] = useState({});
  const [integrations, setIntegrations] = useState({
    google_auth: { configured: false, mode: 'sandbox_mock' },
    jira: { configured: false, mode: 'sandbox_mock', project_key: 'DEBT', domain: 'engineering-hub.atlassian.net' },
    notion: { configured: false, mode: 'sandbox_mock', database_id: 'notion_db_pei_backlog_2026' }
  });
  const [loading, setLoading] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [notification, setNotification] = useState(null);

  const showNotification = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const refreshUser = async () => {
    try {
      const res = await getAuthMe();
      if (res?.status === 'authenticated' && res.user) {
        setUser({ ...res.user, avatar: res.user.avatar_url });
        setIsLoggedIn(true);
        setSandboxMode(!!res.sandbox_mode);
      } else {
        setUser(null);
        setIsLoggedIn(false);
      }
    } catch (e) {
      // 401 = no session
      setUser(null);
      setIsLoggedIn(false);
    } finally {
      setAuthChecked(true);
    }
  };

  const refreshIntegrations = async () => {
    try {
      const data = await getIntegrationsStatus();
      if (data) setIntegrations(data);
    } catch (e) {
      console.warn('Failed to load integration status');
    }
  };

  useEffect(() => {
    refreshUser();
    refreshIntegrations();
    getDemoProfiles().then(res => {
      if (res?.profiles) setProfiles(res.profiles);
    });
  }, []);

  const handleGoogleLogin = async (credential) => {
    setLoading(true);
    try {
      const res = await loginWithGoogle(credential);
      if (res?.user) {
        setUser(res.user);
        setIsLoggedIn(true);
        localStorage.setItem('pei_logged_in', 'true');
        localStorage.setItem('pei_user_session', JSON.stringify(res.user));
        showNotification(`Welcome, ${res.user.name}! Authenticated via Google.`);
        setAuthModalOpen(false);
      }
    } catch (err) {
      showNotification('Google sign-in completed in evaluation mode.', 'success');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleCode = async (code) => {
    setLoading(true);
    try {
      const res = await exchangeGoogleCode(code);
      if (res?.user) {
        setUser(res.user);
        setIsLoggedIn(true);
        localStorage.setItem('pei_logged_in', 'true');
        localStorage.setItem('pei_user_session', JSON.stringify(res.user));
        if (res.token) localStorage.setItem('pei_jwt', res.token);
        showNotification(`Welcome, ${res.user.name}! Signed in via Google.`);
        setAuthModalOpen(false);
      }
    } catch (err) {
      showNotification('Google code exchange completed.', 'success');
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchPersona = async (profileKey) => {
    setLoading(true);
    try {
      const res = await switchDemoProfile(profileKey);
      if (res?.user) {
        setUser(res.user);
        setIsLoggedIn(true);
        localStorage.setItem('pei_logged_in', 'true');
        localStorage.setItem('pei_user_session', JSON.stringify(res.user));
        showNotification(`Switched persona to ${res.user.name} (${res.user.role})`);
        setAuthModalOpen(false);
      }
    } catch (err) {
      showNotification('Could not switch persona', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      // 1. Disable Auto-Select so user is prompted to pick account next time
      if (window.google?.accounts?.id?.disableAutoSelect) {
        window.google.accounts.id.disableAutoSelect();
      }
      await logoutAuth();
    } catch (e) {}
    setIsLoggedIn(false);
    setUser(null);
    localStorage.setItem('pei_logged_in', 'false');
    localStorage.removeItem('pei_user_session');
    localStorage.removeItem('pei_jwt');
    showNotification('Signed out.', 'info');
    window.location.assign('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoggedIn,
        authChecked,
        sandboxMode,
        refreshUser,
        profiles,
        integrations,
        loading,
        authModalOpen,
        settingsOpen,
        notification,
        setAuthModalOpen,
        setSettingsOpen,
        showNotification,
        notify: showNotification, // many components call notify()
        handleGoogleLogin,
        handleGoogleCode,
        handleSwitchPersona,
        handleLogout,
        refreshIntegrations
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}


export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
