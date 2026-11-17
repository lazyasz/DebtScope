/**
 * API Service Layer (Member 4 Integration)
 *
 * Centralized service for communication between React UI and FastAPI backend.
 * Connects to live FastAPI backend at http://localhost:8000.
 * Strict error propagation: no silent mock fallbacks.
 */

import axios from 'axios';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || '';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 5000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,  // send httpOnly session cookie on all requests
});

export const USE_REAL_API = true;

// "Explore sample data": read from the shared demo workspace instead of the user's own.
const SAMPLE_KEY = 'debtscope_sample_mode';
export function isSampleMode() {
  try { return localStorage.getItem(SAMPLE_KEY) === '1'; } catch { return false; }
}
export function setSampleMode(on) {
  try { on ? localStorage.setItem(SAMPLE_KEY, '1') : localStorage.removeItem(SAMPLE_KEY); } catch {}
}
apiClient.interceptors.request.use((config) => {
  if (isSampleMode()) config.headers['X-Workspace-Id'] = 'ws_demo';
  return config;
});

export async function getModelInfo() {
  const { data } = await apiClient.get('/api/predictions/model-info');
  return data;
}

export async function getDashboardSummary() {
  const { data } = await apiClient.get('/api/metrics/dashboard');
  return data;
}

export async function getRepositories() {
  const { data } = await apiClient.get('/api/repositories');
  return data;
}

/**
 * Checks if the current session is operating in the seeded demo / sandbox workspace.
 */
export function isDemoWorkspace() {
  const ws = localStorage.getItem('debtscope_workspace') || sessionStorage.getItem('debtscope_workspace');
  return !ws || ws === 'demo' || ws === 'ws_demo';
}

export async function getMetrics() {
  const { data } = await apiClient.get('/api/metrics');
  return data;
}

export async function getTechnicalDebt() {
  const { data } = await apiClient.get('/api/technical-debt');
  return data;
}

export async function getPredictions() {
  const { data } = await apiClient.get('/api/predictions');
  return data;
}

export async function getHotspots() {
  const { data } = await apiClient.get('/api/hotspots');
  return data;
}

export async function getPriorities(category = 'source') {
  const params = category ? { category } : {};
  const { data } = await apiClient.get('/api/priorities', { params });
  return data;
}

export async function getRecommendations() {
  const { data } = await apiClient.get('/api/recommendations');
  return data;
}

export async function getFile(id) {
  const { data } = await apiClient.get(`/api/files/${id}`);
  return data;
}

export async function scanRepository(url) {
  // Real scans fetch from GitHub and run the models; the 5 s default is far too short
  const { data } = await apiClient.post('/api/repositories/scan', { url }, { timeout: 180000 });
  return data;
}

export async function triggerBackgroundScan(url, authToken = null) {
  const { data } = await apiClient.post('/api/v1/jobs/scan', { url, auth_token: authToken });
  return data;
}

export async function getJobStatus(jobId) {
  const { data } = await apiClient.get(`/api/v1/jobs/${jobId}`);
  return data;
}

export async function listJobs() {
  const { data } = await apiClient.get('/api/v1/jobs');
  return data;
}

// -------------------------------------------------------------
// Authentication & RBAC APIs
// -------------------------------------------------------------
export async function getAuthMe() {
  const { data } = await apiClient.get('/api/auth/me');
  if (data?.workspace_id) {
    localStorage.setItem('debtscope_workspace', data.workspace_id);
  }
  return data;
}

export async function getDemoProfiles() {
  const { data } = await apiClient.get('/api/auth/profiles');
  return data;
}

export async function loginWithGoogle(credential) {
  const { data } = await apiClient.post('/api/auth/google', { credential });
  if (data?.workspace_id) {
    localStorage.setItem('debtscope_workspace', data.workspace_id);
  }
  return data;
}

export async function exchangeGoogleCode(code) {
  const { data } = await apiClient.post('/api/auth/google/code', { code });
  if (data?.workspace_id) {
    localStorage.setItem('debtscope_workspace', data.workspace_id);
  }
  return data;
}

export async function switchDemoProfile(profile_key) {
  const { data } = await apiClient.post('/api/auth/switch-profile', { profile_key });
  return data;
}

export async function logoutAuth() {
  try {
    const { data } = await apiClient.post('/api/auth/logout');
    localStorage.removeItem('debtscope_workspace');
    return data;
  } catch (err) {
    localStorage.removeItem('debtscope_workspace');
    throw err;
  }
}

// -------------------------------------------------------------
// Integrations: Jira & Notion APIs
// -------------------------------------------------------------

export async function updateIntegrationsConfig(config) {
  const { data } = await apiClient.post('/api/integrations/config', config);
  return data;
}

export async function createJiraIssue(payload) {
  const { data } = await apiClient.post('/api/integrations/jira/create-issue', payload);
  return data;
}

export async function bulkExportJira(payload) {
  const { data } = await apiClient.post('/api/integrations/jira/bulk-export', payload);
  return data;
}

export async function ingestNotionCriticality() {
  const { data } = await apiClient.post('/api/integrations/notion/ingest-criticality', {});
  return data;
}

export async function syncNotion(payload) {
  const { data } = await apiClient.post('/api/integrations/notion/sync', payload);
  return data;
}

export async function createNotionReport(payload) {
  const { data } = await apiClient.post('/api/integrations/notion/create-report', payload);
  return data;
}

// -------------------------------------------------------------
// Simulator, AI Recipe, CI/CD Risk Gate & Executive Report APIs
// -------------------------------------------------------------
export async function runWhatIfSimulation(payload) {
  // First call after a deploy loads the model, which takes longer than the 5 s default
  const { data } = await apiClient.post('/api/simulator/what-if', payload, { timeout: 60000 });
  return data;
}

export async function getAiRemediationRecipe(payload) {
  const { data } = await apiClient.post('/api/recommendations/ai-recipe', payload);
  return data;
}

export async function getIntegrationsStatus() {
  const { data } = await apiClient.get('/api/v1/integrations/status');
  return data;
}

export async function getProviderAuthUrl(provider, redirectUri = null) {
  const { data } = await apiClient.get(`/api/v1/integrations/${provider}/auth-url`, {
    params: redirectUri ? { redirect_uri: redirectUri } : {},
  });
  return data;
}

export async function exchangeProviderCode(provider, code, state = null, redirectUri = null) {
  const { data } = await apiClient.post(`/api/v1/integrations/${provider}/callback`, { code, state, redirect_uri: redirectUri }, { timeout: 30000 });
  return data;
}

export async function getProviderResources(provider, query = '') {
  const { data } = await apiClient.get(`/api/v1/integrations/${provider}/resources`, { params: query ? { q: query } : {}, timeout: 30000 });
  return data;
}

export async function syncProviderResources(provider, resourceIds) {
  const { data } = await apiClient.post(`/api/v1/integrations/${provider}/sync`, { resource_ids: resourceIds }, { timeout: 180000 });
  return data;
}

export async function disconnectProvider(provider) {
  const { data } = await apiClient.post(`/api/v1/integrations/${provider}/disconnect`);
  return data;
}

// ── Auth API helpers (P1) ─────────────────────────────────────────────────────

/**
 * Get the current authenticated user and sandbox_mode flag.
 * Uses httpOnly session cookie (credentials: 'include').
 * Returns null if unauthenticated.
 */
export async function getMe() {
  try {
    const res = await fetch('/api/v1/auth/me', { credentials: 'include' });
    if (!res.ok) return null;
    const data = await res.json();
    if (data?.workspace_id) {
      localStorage.setItem('debtscope_workspace', data.workspace_id);
    }
    return data;
  } catch (err) {
    console.warn('[API] /auth/me failed:', err.message);
    return null;
  }
}

/**
 * Log out — clears the httpOnly session cookie server-side.
 */
export async function logout() {
  try {
    await fetch('/api/v1/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });
    localStorage.removeItem('debtscope_workspace');
  } catch (err) {
    localStorage.removeItem('debtscope_workspace');
    console.warn('[API] logout failed:', err.message);
  }
}

export { apiClient };
export default apiClient;

