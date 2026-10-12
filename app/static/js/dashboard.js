/**
 * Cloud Resource & Job Scheduling System - Dashboard Real-time Poller & Charts
 */

let statusChart = null;
let nodeChart = null;
let pollTimer = null;

document.addEventListener('DOMContentLoaded', () => {
  initDashboard();

  // Polling selector event
  const pollSelect = document.getElementById('poll-interval-select');
  if (pollSelect) {
    pollSelect.addEventListener('change', (e) => {
      resetPolling(parseInt(e.target.value, 10));
    });
  }

  // Manual refresh button
  const refreshBtn = document.getElementById('btn-manual-refresh');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      fetchDashboardData();
      App.toast('Dashboard refreshed', 'info');
    });
  }
});

function initDashboard() {
  fetchDashboardData();
  resetPolling(5000);
}

function resetPolling(intervalMs) {
  if (pollTimer) clearInterval(pollTimer);
  const indicator = document.getElementById('live-indicator');

  if (intervalMs > 0) {
    pollTimer = setInterval(fetchDashboardData, intervalMs);
    if (indicator) {
      indicator.className = 'badge bg-success-subtle text-success border border-success border-opacity-25 rounded-pill px-2 py-1 small';
      indicator.innerHTML = '<i class="bi bi-broadcast me-1"></i> Live Polling';
    }
  } else {
    if (indicator) {
      indicator.className = 'badge bg-secondary-subtle text-secondary border border-secondary border-opacity-25 rounded-pill px-2 py-1 small';
      indicator.innerHTML = '<i class="bi bi-pause-circle me-1"></i> Polling Paused';
    }
  }
}

async function fetchDashboardData() {
  try {
    const res = await fetch('/api/dashboard');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderDashboard(data);
  } catch (err) {
    console.error('Error fetching dashboard metrics:', err);
  }
}

function renderDashboard(data) {
  const { job_stats, node_stats, recent_jobs, resource_usage } = data;

  // 1. KPI Stats
  if (job_stats) {
    document.getElementById('stat-total').textContent = job_stats.total || 0;
    document.getElementById('stat-queued').textContent = job_stats.queued || 0;
    document.getElementById('stat-running').textContent = (job_stats.running || 0) + (job_stats.assigned || 0);
    document.getElementById('stat-completed').textContent = job_stats.completed || 0;
    document.getElementById('stat-failed').textContent = job_stats.failed || 0;

    document.getElementById('stat-avg-duration').textContent = `${job_stats.avg_duration || 0}s`;
    document.getElementById('stat-avg-memory').textContent = `${job_stats.avg_memory_mb || 0} MB`;
  }

  // 2. Resource Pool Gauges
  if (node_stats) {
    const totalCpu = node_stats.total_cpu || 0;
    const allocCpu = node_stats.allocated_cpu || 0;
    const availCpu = Math.max(0, totalCpu - allocCpu);
    const cpuPct = totalCpu > 0 ? Math.round((allocCpu / totalCpu) * 100) : 0;

    document.getElementById('cpu-allocated-text').textContent = `${allocCpu} / ${totalCpu}`;
    document.getElementById('cpu-avail-text').textContent = availCpu;
    document.getElementById('cpu-total-text').textContent = totalCpu;
    document.getElementById('cpu-util-badge').textContent = `${cpuPct}%`;
    document.getElementById('cpu-progress-bar').style.width = `${cpuPct}%`;

    const totalMem = node_stats.total_memory || 0;
    const allocMem = node_stats.allocated_memory || 0;
    const availMem = Math.max(0, totalMem - allocMem);
    const memPct = totalMem > 0 ? Math.round((allocMem / totalMem) * 100) : 0;

    document.getElementById('mem-allocated-text').textContent = `${allocMem} / ${totalMem} MB`;
    document.getElementById('mem-avail-text').textContent = availMem;
    document.getElementById('mem-total-text').textContent = totalMem;
    document.getElementById('mem-util-badge').textContent = `${memPct}%`;
    document.getElementById('mem-progress-bar').style.width = `${memPct}%`;

    renderNodesGrid(node_stats.nodes || []);
  }

  // 3. Render Charts
  renderCharts(job_stats, resource_usage);

  // 4. Render Recent Jobs Table
  renderRecentJobsTable(recent_jobs || []);
}

function renderNodesGrid(nodes) {
  const container = document.getElementById('nodes-grid-container');
  if (!container) return;

  if (nodes.length === 0) {
    container.innerHTML = '<div class="col-12 text-center text-muted py-3">No computing nodes registered.</div>';
    return;
  }

  container.innerHTML = nodes.map(node => {
    const statusColor = node.status === 'active' ? 'success' : (node.status === 'maintenance' ? 'warning' : 'danger');
    return `
      <div class="col-md-4">
        <div class="p-3 rounded bg-dark border border-secondary border-opacity-25 h-100">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <div class="d-flex align-items-center gap-2">
              <span class="rounded-circle bg-${statusColor} d-inline-block" style="width: 8px; height: 8px;"></span>
              <strong class="text-light">${node.name}</strong>
            </div>
            <span class="badge bg-${statusColor}-subtle text-${statusColor} text-uppercase small">${node.status}</span>
          </div>
          
          <div class="mb-2">
            <div class="d-flex justify-content-between text-secondary" style="font-size: 0.75rem;">
              <span>CPU: ${node.allocated_cpu_cores} / ${node.total_cpu_cores} Cores</span>
              <span>${node.cpu_utilization}%</span>
            </div>
            <div class="progress-dark mt-1" style="height: 5px;">
              <div class="progress-bar-indigo h-100" style="width: ${node.cpu_utilization}%;"></div>
            </div>
          </div>

          <div>
            <div class="d-flex justify-content-between text-secondary" style="font-size: 0.75rem;">
              <span>RAM: ${node.allocated_memory_mb} / ${node.total_memory_mb} MB</span>
              <span>${node.memory_utilization}%</span>
            </div>
            <div class="progress-dark mt-1" style="height: 5px;">
              <div class="progress-bar-cyan h-100" style="width: ${node.memory_utilization}%;"></div>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderCharts(jobStats, resourceUsage) {
  // 1. Job Status Doughnut Chart
  const statusCtx = document.getElementById('jobStatusChart');
  if (statusCtx && jobStats) {
    const labels = ['Queued', 'Assigned', 'Running', 'Completed', 'Failed'];
    const counts = [
      jobStats.queued || 0,
      jobStats.assigned || 0,
      jobStats.running || 0,
      jobStats.completed || 0,
      jobStats.failed || 0
    ];
    const colors = ['#f59e0b', '#3b82f6', '#06b6d4', '#10b981', '#ef4444'];

    if (!statusChart) {
      statusChart = new Chart(statusCtx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: counts,
            backgroundColor: colors,
            borderWidth: 0,
            hoverOffset: 4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: { color: '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 11 } }
            }
          },
          cutout: '68%'
        }
      });
    } else {
      statusChart.data.datasets[0].data = counts;
      statusChart.update('none');
    }
  }

  // 2. Node Utilization Bar Chart
  const nodeCtx = document.getElementById('nodeUtilChart');
  if (nodeCtx && resourceUsage && resourceUsage.length > 0) {
    const nodeNames = resourceUsage.map(n => n.name);
    const cpuPcts = resourceUsage.map(n => n.cpu_pct);
    const memPcts = resourceUsage.map(n => n.mem_pct);

    if (!nodeChart) {
      nodeChart = new Chart(nodeCtx, {
        type: 'bar',
        data: {
          labels: nodeNames,
          datasets: [
            {
              label: 'CPU Util %',
              data: cpuPcts,
              backgroundColor: '#6366f1',
              borderRadius: 4
            },
            {
              label: 'Memory Util %',
              data: memPcts,
              backgroundColor: '#06b6d4',
              borderRadius: 4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              grid: { color: 'rgba(255, 255, 255, 0.05)' },
              ticks: { color: '#64748b', callback: v => `${v}%` }
            },
            x: {
              grid: { display: false },
              ticks: { color: '#94a3b8' }
            }
          },
          plugins: {
            legend: {
              labels: { color: '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 11 } }
            }
          }
        }
      });
    } else {
      nodeChart.data.labels = nodeNames;
      nodeChart.data.datasets[0].data = cpuPcts;
      nodeChart.data.datasets[1].data = memPcts;
      nodeChart.update('none');
    }
  }
}

function renderRecentJobsTable(jobs) {
  const tbody = document.getElementById('recent-jobs-tbody');
  if (!tbody) return;

  if (jobs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="text-center py-4 text-muted">
          No workloads submitted yet. Click <strong>Submit Workload</strong> to execute your first container job.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = jobs.map(job => {
    const assignment = job.assignment;
    const nodeName = assignment ? (assignment.node_name || 'Assigned') : '-';
    
    // Duration: Est vs Measured Actual
    const estTime = `${job.est_time_seconds || '-'}s (Est)`;
    const actTime = assignment && assignment.actual_duration_seconds !== null && assignment.actual_duration_seconds !== undefined
      ? `<strong class="text-info">${assignment.actual_duration_seconds.toFixed(1)}s</strong> (Act)`
      : '<span class="text-muted">-</span>';

    // Exit code
    let exitBadge = '<span class="text-muted">-</span>';
    if (assignment && assignment.exit_code !== null && assignment.exit_code !== undefined) {
      if (assignment.exit_code === 0) {
        exitBadge = '<span class="badge bg-success-subtle text-success">Exit 0</span>';
      } else {
        exitBadge = `<span class="badge bg-danger-subtle text-danger">Exit ${assignment.exit_code}</span>`;
      }
    }

    return `
      <tr>
        <td class="font-monospace fw-semibold text-light">#${job.id}</td>
        <td>
          <div class="fw-semibold text-light">${job.workload_name || 'Generic'}</div>
          <div class="text-muted small" style="font-size: 0.75rem;">${job.username || 'user'}</div>
        </td>
        <td>${App.renderPriorityBadge(job.priority)}</td>
        <td>${App.renderStatusBadge(job.status)}</td>
        <td><span class="badge bg-dark border border-secondary border-opacity-25 text-light">${nodeName}</span></td>
        <td>
          <div class="small">${actTime}</div>
          <div class="text-muted" style="font-size: 0.7rem;">${estTime}</div>
        </td>
        <td>${exitBadge}</td>
        <td class="text-secondary small">${App.formatDate(job.created_at)}</td>
        <td class="text-end">
          <a href="/jobs/${job.id}" class="btn btn-sm btn-outline-custom py-1 px-2" title="View Execution Logs">
            <i class="bi bi-terminal text-info me-1"></i> Logs
          </a>
        </td>
      </tr>
    `;
  }).join('');
}
