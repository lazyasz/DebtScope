import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import AppLayout from './components/layout/AppLayout';
import SandboxBanner from './components/layout/SandboxBanner';
import LenisSmoothScroll from './components/ui/LenisSmoothScroll';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import TechnicalDebt from './pages/TechnicalDebt';
import Predictions from './pages/Predictions';
import Priorities from './pages/Priorities';
import Hotspots from './pages/Hotspots';
import FileIntelligence from './pages/FileIntelligence';
import Copilot from './pages/Copilot';
import DataQuality from './pages/DataQuality';
import Simulator from './pages/Simulator';
import AuthCallback from './pages/AuthCallback';
import IntegrationsHub from './pages/IntegrationsHub';

export default function App() {
  return (
    <AuthProvider>
      {/* Sandbox banner renders at the very top — visible on all pages */}
      <SandboxBanner />
      <LenisSmoothScroll>
        <BrowserRouter>
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
        </BrowserRouter>
      </LenisSmoothScroll>
    </AuthProvider>
  );
}
