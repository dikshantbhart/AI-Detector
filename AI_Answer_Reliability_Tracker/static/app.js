/**
 * AI Answer Reliability Tracker — Advanced Web Client Logic
 * Theme: Minimal Cream & Orange Theme
 * Font: Figtree
 */

// Global State
let currentTab = 'dashboard';
let currentUser = null;
let claimsData = [];
let sourcesData = [];
let historyData = [];
let searchDebounceTimeout = null;
let activeInspectorClaimId = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  checkAuth();
  loadDashboardData();
  setupModalKeyboardHandlers();
});

// ---------- AUTHENTICATION ----------

async function checkAuth() {
  try {
    const res = await fetch('/api/me');
    const data = await res.json();
    if (data.authenticated && data.user) {
      currentUser = data.user;
      updateUserUI();
    } else {
      currentUser = { username: 'admin', role: 'admin' };
      updateUserUI();
    }
  } catch (err) {
    console.warn('Auth check error:', err);
    currentUser = { username: 'admin', role: 'admin' };
    updateUserUI();
  }
}

function updateUserUI() {
  const nameEl = document.getElementById('userNameDisplay');
  const roleEl = document.getElementById('userRoleDisplay');
  const authBtnText = document.getElementById('authBtnText');

  if (currentUser) {
    nameEl.textContent = `Signed in: ${currentUser.username}`;
    roleEl.textContent = currentUser.role || 'user';
    authBtnText.textContent = 'Logout';
  } else {
    nameEl.textContent = 'Guest Session';
    roleEl.textContent = 'visitor';
    authBtnText.textContent = 'Sign In';
  }
}

function handleAuthAction() {
  if (currentUser) {
    // Logout
    fetch('/api/logout', { method: 'POST' }).finally(() => {
      currentUser = null;
      updateUserUI();
      showToast('Logged out. Switched to guest mode.', 'success');
      openModal('modalAuth');
    });
  } else {
    openModal('modalAuth');
  }
}

function setDemoAuth(username, password) {
  document.getElementById('authUsername').value = username;
  document.getElementById('authPassword').value = password;
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const username = document.getElementById('authUsername').value.trim();
  const password = document.getElementById('authPassword').value.trim();

  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      currentUser = data.user;
      updateUserUI();
      closeModal('modalAuth');
      showToast(`Welcome back, ${currentUser.username}!`, 'success');
      loadDashboardData();
    } else {
      showToast(data.error || 'Login failed', 'error');
    }
  } catch (err) {
    showToast('Failed to connect to authentication server', 'error');
  }
}

// ---------- TAB NAVIGATION ----------

function switchTab(tabId) {
  currentTab = tabId;

  // Update tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  const activeBtn = document.getElementById(`tab-${tabId}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Update tab views
  document.querySelectorAll('.tab-view').forEach(view => {
    view.classList.remove('active');
  });
  const activeView = document.getElementById(`view-${tabId}`);
  if (activeView) activeView.classList.add('active');

  // Trigger data reload for specific tabs
  if (tabId === 'dashboard') loadDashboardData();
  else if (tabId === 'claims') loadClaimsData();
  else if (tabId === 'sources') loadSourcesData();
  else if (tabId === 'history') loadHistoryData();
}

// ---------- TOAST NOTIFICATIONS ----------

function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  let iconSvg = '';
  if (type === 'success') {
    iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--status-verified)" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
  } else if (type === 'error') {
    iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--status-disputed)" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
  } else {
    iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-deep-orange)" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
  }

  toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

// ---------- DASHBOARD TAB ----------

async function loadDashboardData() {
  try {
    const res = await fetch('/api/dashboard');
    const data = await res.json();

    // KPIs
    document.getElementById('kpiTotalClaims').textContent = data.total_claims;
    document.getElementById('kpiVerifiedClaims').textContent = data.status_counts.Verified || 0;
    document.getElementById('kpiUnverifiedClaims').textContent = data.status_counts.Unverified || 0;
    document.getElementById('kpiDisputedClaims').textContent = data.status_counts.Disputed || 0;
    document.getElementById('kpiAvgConfidence').textContent = `${data.avg_verified_confidence}%`;
    document.getElementById('kpiTotalSources').textContent = data.total_sources;
    document.getElementById('kpiAvgSourceCred').textContent = `Avg. cred: ${data.avg_source_credibility} / 5`;

    // Counts on tab pills
    document.getElementById('claimsCountPill').textContent = data.total_claims;
    document.getElementById('sourcesCountPill').textContent = data.total_sources;

    const total = data.total_claims || 1;
    const vPct = Math.round(((data.status_counts.Verified || 0) / total) * 100);
    document.getElementById('kpiVerifiedPct').textContent = `${vPct}% of all claims`;

    // Status bar chart
    renderStatusBarChart(data.status_counts, total);

    // Top categories
    renderTopCategories(data.top_categories);

    // Recent claims table
    renderDashboardRecent(data.recent_claims);

  } catch (err) {
    console.error('Failed to load dashboard:', err);
    showToast('Failed to fetch dashboard metrics', 'error');
  }
}

function renderStatusBarChart(counts, total) {
  const container = document.getElementById('statusBarContainer');
  container.innerHTML = '';

  const statuses = [
    { key: 'Verified', label: 'Verified', color: 'var(--status-verified)' },
    { key: 'Unverified', label: 'Unverified', color: 'var(--status-unverified)' },
    { key: 'Disputed', label: 'Disputed', color: 'var(--status-disputed)' },
    { key: 'Rejected', label: 'Rejected', color: 'var(--status-rejected)' }
  ];

  document.getElementById('legendVerifiedCount').textContent = counts.Verified || 0;
  document.getElementById('legendUnverifiedCount').textContent = counts.Unverified || 0;
  document.getElementById('legendDisputedCount').textContent = counts.Disputed || 0;
  document.getElementById('legendRejectedCount').textContent = counts.Rejected || 0;

  statuses.forEach(st => {
    const count = counts[st.key] || 0;
    const pct = total > 0 ? (count / total) * 100 : 0;
    if (pct > 0) {
      const seg = document.createElement('div');
      seg.className = 'status-bar-segment';
      seg.style.width = `${pct}%`;
      seg.style.backgroundColor = st.color;
      seg.title = `${st.label}: ${count} (${Math.round(pct)}%)`;
      if (pct > 7) {
        seg.textContent = `${Math.round(pct)}%`;
      }
      container.appendChild(seg);
    }
  });

  if (total === 0) {
    container.innerHTML = '<div style="display:flex; align-items:center; justify-content:center; width:100%; color:var(--color-muted-text); font-size:0.8rem;">No claims registered yet</div>';
  }
}

function renderTopCategories(cats) {
  const container = document.getElementById('topCategoriesContainer');
  container.innerHTML = '';

  if (!cats || cats.length === 0) {
    container.innerHTML = '<p class="text-muted" style="font-size:0.85rem;">No categories yet.</p>';
    return;
  }

  cats.forEach(c => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex; justify-content:space-between; align-items:center; padding:6px 10px; background-color:var(--color-warm-cream); border-radius:var(--radius-xs); font-size:0.85rem;';
    row.innerHTML = `
      <span style="font-weight:600; color:var(--color-dark-text);">${escapeHtml(c.category)}</span>
      <span class="badge badge-category">${c.cnt} claim${c.cnt > 1 ? 's' : ''}</span>
    `;
    container.appendChild(row);
  });
}

function renderDashboardRecent(claims) {
  const tbody = document.getElementById('dashboardRecentTableBody');
  tbody.innerHTML = '';

  if (!claims || claims.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state"><p class="text-muted">No claims added yet.</p></td></tr>`;
    return;
  }

  claims.forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>#${c.claim_id}</strong></td>
      <td>
        <span class="claim-cell-text" title="${escapeHtml(c.claim_text)}">${escapeHtml(c.claim_text)}</span>
      </td>
      <td><span class="badge badge-category">${escapeHtml(c.category)}</span></td>
      <td>${getStatusBadgeHtml(c.status)}</td>
      <td>
        <div class="confidence-wrapper">
          <div class="confidence-track">
            <div class="confidence-fill" style="width: ${c.confidence}%;"></div>
          </div>
          <span class="confidence-value">${c.confidence}%</span>
        </div>
      </td>
      <td style="text-align: right;">
        <button class="btn btn-secondary btn-sm" onclick="openClaimInspector(${c.claim_id})">Inspect</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ---------- CLAIMS EXPLORER TAB ----------

function handleSearchDebounce() {
  clearTimeout(searchDebounceTimeout);
  searchDebounceTimeout = setTimeout(() => {
    loadClaimsData();
  }, 250);
}

function resetClaimFilters() {
  document.getElementById('claimSearchInput').value = '';
  document.getElementById('claimStatusFilter').value = 'All';
  document.getElementById('claimCategoryFilter').value = 'All';
  loadClaimsData();
}

async function loadClaimsData() {
  const q = document.getElementById('claimSearchInput').value.trim();
  const status = document.getElementById('claimStatusFilter').value;
  const category = document.getElementById('claimCategoryFilter').value;

  const url = new URL('/api/claims', window.location.origin);
  if (q) url.searchParams.set('q', q);
  if (status && status !== 'All') url.searchParams.set('status', status);
  if (category && category !== 'All') url.searchParams.set('category', category);

  try {
    const res = await fetch(url);
    const data = await res.json();
    claimsData = data.claims || [];

    // Populate category filter if needed
    updateCategoryFilterDropdown(data.categories || []);

    // Render Table
    renderClaimsTable(claimsData);

    // Update count
    document.getElementById('claimsCountPill').textContent = data.count || 0;

  } catch (err) {
    console.error('Failed to load claims:', err);
    showToast('Failed to retrieve claims data', 'error');
  }
}

function updateCategoryFilterDropdown(categories) {
  const select = document.getElementById('claimCategoryFilter');
  const curVal = select.value;

  // Preserve 'All Categories'
  select.innerHTML = '<option value="All">All Categories</option>';
  categories.forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat;
    opt.textContent = cat;
    if (cat === curVal) opt.selected = true;
    select.appendChild(opt);
  });
}

function renderClaimsTable(claims) {
  const tbody = document.getElementById('claimsTableBody');
  tbody.innerHTML = '';

  if (!claims || claims.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8">
          <div class="empty-state">
            <div class="empty-icon">&#128269;</div>
            <div class="empty-title">No claims found</div>
            <div class="empty-text">No claims match your current search terms or filter criteria. Try resetting filters or adding a new claim statement.</div>
            <button class="btn btn-primary btn-sm" onclick="openAddClaimModal()" style="margin-top:8px;">Add New Claim</button>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  claims.forEach(c => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>#${c.claim_id}</strong></td>
      <td>
        <span class="claim-cell-text" title="${escapeHtml(c.claim_text)}">${escapeHtml(c.claim_text)}</span>
      </td>
      <td><span class="badge badge-category">${escapeHtml(c.category)}</span></td>
      <td>${getStatusBadgeHtml(c.status)}</td>
      <td>
        <div class="confidence-wrapper">
          <div class="confidence-track">
            <div class="confidence-fill" style="width: ${c.confidence}%;"></div>
          </div>
          <span class="confidence-value">${c.confidence}%</span>
        </div>
      </td>
      <td>
        <span class="badge badge-category" style="cursor:pointer;" onclick="openClaimInspector(${c.claim_id})" title="Click to view linked sources">
          &#128279; ${c.source_count || 0}
        </span>
      </td>
      <td style="font-size:0.8rem; color:var(--color-muted-text); white-space:nowrap;">
        ${formatDate(c.created_at)}
      </td>
      <td style="text-align: right;">
        <div class="table-actions-group">
          <button class="btn btn-secondary btn-icon btn-sm" onclick="openClaimInspector(${c.claim_id})" title="Inspect Claim & Sources">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
          </button>
          <button class="btn btn-secondary btn-icon btn-sm" onclick="openEditClaimModal(${c.claim_id})" title="Edit Claim">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
          </button>
          <button class="btn btn-secondary btn-icon btn-sm" onclick="openStatusModal(${c.claim_id}, '${escapeHtml(c.claim_text).replace(/'/g, "\\'")}', '${c.status}')" title="Change Verification Status">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
          </button>
          <button class="btn btn-danger btn-icon btn-sm" onclick="handleDeleteClaim(${c.claim_id})" title="Delete Claim">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ---------- CLAIM INSPECTOR & SOURCES LINKER ----------

async function openClaimInspector(claimId) {
  activeInspectorClaimId = claimId;
  const modal = document.getElementById('modalClaimInspector');
  const body = document.getElementById('inspectorBody');
  body.innerHTML = '<div style="text-align:center; padding:30px;"><p class="text-muted">Loading claim details and evidence citations...</p></div>';

  openModal('modalClaimInspector');

  try {
    const res = await fetch(`/api/claims/${claimId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to load details');

    const c = data.claim;
    const sources = data.sources || [];
    const history = data.history || [];

    document.getElementById('inspectorTitle').textContent = `Claim Audit Inspector #${c.claim_id}`;

    // Link button actions in inspector footer
    document.getElementById('inspectorStatusBtn').onclick = () => {
      openStatusModal(c.claim_id, c.claim_text, c.status);
    };
    document.getElementById('inspectorLinkBtn').onclick = () => {
      openLinkSourceModal(c.claim_id);
    };

    let sourcesHtml = '';
    if (sources.length === 0) {
      sourcesHtml = `
        <div style="background-color:var(--color-soft-white); border:1px dashed var(--color-border-strong); border-radius:var(--radius-sm); padding:16px; text-align:center;">
          <p class="text-muted" style="font-size:0.85rem; margin-bottom:8px;">No sources currently linked to this claim.</p>
          <button class="btn btn-soft btn-sm" onclick="openLinkSourceModal(${c.claim_id})">+ Link First Source Citation</button>
        </div>
      `;
    } else {
      sources.forEach(s => {
        sourcesHtml += `
          <div class="source-item-card">
            <div class="source-item-info">
              <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                <span class="source-item-title">${escapeHtml(s.source_name)}</span>
                <span class="credibility-stars">${getCredibilityStarsHtml(s.credibility)}</span>
              </div>
              <a href="${escapeHtml(s.source_url)}" target="_blank" rel="noopener noreferrer" class="source-item-url">
                ${escapeHtml(s.source_url)} &#8599;
              </a>
              ${s.relation_note ? `<p style="font-size:0.82rem; color:var(--color-muted-text); margin-top:2px;"><strong>Relation Note:</strong> ${escapeHtml(s.relation_note)}</p>` : ''}
              ${s.evidence ? `<p style="font-size:0.82rem; color:var(--color-dark-text); background:var(--color-warm-cream); padding:6px 10px; border-radius:4px; margin-top:4px;"><em>"${escapeHtml(s.evidence)}"</em></p>` : ''}
            </div>
            <button class="btn btn-secondary btn-sm" style="color:var(--status-disputed);" onclick="handleUnlinkSource(${c.claim_id}, ${s.source_id})" title="Unlink this source">
              Unlink
            </button>
          </div>
        `;
      });
    }

    let historyHtml = '';
    if (history.length === 0) {
      historyHtml = '<p class="text-muted" style="font-size:0.85rem;">No status transition history recorded yet.</p>';
    } else {
      historyHtml = '<div class="timeline">';
      history.forEach(h => {
        historyHtml += `
          <div class="timeline-event">
            <div class="timeline-dot"></div>
            <div class="timeline-title">
              Transitioned: <span style="font-weight:500;">${h.old_status || 'Initial'}</span> &rarr; <strong>${h.new_status}</strong>
            </div>
            <div class="timeline-time">${formatDate(h.changed_at)} by <strong>${escapeHtml(h.changed_by_name || 'System')}</strong></div>
            ${h.comment ? `<div class="timeline-comment">${escapeHtml(h.comment)}</div>` : ''}
          </div>
        `;
      });
      historyHtml += '</div>';
    }

    body.innerHTML = `
      <div class="inspector-section">
        <div class="inspector-section-title">Claim Statement</div>
        <p style="font-size:1.05rem; font-weight:700; color:var(--color-dark-text); line-height:1.45;">
          ${escapeHtml(c.claim_text)}
        </p>
        <div style="display:flex; align-items:center; gap:12px; margin-top:10px; flex-wrap:wrap;">
          <span class="badge badge-category">Category: ${escapeHtml(c.category)}</span>
          ${getStatusBadgeHtml(c.status)}
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-size:0.82rem; font-weight:600; color:var(--color-muted-text);">Confidence:</span>
            <div class="confidence-wrapper" style="max-width:90px;">
              <div class="confidence-track">
                <div class="confidence-fill" style="width: ${c.confidence}%;"></div>
              </div>
              <span class="confidence-value">${c.confidence}%</span>
            </div>
          </div>
        </div>
      </div>

      ${c.notes ? `
        <div class="inspector-section">
          <div class="inspector-section-title">Evaluation Notes</div>
          <p style="font-size:0.9rem; line-height:1.5;">${escapeHtml(c.notes)}</p>
        </div>
      ` : ''}

      <div class="inspector-section">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <div class="inspector-section-title" style="margin-bottom:0;">Linked Corroborating Sources (${sources.length})</div>
          <button class="btn btn-secondary btn-sm" onclick="openLinkSourceModal(${c.claim_id})">+ Link Another Source</button>
        </div>
        ${sourcesHtml}
      </div>

      <div class="inspector-section">
        <div class="inspector-section-title">Verification Audit Trail</div>
        ${historyHtml}
      </div>
    `;

  } catch (err) {
    body.innerHTML = `<div class="empty-state"><p class="text-muted">${err.message}</p></div>`;
  }
}

// ---------- CLAIM CRUD OPERATIONS ----------

function openAddClaimModal() {
  document.getElementById('claimFormTitle').textContent = 'Add New Claim';
  document.getElementById('formClaimId').value = '';
  document.getElementById('formClaimText').value = '';
  document.getElementById('formClaimCategory').value = 'General';
  document.getElementById('formClaimConfidence').value = '60';
  document.getElementById('formConfidenceOutput').textContent = '60%';
  document.getElementById('formClaimNotes').value = '';
  openModal('modalClaimForm');
}

async function openEditClaimModal(claimId) {
  try {
    const res = await fetch(`/api/claims/${claimId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);

    const c = data.claim;
    document.getElementById('claimFormTitle').textContent = `Edit Claim #${c.claim_id}`;
    document.getElementById('formClaimId').value = c.claim_id;
    document.getElementById('formClaimText').value = c.claim_text;
    document.getElementById('formClaimCategory').value = c.category;
    document.getElementById('formClaimConfidence').value = c.confidence;
    document.getElementById('formConfidenceOutput').textContent = `${c.confidence}%`;
    document.getElementById('formClaimNotes').value = c.notes || '';

    openModal('modalClaimForm');
  } catch (err) {
    showToast('Failed to load claim for editing', 'error');
  }
}

async function handleSaveClaim(event) {
  event.preventDefault();
  const id = document.getElementById('formClaimId').value;
  const isEdit = !!id;

  const claim_text = document.getElementById('formClaimText').value.trim();
  const category = document.getElementById('formClaimCategory').value.trim() || 'General';
  const confidence = parseInt(document.getElementById('formClaimConfidence').value, 10);
  const notes = document.getElementById('formClaimNotes').value.trim();

  const payload = { claim_text, category, confidence, notes };

  try {
    const url = isEdit ? `/api/claims/${id}` : '/api/claims';
    const method = isEdit ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok) {
      closeModal('modalClaimForm');
      showToast(isEdit ? 'Claim updated successfully' : 'New claim registered', 'success');
      loadClaimsData();
      loadDashboardData();
    } else {
      showToast(data.error || 'Failed to save claim', 'error');
    }
  } catch (err) {
    showToast('Network error while saving claim', 'error');
  }
}

async function handleDeleteClaim(claimId) {
  if (!confirm(`Are you sure you want to delete claim #${claimId}? All linked citations and audit history for this claim will be permanently removed.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/claims/${claimId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast(`Claim #${claimId} deleted successfully`, 'success');
      loadClaimsData();
      loadDashboardData();
      if (activeInspectorClaimId === claimId) {
        closeModal('modalClaimInspector');
      }
    } else {
      showToast(data.error || 'Failed to delete claim', 'error');
    }
  } catch (err) {
    showToast('Error deleting claim', 'error');
  }
}

// ---------- STATUS UPDATE MODAL ----------

function openStatusModal(claimId, excerpt, currentStatus) {
  document.getElementById('statusClaimId').value = claimId;
  document.getElementById('statusClaimExcerpt').textContent = excerpt;
  document.getElementById('statusSelect').value = currentStatus || 'Verified';
  document.getElementById('statusComment').value = '';
  openModal('modalStatusForm');
}

async function handleSaveStatus(event) {
  event.preventDefault();
  const claimId = document.getElementById('statusClaimId').value;
  const status = document.getElementById('statusSelect').value;
  const comment = document.getElementById('statusComment').value.trim();

  try {
    const res = await fetch(`/api/claims/${claimId}/status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, comment })
    });
    const data = await res.json();
    if (res.ok) {
      closeModal('modalStatusForm');
      showToast(`Status updated to '${status}' with audit trail entry`, 'success');
      loadClaimsData();
      loadDashboardData();
      loadHistoryData();
      if (activeInspectorClaimId === parseInt(claimId, 10)) {
        openClaimInspector(claimId);
      }
    } else {
      showToast(data.error || 'Failed to update status', 'error');
    }
  } catch (err) {
    showToast('Error updating status', 'error');
  }
}

// ---------- SOURCES REPOSITORY TAB ----------

async function loadSourcesData() {
  try {
    const res = await fetch('/api/sources');
    const data = await res.json();
    sourcesData = data.sources || [];
    renderSourcesTable(sourcesData);
    document.getElementById('sourcesCountPill').textContent = data.count || 0;
  } catch (err) {
    console.error('Failed to load sources:', err);
    showToast('Failed to fetch sources repository', 'error');
  }
}

function renderSourcesTable(sources) {
  const tbody = document.getElementById('sourcesTableBody');
  tbody.innerHTML = '';

  if (!sources || sources.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7">
          <div class="empty-state">
            <div class="empty-icon">&#127760;</div>
            <div class="empty-title">No sources recorded</div>
            <div class="empty-text">Catalog trustworthy peer-reviewed journals, science portals, or benchmark sources to support claim verification.</div>
            <button class="btn btn-primary btn-sm" onclick="openAddSourceModal()" style="margin-top:8px;">Add New Source</button>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  sources.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>#${s.source_id}</strong></td>
      <td>
        <strong style="color:var(--color-dark-text);">${escapeHtml(s.source_name)}</strong>
        ${s.evidence ? `<div style="font-size:0.8rem; color:var(--color-muted-text); margin-top:2px;">${escapeHtml(s.evidence)}</div>` : ''}
      </td>
      <td>
        <a href="${escapeHtml(s.source_url)}" target="_blank" rel="noopener noreferrer" style="font-size:0.85rem;">
          ${escapeHtml(s.source_url)} &#8599;
        </a>
      </td>
      <td>
        <div class="credibility-stars" title="Credibility rating: ${s.credibility}/5">
          ${getCredibilityStarsHtml(s.credibility)}
        </div>
      </td>
      <td>
        <span class="badge badge-category">&#128279; ${s.linked_claims_count || 0} claims</span>
      </td>
      <td style="font-size:0.8rem; color:var(--color-muted-text); white-space:nowrap;">
        ${formatDate(s.added_at)}
      </td>
      <td style="text-align: right;">
        <div class="table-actions-group">
          <button class="btn btn-secondary btn-icon btn-sm" onclick="openEditSourceModal(${s.source_id})" title="Edit Source">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>
          </button>
          <button class="btn btn-danger btn-icon btn-sm" onclick="handleDeleteSource(${s.source_id})" title="Delete Source">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
          </button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function openAddSourceModal() {
  document.getElementById('sourceFormTitle').textContent = 'Add Verification Source';
  document.getElementById('formSourceId').value = '';
  document.getElementById('formSourceName').value = '';
  document.getElementById('formSourceUrl').value = '';
  document.getElementById('formSourceCredibility').value = '4';
  document.getElementById('formCredibilityOutput').textContent = '4 / 5';
  document.getElementById('formSourceEvidence').value = '';
  openModal('modalSourceForm');
}

function openEditSourceModal(sourceId) {
  const s = sourcesData.find(item => item.source_id === sourceId);
  if (!s) return;

  document.getElementById('sourceFormTitle').textContent = `Edit Source #${s.source_id}`;
  document.getElementById('formSourceId').value = s.source_id;
  document.getElementById('formSourceName').value = s.source_name;
  document.getElementById('formSourceUrl').value = s.source_url;
  document.getElementById('formSourceCredibility').value = s.credibility;
  document.getElementById('formCredibilityOutput').textContent = `${s.credibility} / 5`;
  document.getElementById('formSourceEvidence').value = s.evidence || '';
  openModal('modalSourceForm');
}

async function handleSaveSource(event) {
  event.preventDefault();
  const id = document.getElementById('formSourceId').value;
  const isEdit = !!id;

  const source_name = document.getElementById('formSourceName').value.trim();
  const source_url = document.getElementById('formSourceUrl').value.trim();
  const credibility = parseInt(document.getElementById('formSourceCredibility').value, 10);
  const evidence = document.getElementById('formSourceEvidence').value.trim();

  const payload = { source_name, source_url, credibility, evidence };

  try {
    const url = isEdit ? `/api/sources/${id}` : '/api/sources';
    const method = isEdit ? 'PUT' : 'POST';

    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok) {
      closeModal('modalSourceForm');
      showToast(isEdit ? 'Source updated' : 'Source cataloged', 'success');
      loadSourcesData();
      loadDashboardData();
    } else {
      showToast(data.error || 'Failed to save source', 'error');
    }
  } catch (err) {
    showToast('Error saving source', 'error');
  }
}

async function handleDeleteSource(sourceId) {
  if (!confirm(`Are you sure you want to delete source #${sourceId}? Any links to claims will also be removed.`)) {
    return;
  }

  try {
    const res = await fetch(`/api/sources/${sourceId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast(`Source #${sourceId} deleted`, 'success');
      loadSourcesData();
      loadDashboardData();
      if (activeInspectorClaimId) {
        openClaimInspector(activeInspectorClaimId);
      }
    } else {
      showToast(data.error || 'Failed to delete source', 'error');
    }
  } catch (err) {
    showToast('Error deleting source', 'error');
  }
}

// ---------- LINK / UNLINK SOURCE TO CLAIM ----------

async function openLinkSourceModal(claimId) {
  document.getElementById('linkClaimId').value = claimId;
  const select = document.getElementById('linkSourceSelect');
  select.innerHTML = '<option value="">Loading sources catalog...</option>';

  openModal('modalLinkSource');

  try {
    const res = await fetch('/api/sources');
    const data = await res.json();
    const sources = data.sources || [];

    select.innerHTML = '';
    if (sources.length === 0) {
      select.innerHTML = '<option value="">No sources available. Please add a source first.</option>';
      return;
    }

    sources.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.source_id;
      opt.textContent = `${s.source_name} (Credibility: ${s.credibility}/5)`;
      select.appendChild(opt);
    });
  } catch (err) {
    select.innerHTML = '<option value="">Error loading sources</option>';
  }
}

async function handleSaveSourceLink(event) {
  event.preventDefault();
  const claimId = document.getElementById('linkClaimId').value;
  const sourceId = document.getElementById('linkSourceSelect').value;
  const relationNote = document.getElementById('linkRelationNote').value.trim();

  if (!sourceId) {
    showToast('Please select a source to link', 'error');
    return;
  }

  try {
    const res = await fetch(`/api/claims/${claimId}/sources`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_id: sourceId, relation_note: relationNote })
    });
    const data = await res.json();

    if (res.ok) {
      closeModal('modalLinkSource');
      showToast('Source linked to claim successfully', 'success');
      loadClaimsData();
      loadDashboardData();
      if (activeInspectorClaimId === parseInt(claimId, 10)) {
        openClaimInspector(claimId);
      }
    } else {
      showToast(data.error || 'Failed to link source', 'error');
    }
  } catch (err) {
    showToast('Network error while linking source', 'error');
  }
}

async function handleUnlinkSource(claimId, sourceId) {
  if (!confirm('Remove this source link from the claim?')) return;

  try {
    const res = await fetch(`/api/claims/${claimId}/sources/${sourceId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast('Source unlinked from claim', 'success');
      loadClaimsData();
      loadDashboardData();
      openClaimInspector(claimId);
    } else {
      showToast(data.error || 'Failed to unlink source', 'error');
    }
  } catch (err) {
    showToast('Error unlinking source', 'error');
  }
}

// ---------- VERIFICATION HISTORY TAB ----------

async function loadHistoryData() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    historyData = data.history || [];
    renderHistoryTable(historyData);
  } catch (err) {
    console.error('Failed to load history:', err);
    showToast('Failed to fetch audit history', 'error');
  }
}

function renderHistoryTable(items) {
  const tbody = document.getElementById('historyTableBody');
  tbody.innerHTML = '';

  if (!items || items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state"><p class="text-muted">No status transitions logged yet.</p></td></tr>`;
    return;
  }

  items.forEach(h => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>#${h.history_id}</strong></td>
      <td>
        <span class="claim-cell-text" title="${escapeHtml(h.claim_text)}">
          <strong>#${h.claim_id}:</strong> ${escapeHtml(h.claim_text)}
        </span>
      </td>
      <td>
        <div style="display:flex; align-items:center; gap:6px;">
          ${h.old_status ? getStatusBadgeHtml(h.old_status) : '<span class="text-muted">Initial</span>'}
          <span>&rarr;</span>
          ${getStatusBadgeHtml(h.new_status)}
        </div>
      </td>
      <td>
        <span style="font-size:0.88rem; color:var(--color-dark-text);">${escapeHtml(h.comment || '—')}</span>
      </td>
      <td>
        <span class="badge badge-category">${escapeHtml(h.changed_by_name || 'System')}</span>
      </td>
      <td style="font-size:0.8rem; color:var(--color-muted-text); white-space:nowrap;">
        ${formatDate(h.changed_at)}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// ---------- CSV EXPORT ----------

function exportClaimsCSV() {
  showToast('Generating CSV report download...', 'info');
  window.location.href = '/api/export/csv';
}

// ---------- MODAL HELPERS & KEYBOARD HANDLERS ----------

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('open');
    const firstInput = modal.querySelector('input:not([type="hidden"]), textarea, select');
    if (firstInput) setTimeout(() => firstInput.focus(), 50);
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
  }
}

function setupModalKeyboardHandlers() {
  // Close modal when pressing ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop.open').forEach(modal => {
        modal.classList.remove('open');
      });
    }
  });

  // Close modal when clicking on backdrop
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) {
        backdrop.classList.remove('open');
      }
    });
  });
}

// ---------- HTML FORMATTING UTILITIES ----------

function getStatusBadgeHtml(status) {
  const s = String(status || 'Unverified').toLowerCase();
  let badgeClass = 'badge-unverified';
  let dotColor = 'var(--status-unverified)';

  if (s === 'verified') {
    badgeClass = 'badge-verified';
    dotColor = 'var(--status-verified)';
  } else if (s === 'disputed') {
    badgeClass = 'badge-disputed';
    dotColor = 'var(--status-disputed)';
  } else if (s === 'rejected') {
    badgeClass = 'badge-rejected';
    dotColor = 'var(--status-rejected)';
  }

  return `
    <span class="badge ${badgeClass}">
      <span style="width:6px; height:6px; border-radius:50%; background-color:${dotColor};"></span>
      ${escapeHtml(status || 'Unverified')}
    </span>
  `;
}

function getCredibilityStarsHtml(rating) {
  const score = Math.max(1, Math.min(5, parseInt(rating, 10) || 1));
  let stars = '';
  for (let i = 1; i <= 5; i++) {
    if (i <= score) {
      stars += '&#9733;'; // filled star
    } else {
      stars += '<span class="star-empty">&#9734;</span>'; // empty star
    }
  }
  return `${stars} <span style="font-size:0.75rem; color:var(--color-muted-text); margin-left:4px;">(${score}/5)</span>`;
}

function formatDate(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  } catch {
    return isoString;
  }
}

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
