import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// After a deploy, an open tab asks for page files that no longer exist (blank page).
// Reload once to pick up the new version; the flag stops a reload loop if the server is really down.
window.addEventListener('vite:preloadError', (event) => {
  if (sessionStorage.getItem('reloaded_after_deploy')) return;
  sessionStorage.setItem('reloaded_after_deploy', '1');
  event.preventDefault();
  window.location.reload();
});
window.addEventListener('load', () => setTimeout(() => sessionStorage.removeItem('reloaded_after_deploy'), 10000));

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
