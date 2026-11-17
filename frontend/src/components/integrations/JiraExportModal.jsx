import React, { useEffect, useState } from 'react';
import { createJiraIssue, bulkExportJira, getProviderResources } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { Layers, CheckCircle2, ExternalLink, X, Sparkles, AlertCircle } from 'lucide-react';

export default function JiraExportModal({ isOpen, onClose, item, component, isBulk = false, components = [] }) {
  const targetComponent = component || item;
  const targetComponents = components;
  const { showNotification, notify } = useAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const [projectKey, setProjectKey] = useState('');
  const [projects, setProjects] = useState(null); // null = loading, [] = none/not connected
  const [projectsError, setProjectsError] = useState(null);
  const [issueType, setIssueType] = useState('Task');
  const sprintName = 'DebtScope priorities';

  useEffect(() => {
    if (!isOpen) return;
    getProviderResources('jira')
      .then((r) => {
        const list = r.connected ? r.projects || [] : [];
        setProjectsError(r.connected && !list.length ? r.error || 'No projects found in your Jira.' : null);
        setProjects(list);
        if (list.length) setProjectKey((k) => k || list[0].key);
      })
      .catch(() => setProjects([]));
  }, [isOpen]);

  if (!isOpen) return null;

  const notifyUser = (msg) => {
    if (showNotification) showNotification(msg);
    else if (notify) notify(msg);
  };

  const handleExport = async () => {
    setLoading(true);
    try {
      if (isBulk) {
        const payload = {
          sprint_name: sprintName,
          project_key: projectKey || null,
          components: targetComponents.map((c) => ({
            component_name: c.component || c.file_path || c.name || c.file || 'Component',
            priority_score: c.priority_score || c.priority || 75.0,
            remediation_effort_hours: c.remediation_effort_hours || c.remediation_effort || 8.0,
            defect_probability: c.defect_probability || 0.45,
            technical_risk: c.technical_risk || c.risk_score || 60.0,
            business_impact: c.business_impact || 70.0,
            roi_quadrant: c.roi_quadrant || 'Quick Wins',
            issue_type: issueType,
          })),
        };
        const res = await bulkExportJira(payload);
        setResult(res);
        notifyUser(res.mode === 'sandbox_mock'
          ? 'Simulated only: Jira is not connected, no tickets were created.'
          : `Created ${res.total_tickets_created} Jira tickets in ${res.project_key}.`);
      } else {
        const payload = {
          component_name: targetComponent?.component || targetComponent?.name || targetComponent?.file || 'Component',
          priority_score: targetComponent?.priority_score || targetComponent?.priority || 75.0,
          remediation_effort_hours: targetComponent?.remediation_effort_hours || targetComponent?.remediation_effort || 8.0,
          defect_probability: targetComponent?.defect_probability || 0.45,
          technical_risk: targetComponent?.technical_risk || targetComponent?.risk_score || 60.0,
          business_impact: targetComponent?.business_impact || 70.0,
          roi_quadrant: targetComponent?.roi_quadrant || 'Quick Wins',
          issue_type: issueType,
          project_key: projectKey || null,
          summary: `[Tech Debt] Refactor high-risk component: ${targetComponent?.component || targetComponent?.name || targetComponent?.file || 'Component'}`,
        };
        const res = await createJiraIssue(payload);
        setResult(res);
        notifyUser(res.mode === 'sandbox_mock'
          ? 'Simulated only: Jira is not connected, no ticket was created.'
          : `Created Jira ticket ${res.issue_key}.`);
      }
    } catch (err) {
      const message = err?.response?.data?.detail || err?.message || 'Request failed';
      setResult({ status: 'error', message });
      notifyUser(`Jira export failed: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setResult(null);
    onClose();
  };

  const effortHours = targetComponent?.remediation_effort_hours || targetComponent?.remediation_effort || 8.0;
  const storyPoints = effortHours <= 4 ? 1 : effortHours <= 8 ? 2 : effortHours <= 16 ? 3 : effortHours <= 30 ? 5 : 8;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#161e10]/60 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-[#d4dece] overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 bg-gradient-to-r from-[#2d3f16] via-[#43562b] to-[#1e2a0f] text-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white/15 flex items-center justify-center border border-white/20">
              <Layers className="h-5 w-5 text-[#d3ebb2]" />
            </div>
            <div>
              <h3 className="text-base font-bold tracking-tight">
                {isBulk ? 'Export priorities to Jira' : 'Create a Jira ticket'}
              </h3>
              <p className="text-xs text-[#d3ebb2]">Creates tickets in your connected Jira</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-full text-white/70 hover:text-white hover:bg-white/10 transition cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {result ? (
            <div className="space-y-4 text-center py-4">
              <div className="w-12 h-12 bg-[#d3ebb2] text-[#2d3f16] rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-[#161e10]">
                  {result.status === 'error' ? 'Jira export failed'
                    : result.mode === 'sandbox_mock' ? 'Simulated — Jira not connected' : 'Jira issues created'}
                </h4>
                <p className="text-xs text-[#75786d] mt-1 font-mono">
                  {result.status === 'error' ? result.message
                    : result.mode === 'sandbox_mock' ? 'Connect Jira in Integrations to create real tickets.'
                    : result.issue_key ? `Ticket: ${result.issue_key}` : `${result.total_tickets_created} tickets created`}
                </p>
                {result.mode === 'live' && (result.issues || []).length > 0 && (
                  <div className="mt-2 flex flex-wrap justify-center gap-2">
                    {result.issues.slice(0, 10).map((iss) => (
                      <a key={iss.issue_key} href={iss.issue_url} target="_blank" rel="noreferrer"
                        className="inline-flex items-center gap-1 text-xs font-semibold text-[#43562b] hover:underline">
                        {iss.issue_key} <ExternalLink className="w-3 h-3" />
                      </a>
                    ))}
                  </div>
                )}
                {(result.errors || []).length > 0 && (
                  <p className="text-[11px] text-[#855300] mt-2">{result.errors.length} item(s) failed: {result.errors[0]}</p>
                )}
              </div>
              <div className="p-3 bg-[#f8faf6] rounded-2xl border border-[#d4dece] text-xs font-mono text-left space-y-1">
                <div className="flex justify-between">
                  <span className="text-[#75786d]">Mode:</span>
                  <span className="font-bold text-[#2d3f16]">{result.mode === 'live' ? 'Live' : result.mode === 'sandbox_mock' ? 'Simulated' : '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#75786d]">Project:</span>
                  <span className="font-bold text-[#161e10]">{result.project_key || projectKey || '—'}</span>
                </div>
              </div>
              <button
                onClick={handleClose}
                className="w-full py-2.5 bg-[#43562b] hover:bg-[#2d3f16] text-white font-bold rounded-2xl shadow-md transition"
              >
                Done
              </button>
            </div>
          ) : (
            <>
              {isBulk ? (
                <div className="p-4 bg-[#f8faf6] rounded-2xl border border-[#d4dece] space-y-2">
                  <span className="text-[11px] font-mono uppercase font-bold text-[#75786d] block">What will be exported</span>
                  <p className="text-xs text-[#161e10]">
                    <strong>{targetComponents.length} top-priority files</strong>, one ticket each.
                  </p>
                </div>
              ) : (
                <div className="p-4 bg-[#f8faf6] rounded-2xl border border-[#d4dece] space-y-2">
                  <span className="text-[11px] font-mono uppercase font-bold text-[#75786d] block">Target Component</span>
                  <p className="text-xs font-mono font-bold text-[#161e10] truncate">
                    {targetComponent?.component || targetComponent?.name || targetComponent?.file || 'Target File'}
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                    <div>
                      <span className="text-[#75786d] block text-[10px]">Estimated Effort:</span>
                      <span className="font-bold text-[#161e10]">{effortHours}h ({storyPoints} Story Points)</span>
                    </div>
                    <div>
                      <span className="text-[#75786d] block text-[10px]">Priority Score:</span>
                      <span className="font-bold text-[#43562b]">{targetComponent?.priority_score || 82} / 100</span>
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-[#45483e] font-semibold mb-1">Jira project</label>
                  {projects === null ? (
                    <p className="text-[#75786d]">Loading your Jira projects…</p>
                  ) : projectsError ? (
                    <p className="text-[#855300]">{projectsError}</p>
                  ) : projects.length === 0 ? (
                    <p className="text-[#855300]">Jira isn't connected, so this will only be simulated. Connect Jira on the Integrations page to create real tickets.</p>
                  ) : (
                    <select
                      value={projectKey}
                      onChange={(e) => setProjectKey(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#f8faf6] border border-[#c5c8ba] rounded-xl focus:ring-2 focus:ring-[#43562b]"
                    >
                      {projects.map((p) => <option key={p.id} value={p.key}>{p.name}</option>)}
                    </select>
                  )}
                </div>
                <div>
                  <label className="block text-[#45483e] font-semibold mb-1">Issue Type</label>
                  <select
                    value={issueType}
                    onChange={(e) => setIssueType(e.target.value)}
                    className="w-full px-3.5 py-2 bg-[#f8faf6] border border-[#c5c8ba] rounded-xl focus:ring-2 focus:ring-[#43562b]"
                  >
                    <option value="Task">Task</option>
                    <option value="Bug">Bug</option>
                    <option value="Story">Story</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 bg-[#edf1e8] hover:bg-[#dde5d7] text-[#2d3f16] font-bold rounded-xl transition text-xs"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleExport}
                  disabled={loading}
                  className="px-5 py-2 bg-[#43562b] hover:bg-[#2d3f16] text-white font-bold rounded-xl shadow-md transition flex items-center gap-1.5 text-xs cursor-pointer disabled:opacity-50"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>{loading ? 'Creating…' : isBulk ? `Create ${targetComponents.length} tickets` : 'Create ticket'}</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
