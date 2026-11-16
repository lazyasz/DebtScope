import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AppLayout from './components/layout/AppLayout';
import SandboxBanner from './components/layout/SandboxBanner';
import LenisSmoothScroll from './components/ui/LenisSmoothScroll';
import LoadingState from './components/ui/LoadingState';

// Route-level code splitting for performance and bundle size reduction
const Login = lazy(() => import('./pages/Login'));
const AuthCallback = lazy(() => import('./pages/AuthCallback'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const TechnicalDebt = lazy(() => import('./pages/TechnicalDebt'));
const Predictions = lazy(() => import('./pages/Predictions'));
const Priorities = lazy(() => import('./pages/Priorities'));
const Hotspots = lazy(() => import('./pages/Hotspots'));
const FileIntelligence = lazy(() => import('./pages/FileIntelligence'));
const Copilot = lazy(() => import('./pages/Copilot'));
const DataQuality = lazy(() => import('./pages/DataQuality'));
const Simulator = lazy(() => import('./pages/Simulator'));
const IntegrationsHub = lazy(() => import('./pages/IntegrationsHub'));

const fullPageLoader = (
  <div className="min-h-[60vh] flex items-center justify-center">
    <LoadingState message="Loading DebtScope intelligence view..." />
  </div>
);

// App pages need a server session; the login page should not show once signed in.
function RequireAuth({ children }) {
  const { authChecked, isLoggedIn } = useAuth();
  if (!authChecked) return fullPageLoader;
  return isLoggedIn ? children : <Navigate to="/login" replace />;
}

function GuestOnly({ children }) {
  const { authChecked, isLoggedIn } = useAuth();
  if (!authChecked) return fullPageLoader;
  return isLoggedIn ? <Navigate to="/dashboard" replace /> : children;
}

export default function App() {
  return (
    <AuthProvider>
      {/* Sandbox banner renders at the very top — visible on all pages */}
      <SandboxBanner />
      <LenisSmoothScroll>
        <BrowserRouter>
          <Suspense fallback={fullPageLoader}>
            <Routes>
              {/* Auth routes */}
              <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
              <Route path="/auth/callback" element={<AuthCallback />} />

              {/* Main App Layout — signed-in users only */}
              <Route element={<RequireAuth><AppLayout /></RequireAuth>}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/integrations" element={<IntegrationsHub />} />
                <Route path="/simulator" element={<Simulator />} />
                <Route path="/debt" element={<TechnicalDebt />} />
                <Route path="/predictions" element={<Predictions />} />
                <Route path="/priorities" element={<Priorities />} />
                <Route path="/hotspots" element={<Hotspots />} />
                <Route path="/data-quality" element={<DataQuality />} />
                <Route path="/files/:id" element={<FileIntelligence />} />
                <Route path="/copilot" element={<Copilot />} />
              </Route>
              <Route path="*" element={<Navigate to="/dashboard" replace />} />

            </Routes>
          </Suspense>
        </BrowserRouter>
      </LenisSmoothScroll>
    </AuthProvider>
  );
}
