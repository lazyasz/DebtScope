import React from 'react';
import { Link } from 'react-router-dom';

// Public pages Google requires before the OAuth app can be published.
const CONTACT = 'dhruvsakhare2006@gmail.com';
const UPDATED = '16 November 2026';

function LegalPage({ title, children }) {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-300 px-4 py-12">
      <article className="max-w-2xl mx-auto space-y-5 text-sm leading-relaxed">
        <Link to="/login" className="text-emerald-400 text-xs hover:underline">← DebtScope</Link>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        <p className="text-xs text-gray-500">Last updated {UPDATED}</p>
        {children}
        <p>Questions: <a className="text-emerald-400 hover:underline" href={`mailto:${CONTACT}`}>{CONTACT}</a></p>
      </article>
    </div>
  );
}

const H = ({ children }) => <h2 className="text-base font-semibold text-white pt-2">{children}</h2>;

export function Privacy() {
  return (
    <LegalPage title="Privacy Policy">
      <p>DebtScope is an academic project (PBL 2026) that analyses software repositories to prioritise technical debt.</p>
      <H>What we collect</H>
      <p>When you sign in with Google we receive your name, email address and profile picture. We use them only to identify you and your workspace. We do not request access to your Gmail, Drive or any other Google data.</p>
      <p>When you scan a repository, we store metrics derived from its code and history (file sizes, complexity, change counts). If you connect GitHub, Jira or Notion, we store the access tokens encrypted and use them only to read or write the items you choose.</p>
      <H>How it is stored</H>
      <p>Data is kept in a database hosted on Render. It is not sold, shared with advertisers, or used to train AI models. When you use the AI Copilot, the question and relevant code metrics are sent to Google Gemini to generate the answer.</p>
      <H>Your choices</H>
      <p>You can sign out at any time. To have your account and workspace data deleted, email us and we will remove it.</p>
    </LegalPage>
  );
}

export function Terms() {
  return (
    <LegalPage title="Terms of Service">
      <p>DebtScope is provided as an academic project for evaluation and learning, free of charge.</p>
      <H>Use</H>
      <p>Only scan repositories you are allowed to access. Do not use the service to attack, overload or misuse other systems.</p>
      <H>No warranty</H>
      <p>The service and its predictions are provided "as is", without warranty of any kind. Risk scores are estimates; review them before acting on them. We are not liable for decisions made using the service.</p>
      <H>Changes</H>
      <p>The service may change or stop at any time. Continued use after a change means you accept the updated terms.</p>
    </LegalPage>
  );
}
