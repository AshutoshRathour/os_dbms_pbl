/**
 * Cloud Resource & Job Scheduling System - Main Client Utilities
 */

const App = {
  // Format seconds to human readable
  formatDuration(seconds) {
    if (seconds === null || seconds === undefined) return '-';
    if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(0);
    return `${mins}m ${secs}s`;
  },

  // Format timestamp to localized date/time
  formatDate(isoString) {
    if (!isoString) return '-';
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + 
           ' ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  },

  // Generate status badge HTML
  renderStatusBadge(status) {
    const s = (status || 'queued').toLowerCase();
    return `<span class="badge-status badge-status-${s}">${s}</span>`;
  },

  // Priority badge
  renderPriorityBadge(priority) {
    let color = 'secondary';
    let label = 'Normal';
    if (priority <= 2) { color = 'danger'; label = 'Critical'; }
    else if (priority <= 4) { color = 'warning'; label = 'High'; }
    else if (priority <= 7) { color = 'info'; label = 'Normal'; }
    else { color = 'secondary'; label = 'Low'; }
    return `<span class="badge bg-${color} text-uppercase" style="font-size: 0.7rem; font-weight: 600;">P${priority} · ${label}</span>`;
  },

  // Show Toast notification
  toast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
      container.style.zIndex = '9999';
      document.body.appendChild(container);
    }

    const toastId = 'toast-' + Date.now();
    const bgMap = {
      success: 'bg-success',
      danger: 'bg-danger',
      error: 'bg-danger',
      warning: 'bg-warning text-dark',
      info: 'bg-primary'
    };
    const bgClass = bgMap[type] || 'bg-secondary';

    const toastEl = document.createElement('div');
    toastEl.id = toastId;
    toastEl.className = `toast align-items-center text-white ${bgClass} border-0 shadow-lg`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body py-2 px-3 fw-medium">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;

    container.appendChild(toastEl);
    const bsToast = new bootstrap.Toast(toastEl, { delay: 4000 });
    bsToast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
  },

  // Copy text to clipboard
  copyToClipboard(text, successMsg = 'Copied to clipboard!') {
    navigator.clipboard.writeText(text).then(() => {
      App.toast(successMsg, 'success');
    }).catch(err => {
      App.toast('Failed to copy', 'danger');
    });
  }
};
