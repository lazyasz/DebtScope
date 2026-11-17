import React, { createContext, useContext, useState, useEffect } from 'react';
import { getAuthMe, logoutAuth, getIntegrationsStatus } from '../services/api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  // The server session (httpOnly cookie) is the only source of truth for who is signed in.
  const [user, setUser] = useState(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [sandboxMode, setSandboxMode] = useState(false);
  const [integrations, setIntegrations] = useState({});
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
    } catch {
      setUser(null); // 401 = no session
      setIsLoggedIn(false);
    } finally {
      setAuthChecked(true);
    }
  };

  const refreshIntegrations = async () => {
    try {
      const data = await getIntegrationsStatus();
      if (data) setIntegrations(data);
    } catch {
      // not signed in yet, or server unreachable; pages show their own errors
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  useEffect(() => {
    if (isLoggedIn) refreshIntegrations();
  }, [isLoggedIn]);

  const handleLogout = async () => {
    try {
      window.google?.accounts?.id?.disableAutoSelect?.();
      await logoutAuth();
    } catch {
      // the cookie is cleared server-side; navigate away regardless
    }
    setIsLoggedIn(false);
    setUser(null);
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
        integrations,
        refreshIntegrations,
        notification,
        showNotification,
        notify: showNotification,
        handleLogout,
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
