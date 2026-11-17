import React, { useState, useRef, useEffect } from 'react';
import { Menu, Search, Settings, ChevronDown, Network, Info } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { getPriorities } from '../../services/api';

const TITLES = {
  '/dashboard': 'Dashboard',
  '/integrations': 'Integrations',
  '/simulator': 'What-If Simulator',
  '/predictions': 'Risk Predictions',
  '/priorities': 'What to fix first',
  '/hotspots': 'Code Hotspots',
  '/data-quality': 'Data Quality',
  '/copilot': 'AI Copilot',
};

export default function Header({ onMenuClick }) {
  const { user, handleLogout, notification } = useAuth();
  const [query, setQuery] = useState('');
  const [files, setFiles] = useState(null); // loaded on first focus
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const loadFiles = () => {
    if (files !== null) return;
    getPriorities(null).then((d) => setFiles(Array.isArray(d) ? d : [])).catch(() => setFiles([]));
  };

  const q = query.trim().toLowerCase();
  const matches = q && files ? files.filter((f) => f.file_path.toLowerCase().includes(q)).slice(0, 8) : [];

  const openFile = (f) => {
    navigate(`/files/${f.file_id}`);
    setQuery('');
    setOpen(false);
  };

  const title = location.pathname.startsWith('/files/') ? 'File details' : TITLES[location.pathname] || 'DebtScope';

  return (
    <>
      <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 sm:px-6 bg-white/95 backdrop-blur-md border-b border-[#e2e4ea]">
        <div className="flex items-center gap-3">
          <button
            onClick={onMenuClick}
            className="lg:hidden p-1.5 rounded-lg text-[#525866] hover:bg-[#f3f4f8] transition cursor-pointer"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#130e24] flex items-center justify-center text-white">
              <Network className="w-3.5 h-3.5 text-[#b39ef2]" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-xs sm:text-sm text-[#0f1015] tracking-tight leading-none">DebtScope</span>
              <span className="text-[11px] text-[#525866] font-medium leading-tight hidden sm:block">{title}</span>
            </div>
          </div>
        </div>

        {/* File search */}
        <div className="relative flex-1 max-w-md mx-4 hidden md:block">
          <form
            onSubmit={(e) => { e.preventDefault(); if (matches[0]) openFile(matches[0]); }}
            className="flex items-center bg-[#f8f9fb] rounded-lg px-3.5 py-1.5 border border-[#e2e4ea] focus-within:border-[#7048e8] focus-within:bg-white transition"
          >
            <Search className="w-3.5 h-3.5 text-[#88909e] mr-2 shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onFocus={() => { loadFiles(); setOpen(true); }}
              onBlur={() => setTimeout(() => setOpen(false), 150)}
              onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
              placeholder="Search your files (⌘K)..."
              aria-label="Search files"
              className="bg-transparent border-none text-xs text-[#0f1015] placeholder-[#88909e] focus:outline-none w-full"
            />
          </form>
          {open && q && (
            <div className="absolute left-0 right-0 mt-1 bg-white rounded-xl shadow-lg border border-[#e2e4ea] py-1 z-50 text-xs">
              {files === null ? (
                <p className="px-3 py-2 text-[#88909e]">Loading files…</p>
              ) : matches.length === 0 ? (
                <p className="px-3 py-2 text-[#88909e]">
                  {files.length ? 'No file matches.' : 'No scanned files yet. Scan a repository first.'}
                </p>
              ) : (
                matches.map((f) => (
                  <button
                    key={f.file_id}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => openFile(f)}
                    className="w-full text-left px-3 py-1.5 font-mono truncate hover:bg-[#f8f9fb] cursor-pointer"
                  >
                    {f.file_path}
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {user && (
            <div className="relative">
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="flex items-center gap-2 bg-[#f8f9fb] py-1 pl-1 pr-2.5 rounded-lg border border-[#e2e4ea] hover:border-[#d0d4de] transition cursor-pointer"
                aria-label="Account menu"
              >
                <img
                  src={user.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name || 'User')}&background=130e24&color=ffffff`}
                  alt=""
                  className="w-6 h-6 rounded-md object-cover"
                />
                <span className="text-xs font-semibold text-[#0f1015] truncate max-w-[120px] hidden sm:block">{user.name}</span>
                <ChevronDown className={`w-3 h-3 text-[#525866] transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
              </button>

              {menuOpen && (
                <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-lg border border-[#e2e4ea] p-3 z-50 text-left">
                  <div className="pb-2 border-b border-[#e2e4ea]">
                    <p className="text-xs font-bold text-[#0f1015] truncate">{user.name}</p>
                    <p className="text-[11px] text-[#525866] truncate">{user.email}</p>
                  </div>
                  <button
                    onClick={() => { setMenuOpen(false); navigate('/integrations'); }}
                    className="w-full text-left mt-2 px-2.5 py-1.5 text-xs font-medium text-[#0f1015] hover:bg-[#f8f9fb] rounded-lg cursor-pointer"
                  >
                    Integrations
                  </button>
                  <button
                    onClick={() => { setMenuOpen(false); handleLogout(); }}
                    className="w-full text-left px-2.5 py-1.5 text-xs text-[#dc2626] hover:bg-[#fef2f2] font-semibold rounded-lg cursor-pointer"
                  >
                    Sign out
                  </button>
                  <p className="px-2.5 pt-1 text-[10px] text-[#88909e]">To use another Google account, sign out and sign in again.</p>
                </div>
              )}
            </div>
          )}

          <button
            onClick={() => navigate('/integrations')}
            className="p-1.5 rounded-lg text-[#525866] hover:bg-[#f3f4f8] transition cursor-pointer"
            title="Integrations"
            aria-label="Integrations"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </header>

      {notification && (
        <div role="status" className="fixed bottom-6 right-6 z-50 bg-[#130e24] text-white px-4 py-2.5 rounded-xl shadow-xl border border-[#261c47] flex items-center gap-2.5 animate-fade-in text-xs font-medium">
          <Info className="w-4 h-4 text-[#b39ef2]" />
          <span>{notification.msg}</span>
        </div>
      )}
    </>
  );
}
