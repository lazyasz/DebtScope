import React from 'react';
import CopilotShell from '../components/copilot/CopilotShell';

export default function Copilot() {
  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 py-6 space-y-6 max-w-[1720px] mx-auto animate-fade-in">
      <section className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-[#161e10] tracking-tight">Ask the AI about your code</h1>
        <p className="text-sm text-[#45483e]">
          Ask why a file is ranked high, what your hotspots are, or how to fix a file. Answers use your workspace's real scan data.
        </p>
      </section>
      <CopilotShell />
    </div>
  );
}
