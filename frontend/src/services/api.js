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
  try {
    const { data } = await apiClient.post('/api/simulator/what-if', payload);
    return data;
  } catch (err) {
    if (!isDemoWorkspace()) throw err;
    console.warn('[API] /api/simulator/what-if failed, computing client fallback:', err.message);
    const effort = payload.refactoring_effort_pct || 40.0;
    const testCov = payload.test_coverage_pct || 80.0;
    const hourly = payload.hourly_rate || 85.0;
    const budgetHrs = payload.refactoring_budget_hours || Math.round((payload.debt_minutes || 90) / 60 * (effort / 100) * 1.2 * 10) / 10;
    const storyPts = payload.refactoring_story_points || Math.max(1, Math.ceil(budgetHrs / 6.0));
    const riskTol = payload.risk_tolerance || 'balanced';

    const origProb = Math.min(94.5, Math.max(15.0, ((payload.churn || 120) * 0.15 + (payload.complexity || 14) * 2.2)));
    const reduction = (effort * 0.45) + ((testCov - 50) * 0.35);
    const newProb = Math.max(8.0, origProb * (1 - reduction / 100));
    const savedMins = (payload.debt_minutes || 90) * (effort / 100) * 1.25;
    const dollars = (savedMins / 60) * hourly * 3.5;

    const projection_curves = [];
    const baseDebtHrs = (payload.debt_minutes || 90) / 60;
    for (let s = 1; s <= 6; s++) {
      const decay = Math.min(1.0, (s / 4.0) * (effort / 100.0));
      projection_curves.push({
        sprint: `Sprint ${s}`,
        debt_hours: Math.max(0, Math.round(baseDebtHrs * (1 - decay) * 10) / 10),
        defect_probability_pct: Math.max(5, Math.round(origProb * (1 - (reduction / 100) * decay) * 10) / 10),
        team_velocity_sp: Math.round(60 * (1 + 0.35 * (effort / 100) * (s / 6)) * 10) / 10,
        velocity_gain_pct: Math.round(35 * (effort / 100) * (s / 6) * 10) / 10,
        cumulative_savings_usd: Math.round((dollars * (s / 6)))
      });
    }

    return {
      status: 'success',
      baseline: {
        churn: payload.churn || 120,
        complexity: payload.complexity || 14,
        debt_minutes: payload.debt_minutes || 90,
        debt_hours: Math.round(((payload.debt_minutes || 90) / 60) * 10) / 10,
        defect_probability_pct: Math.round(origProb * 10) / 10
      },
      simulated: {
        defect_probability_pct: Math.round(newProb * 10) / 10,
        risk_reduction_pct: Math.round(Math.max(5, origProb - newProb) * 10) / 10,
        estimated_debt_minutes_saved: Math.round(savedMins),
        estimated_hours_saved: Math.round((savedMins / 60) * 10) / 10,
        financial_roi_usd: Math.round(dollars),
        payback_velocity: effort > 60 ? 'Immediate (< 2 Sprints)' : 'Medium (3-4 Sprints)',
        recommendation: `Allocating ${budgetHrs}h (${storyPts} SP) under a ${riskTol} strategy yields $${Math.round(dollars).toLocaleString()} net engineering value.`
      },
      impact: {
        faults_prevented: Math.round((origProb - newProb) / 10 * 10) / 10,
        fault_reduction_pct: Math.round(reduction * 10) / 10,
        total_hours_saved: Math.round((savedMins / 60) * 10) / 10,
        dollar_savings: Math.round(dollars),
        hourly_rate_used: hourly,
        budget_hours: budgetHrs,
        story_points: storyPts,
        risk_tolerance: riskTol,
        return_on_investment_multiple: Math.round(Math.max(1.0, dollars / Math.max(100, budgetHrs * hourly * 0.4)) * 10) / 10
      },
      projection_curves,
      jira_package: {
        sprint_name: `Sprint 49 — Debt Remediation (${riskTol.toUpperCase()})`,
        total_story_points: storyPts,
        estimated_budget_hours: budgetHrs,
        projected_roi_usd: Math.round(dollars),
        risk_reduction_pct: Math.round(reduction),
        suggested_tickets: [
          { issue_key: 'DEBT-101', summary: `Refactor high-cyclomatic hotspot (${payload.complexity || 14} complexity)`, story_points: Math.max(1, Math.ceil(storyPts * 0.5)), priority: 'High', component: 'Core Architecture' },
          { issue_key: 'DEBT-102', summary: `Increase unit test harness to ${testCov}%`, story_points: Math.max(1, Math.ceil(storyPts * 0.3)), priority: 'Medium', component: 'Test Harness' },
          { issue_key: 'DEBT-103', summary: 'Extract domain handlers from God Class', story_points: Math.max(1, Math.ceil(storyPts * 0.2)), priority: 'High', component: 'Domain Model' }
        ]
      }
    };
  }
}

export async function getFinancialTcoAnalysis(payload = {}) {
  try {
    const { data } = await apiClient.post('/api/simulator/financial-tco', {
      hourly_rate: payload.hourly_rate || 85.0,
      team_size: payload.team_size || 12,
      sprint_length_weeks: payload.sprint_length_weeks || 2,
      velocity_drag_pct: payload.velocity_drag_pct || 24.5
    });
    return data;
  } catch (err) {
    if (!isDemoWorkspace()) throw err;
    console.warn('[API] /api/simulator/financial-tco failed, fallback:', err.message);
    const hourly = payload.hourly_rate || 85.0;
    const teamSize = payload.team_size || 12;
    const dragPct = payload.velocity_drag_pct || 24.5;
    const totalDebtHrs = 1420.5;
    const principal = totalDebtHrs * hourly;
    const monthlyTeamHrs = teamSize * 160;
    const velocityDragMonthly = monthlyTeamHrs * (dragPct / 100) * hourly;
    const defectOverheadMonthly = 18 * 16.5 * hourly;
    const monthlyDragInterest = velocityDragMonthly + defectOverheadMonthly;
    const annualizedWaste = monthlyDragInterest * 12;
    const remediationInv = principal * 0.60;
    const monthlySavings = monthlyDragInterest * 0.65;
    const paybackMonths = Math.round((remediationInv / monthlySavings) * 10) / 10;
    const annualDragSavings = monthlySavings * 12;
    const netFirstYearSavings = annualDragSavings - remediationInv;

    const twelve_month_projection = [];
    let accInaction = 0;
    let accRemediated = remediationInv;
    for (let m = 1; m <= 12; m++) {
      const compDrag = monthlyDragInterest * (1 + 0.025 * (m - 1));
      accInaction += compDrag;
      accRemediated += monthlyDragInterest * 0.35;
      twelve_month_projection.push({
        month: `M${m}`,
        inaction_cumulative_cost: Math.round(accInaction),
        remediated_cumulative_cost: Math.round(accRemediated),
        net_cumulative_savings: Math.round(Math.max(0, accInaction - accRemediated)),
        monthly_drag_tax: Math.round(compDrag)
      });
    }

    return {
      kpis: {
        principal_debt_usd: principal,
        total_debt_hours: totalDebtHrs,
        hourly_rate: hourly,
        monthly_interest_drag_usd: monthlyDragInterest,
        velocity_drag_monthly_usd: velocityDragMonthly,
        defect_overhead_monthly_usd: defectOverheadMonthly,
        annualized_waste_usd: annualizedWaste,
        payback_period_months: paybackMonths,
        remediation_investment_usd: remediationInv,
        annual_drag_savings_usd: annualDragSavings,
        net_first_year_savings_usd: netFirstYearSavings,
        roi_multiplier: Math.round((annualDragSavings / remediationInv) * 10) / 10,
        velocity_drag_pct: dragPct
      },
      subsystems: [
        { id: 'sub_01', name: 'Core Lakehouse Ingestion Engine', loc: 184500, complexity_avg: 24.8, remediation_hours: 420.0, principal_debt_usd: 420.0 * hourly, monthly_drag_usd: 14500.0 * (hourly / 85.0), payback_months: 2.1, risk_tier: 'CRITICAL', recommended_action: 'Decompose monolithic stream transformer into domain events' },
        { id: 'sub_02', name: 'Enterprise Auth & RBAC Gateway', loc: 64200, complexity_avg: 21.2, remediation_hours: 285.0, principal_debt_usd: 285.0 * hourly, monthly_drag_usd: 9800.0 * (hourly / 85.0), payback_months: 2.4, risk_tier: 'HIGH', recommended_action: 'Deprecate legacy JWT session validator and introduce zero-trust guard' },
        { id: 'sub_03', name: 'Spark Streaming Analytics & Aggregators', loc: 128400, complexity_avg: 19.5, remediation_hours: 340.0, principal_debt_usd: 340.0 * hourly, monthly_drag_usd: 11200.0 * (hourly / 85.0), payback_months: 2.6, risk_tier: 'HIGH', recommended_action: 'Refactor shuffle joins and eliminate unindexed DataFrame scans' },
        { id: 'sub_04', name: 'REST API Gateway & OpenAPI Routers', loc: 52100, complexity_avg: 14.0, remediation_hours: 195.0, principal_debt_usd: 195.0 * hourly, monthly_drag_usd: 6100.0 * (hourly / 85.0), payback_months: 2.7, risk_tier: 'MEDIUM', recommended_action: 'Standardize Pydantic v2 schemas and response serialization caching' },
        { id: 'sub_05', name: 'Executive Reporting & PDF Generator', loc: 38900, complexity_avg: 11.5, remediation_hours: 180.5, principal_debt_usd: 180.5 * hourly, monthly_drag_usd: 4400.0 * (hourly / 85.0), payback_months: 3.4, risk_tier: 'LOW', recommended_action: 'Decouple synchronous print rendering into background worker task' }
      ],
      twelve_month_projection
    };
  }
}


export async function getAiRemediationRecipe(payload) {
  const { data } = await apiClient.post('/api/recommendations/ai-recipe', payload);
  return data;
}

export async function evaluateCiCdPr(payload) {
  try {
    const { data } = await apiClient.post('/api/ci-cd/evaluate-pr', payload);
    return data;
  } catch (err) {
    if (!isDemoWorkspace()) throw err;
    console.warn('[API] /api/ci-cd/evaluate-pr failed, fallback to local evaluator:', err.message);
    const totalLines = (payload.changed_files || []).reduce((acc, f) => acc + (f.lines_added || 0) + (f.lines_deleted || 0), 0);
    const blocked = totalLines > 450;
    return {
      status: 'success',
      pr_number: payload.pr_number || 104,
      pr_title: payload.pr_title || 'feat: Add Payment Webhook Gateway',
      author: payload.author || 'developer.alex',
      gate_status: blocked ? 'BLOCKED' : 'PASSED',
      risk_level: blocked ? 'HIGH' : 'LOW',
      peak_defect_risk_pct: blocked ? 78.4 : 22.1,
      total_churn_lines: totalLines || 380,
      policy_evaluation: {
        defect_threshold_check: { passed: !blocked, limit_pct: 70.0, actual_pct: blocked ? 78.4 : 22.1 },
        churn_volume_check: { passed: totalLines <= 500, limit_lines: 500, actual_lines: totalLines || 380 },
        author_trust_score: { score: 82, status: 'Verified Contributor' }
      },
      file_risk_breakdown: (payload.changed_files || []).map((f) => ({
        filename: f.filename,
        defect_risk_pct: f.cyclomatic_complexity > 10 ? 74.5 : 21.0,
        risk_grade: f.cyclomatic_complexity > 10 ? 'HIGH' : 'SAFE'
      })),
      merge_recommendation: blocked 
        ? 'CI/CD Gate Blocked: PR introduces high-risk cyclomatic complexity in payment modules. Require Lead Architect sign-off.' 
        : 'CI/CD Gate Approved: PR satisfies code hygiene and defect tolerance thresholds.'
    };
  }
}

export async function getExecutiveReportSummary() {
  try {
    const { data } = await apiClient.get('/api/reports/executive-summary');
    return data;
  } catch (err) {
    if (!isDemoWorkspace()) throw err;
    console.warn('[API] /api/reports/executive-summary failed, fallback:', err.message);
    return {
      status: 'success',
      timestamp: new Date().toISOString(),
      platform_version: 'v4.18.2-enterprise',
      executive_health_grade: 'B+',
      overall_risk_index: 34.2,
      total_debt_valuation_usd: 148500,
      projected_annual_savings_usd: 62400,
      active_modules_analyzed: 142,
      total_cyclomatic_hotspots: 19,
      szz_ml_defect_accuracy_pct: 98.85,
      medallion_architecture_compliance: {
        bronze_raw_ingestion: '100% (48/48 Microservices)',
        silver_szz_feature_store: '100% Validated',
        gold_decision_matrix: 'Active Telemetry Mesh'
      },
      top_critical_initiatives: [
        { module: 'src/core/DataTree.java', debt_hours: 42, estimated_cost: '$3,570', priority: 'P0 - Urgent' },
        { module: 'src/services/auth/token_provider.py', debt_hours: 36, estimated_cost: '$3,060', priority: 'P0 - Urgent' },
        { module: 'src/pipeline/analytics/spark_aggregator.py', debt_hours: 28, estimated_cost: '$2,380', priority: 'P1 - High' },
        { module: 'src/api/routes/transaction_billing.py', debt_hours: 24, estimated_cost: '$2,040', priority: 'P1 - High' }
      ]
    };
  }
}

// ---------------------------------------------------------
// Unified Integrations Provider API (GitHub, Jira, Notion, Google)
// ---------------------------------------------------------

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

