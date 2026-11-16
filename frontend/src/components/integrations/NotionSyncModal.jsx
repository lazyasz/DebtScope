import React, { useState } from 'react';
import { syncNotion, createNotionReport } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { FileText, Database, CheckCircle2, ExternalLink, X, Sparkles, BookOpen } from 'lucide-react';

export default function NotionSyncModal({ isOpen, onClose, items = [], components = [], summaryStats = {} }) {
  const targetComponents = items.length > 0 ? items : components;
  const { integrations, showNotification, notify } = useAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeTab, setActiveTab] = useState('database'); // 'database' | 'audit_report'

  const [databaseId, setDatabaseId] = useState(integrations?.notion?.database_id || 'notion_db_pei_backlog_2026');
  const [reportTitle, setReportTitle] = useState('Executive Technical Debt Audit — Q3 2026');

  if (!isOpen) return null;

  const notifyUser = (msg) => {
    if (showNotification) showNotification(msg);
    else if (notify) notify(msg);
  };

  const handleSyncDatabase = async () => {
    setLoading(true);
    try {
      const payload = {
        database_id: databaseId,
        components: (targetComponents.length > 0 ? targetComponents : [{ file: 'services/auth/token_provider.py', priority_score: 85 }]).map((c) => ({
          component_name: c.component || c.name || c.file || 'Component',
          priority_score: c.priority_score || c.priority || 75.0,
          remediation_effort_hours: c.remediation_effort_hours || c.remediation_effort || 8.0,
          defect_probability: c.defect_probability || 0.45,
          technical_risk: c.technical_risk || c.risk_score || 60.0,
          business_impact: c.business_impact || 70.0,
          roi_quadrant: c.roi_quadrant || 'Quick Wins',
        })),
      };
      const res = await syncNotion(payload);
      setResult(res);
      notifyUser(res.status === 'success'
        ? `📑 Synced ${res.synced_count} components to Notion${res.mode === 'sandbox_mock' ? ' (simulated)' : ''}`
        : `Notion sync failed for ${res.failed_count} of ${(res.items || []).length} components`);
    } catch (err) {
      setResult({ status: 'error', message: err?.message || 'Request failed' });
      notifyUser(`Notion sync failed: ${err?.message || 'request failed'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateReport = async () => {
    setLoading(true);
    try {
      const payload = {
        title: reportTitle,
        total_components: summaryStats.total_components || targetComponents.length || 85,
        avg_priority_score: summaryStats.avg_priority || 64.2,
        quick_wins_count: summaryStats.quick_wins || 24,
        critical_hotspots_count: summaryStats.hotspots || 12,
      };
      const res = await createNotionReport(payload);
      setResult(res);
      notifyUser(`📑 ${res.message || 'Report created'}`);
    } catch (err) {
      setResult({ status: 'error', message: err?.message || 'Request failed' });
      notifyUser(`Report failed: ${err?.message || 'request failed'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setResult(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#161e10]/60 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-lg bg-white rounded-3xl shadow-2xl border border-[#d4dece] overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 bg-gradient-to-r from-[#2d3f16] via-[#43562b] to-[#1e2a0f] text-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-white/15 flex items-center justify-center border border-white/20">
              <Database className="h-5 w-5 text-[#d3ebb2]" />
            </div>
            <div>
              <h3 className="text-base font-bold tracking-tight">Notion Knowledge Hub Sync</h3>
              <p className="text-xs text-[#d3ebb2]">Living Backlog Databases & Architecture Decision Records</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-full text-white/70 hover:text-white hover:bg-white/10 transition cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Tab Selection */}
        {!result && (
          <div className="flex border-b border-[#e5ebe0] bg-[#f8faf6] px-6 pt-2">
            <button
              onClick={() => setActiveTab('database')}
              className={`flex items-center gap-2 pb-2.5 px-3 text-xs font-semibold border-b-2 transition cursor-pointer ${
                activeTab === 'database'
                  ? 'border-[#43562b] text-[#2d3f16]'
                  : 'border-transparent text-[#75786d] hover:text-[#161e10]'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Sync Backlog Database</span>
            </button>
            <button
              onClick={() => setActiveTab('audit_report')}
              className={`flex items-center gap-2 pb-2.5 px-3 text-xs font-semibold border-b-2 transition cursor-pointer ${
                activeTab === 'audit_report'
                  ? 'border-[#43562b] text-[#2d3f16]'
                  : 'border-transparent text-[#75786d] hover:text-[#161e10]'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Publish Executive RFC</span>
            </button>
          </div>
        )}

        {/* Content */}
        <div className="p-6 space-y-4">
          {result ? (
            <div className="space-y-4 text-center py-4">
              <div className="w-12 h-12 bg-[#d3ebb2] text-[#2d3f16] rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <h4 className="text-base font-bold text-[#161e10]">
                  {result.status === 'error' || result.status === 'partial'
                    ? 'Notion Sync Failed'
                    : result.mode === 'sandbox_mock' ? 'Simulated — not sent to Notion' : 'Notion Sync Successful!'}
                </h4>
                <p className="text-xs text-[#75786d] mt-1 font-mono">
                  {result.message
                    || (result.failed_count ? `${result.synced_count} synced, ${result.failed_count} failed` : `${result.synced_count ?? 0} items synchronized`)}
                </p>
              </div>
              <div className="p-3 bg-[#f8faf6] rounded-2xl border border-[#d4dece] text-xs font-mono text-left space-y-1">
                <div className="flex justify-between">
                  <span className="text-[#75786d]">Status:</span>
                  <span className="font-bold text-[#2d3f16]">Active Sync</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#75786d]">Database:</span>
                  <span className="font-bold text-[#161e10] truncate max-w-[200px]">{databaseId}</span>
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
              {activeTab === 'database' ? (
                <div className="space-y-3 text-xs">
                  <div className="p-3 bg-[#f8faf6] rounded-2xl border border-[#d4dece]">
                    <span className="text-[10px] font-mono uppercase font-bold text-[#75786d] block mb-1">Scope</span>
                    <p className="text-xs text-[#161e10]">
                      Synchronizing <strong>{targetComponents.length || 18} prioritized debt modules</strong> into your team's Notion Roadmap.
                    </p>
                  </div>
                  <div>
                    <label className="block text-[#45483e] font-semibold mb-1">Target Notion Database ID</label>
                    <input
                      type="text"
                      value={databaseId}
                      onChange={(e) => setDatabaseId(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#f8faf6] border border-[#c5c8ba] rounded-xl font-mono focus:ring-2 focus:ring-[#43562b]"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-3 text-xs">
                  <div>
                    <label className="block text-[#45483e] font-semibold mb-1">RFC Document Title</label>
                    <input
                      type="text"
                      value={reportTitle}
                      onChange={(e) => setReportTitle(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#f8faf6] border border-[#c5c8ba] rounded-xl focus:ring-2 focus:ring-[#43562b]"
                    />
                  </div>
                  <div className="p-3 bg-[#eef7e0] rounded-2xl border border-[#d3ebb2] text-[11px] text-[#2d3f16]">
                    ✨ Includes automatic executive summary, 5-factor regression chart embedding, and ROI quadrant breakdown.
                  </div>
                </div>
              )}

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
                  onClick={activeTab === 'database' ? handleSyncDatabase : handleCreateReport}
                  disabled={loading}
                  className="px-5 py-2 bg-[#43562b] hover:bg-[#2d3f16] text-white font-bold rounded-xl shadow-md transition flex items-center gap-1.5 text-xs cursor-pointer disabled:opacity-50"
                >
                  <Database className="w-3.5 h-3.5 text-[#d3ebb2]" />
                  <span>{loading ? 'Publishing...' : activeTab === 'database' ? 'Sync to Notion' : 'Publish Report'}</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
