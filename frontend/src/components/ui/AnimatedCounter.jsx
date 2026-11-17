import React from 'react';

// Shows the value immediately: a count-up animation showed 0 in background tabs and screenshots
export default function AnimatedCounter({ value = 0, decimals = 0, prefix = '', suffix = '', className = '' }) {
  const n = typeof value === 'number' ? value : parseFloat(value) || 0;
  return <span className={`font-mono tabular-nums ${className}`}>{`${prefix}${n.toFixed(decimals)}${suffix}`}</span>;
}
