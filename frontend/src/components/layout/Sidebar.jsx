import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Grid,
  Flame,
  Activity,
  Bot,
  Layers,
  GitBranch,
  ShieldCheck,
  Zap,
  Sliders,
  Network,
} from 'lucide-react';

// Grouped by the user's journey: see the state → decide what to fix → act → connect tools
const sections = [
  {
    title: 'Overview',
    items: [{ name: 'Dashboard', to: '/dashboard', icon: LayoutDashboard }],
  },
  {
    title: 'Analyze',
    items: [
      { name: 'Priorities', to: '/priorities', icon: Grid },
      { name: 'Hotspots', to: '/hotspots', icon: Flame },
      { name: 'Risk Predictions', to: '/predictions', icon: Activity },
    ],
  },
  {
    title: 'Act',
    items: [
      { name: 'AI Copilot', to: '/copilot', icon: Bot },
      { name: 'What-If Simulator', to: '/simulator', icon: Sliders },
    ],
  },
  {
    title: 'Workspace',
    items: [
      { name: 'Integrations', to: '/integrations', icon: Layers },
      { name: 'About the model', to: '/data-quality', icon: ShieldCheck },
    ],
  },
];

export default function Sidebar({ open, onClose, onOpenScanModal }) {
  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-[#0b0714]/40 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-white border-r border-[#e2e4ea] transition-transform duration-200 lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="flex items-center gap-3 h-18 px-5 border-b border-[#e2e4ea]">
          <div className="flex items-center justify-center h-9 w-9 rounded-xl bg-[#130e24] text-white border border-[#261c47]">
            <Network className="w-4 h-4 text-[#b39ef2]" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[#0f1015] tracking-tight">DebtScope</h1>
            <p className="text-[10px] text-[#5b42a5] font-semibold leading-tight">Find what to fix first</p>
          </div>
        </div>

        {/* Navigation Section */}
        <div className="flex-1 px-3 py-5 space-y-5 overflow-y-auto">
          {sections.map((section) => (
          <div key={section.title}>
            <span className="px-3 text-[10px] font-mono font-bold uppercase tracking-wider text-[#88909e]">
              {section.title}
            </span>
            <nav className="mt-2 space-y-1">
              {section.items.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-[#130e24] text-white shadow-xs'
                        : 'text-[#525866] hover:bg-[#f3f4f8] hover:text-[#0f1015]'
                    }`
                  }
                >
                  <div className="flex items-center gap-2.5">
                    <item.icon className="h-4 w-4 shrink-0" />
                    <span>{item.name}</span>
                  </div>
                </NavLink>
              ))}
            </nav>
          </div>
          ))}

          {/* Quick Repo Scan Trigger */}
          <div className="p-3.5 bg-[#f8f9fb] rounded-xl border border-[#e2e4ea] space-y-2">
            <div className="flex items-center gap-2 text-[#0f1015]">
              <GitBranch className="w-4 h-4 text-[#7048e8]" />
              <span className="text-xs font-bold">Scan a repository</span>
            </div>
            <p className="text-[11px] text-[#525866] leading-snug">
              Paste a public GitHub link to find risky files.
            </p>
            <button
              onClick={() => {
                if (onClose) onClose();
                if (onOpenScanModal) onOpenScanModal();
              }}
              className="w-full mt-1 py-1.5 px-3 bg-white hover:bg-[#f0ecfc] text-[#5b42a5] text-xs font-semibold rounded-lg transition flex items-center justify-center gap-1.5 border border-[#e2e4ea] cursor-pointer"
            >
              <Zap className="w-3.5 h-3.5 text-[#7048e8]" />
              <span>Scan repository</span>
            </button>
          </div>
        </div>

      </aside>
    </>
  );
}
