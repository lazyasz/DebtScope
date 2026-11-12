import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
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

export default function App() {
  return (
    <AuthProvider>
      {/* Sandbox banner renders at the very top — visible on all pages */}
      <SandboxBanner />
      <LenisSmoothScroll>
        <BrowserRouter>
          <Suspense
            fallback={
              <div className="min-h-[60vh] flex items-center justify-center">
                <LoadingState message="Loading DebtScope intelligence view..." />
              </div>
            }
          >
            <Routes>
              {/* Auth routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/auth/callback" element={<AuthCallback />} />

              {/* Main App Layout */}
              <Route element={<AppLayout />}>
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
            </Routes>
          </Suspense>
        </BrowserRouter>
      </LenisSmoothScroll>
    </AuthProvider>
  );
}
