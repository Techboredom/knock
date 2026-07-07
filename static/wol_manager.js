/**
 * Computer_Waker - WoL Management JavaScript
 */

(function () {
  'use strict';

  // ===== API endpoints =====

  const API = {
    status: '/api/status',
    nodes: '/api/nodes',
    interfaces: '/api/interfaces',
    nodeById: (id) => `/api/nodes/${id}`,
    wakeNode: (id) => `/api/nodes/${id}/wake`,
  };

  // ===== App state =====

  const state = {
    nodes: [],
    isConnected: false,
  };

  // ===== Utilities =====

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = String(text == null ? '' : text);
    return d.innerHTML;
  }

  function formatDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString();
    } catch (_) {
      return iso;
    }
  }

  function showToast(message, type, duration) {
    type = type || 'info';
    duration = duration || 3000;
    const toast = document.getElementById('toast');
    if (!toast) return;
    const icons = {
      success: 'fas fa-check-circle',
      error: 'fas fa-exclamation-circle',
      warning: 'fas fa-exclamation-triangle',
      info: 'fas fa-info-circle',
    };
    toast.className = 'toast ' + type + ' show';
    toast.innerHTML =
      '<i class="' + (icons[type] || icons.info) + '"></i> ' +
      '<span>' + escapeHtml(message) + '</span>';
    setTimeout(function () {
      toast.classList.remove('show');
    }, duration);
  }

  // ===== Fetch wrapper =====

  async function apiFetch(url, options) {
    const resp = await fetch(url, options || {});
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.error || 'HTTP ' + resp.status);
    }
    return data;
  }

  // ===== Server status =====

  function updateStatusBadge(connected) {
    const el = document.getElementById('server-status');
    if (!el) return;
    if (connected) {
      el.innerHTML = '<span class="status-dot online"></span> Connected';
    } else {
      el.innerHTML = '<span class="status-dot offline"></span> Disconnected';
    }
  }

  async function checkStatus() {
    try {
      const data = await apiFetch(API.status);
      state.isConnected = data.server_status === 'running';
    } catch (_) {
      state.isConnected = false;
    }
    updateStatusBadge(state.isConnected);
  }

  // ===== Load & render nodes =====

  async function loadNodes() {
    try {
      const data = await apiFetch(API.nodes);
      state.nodes = Array.isArray(data) ? data : [];
      renderNodesTable();
      updateWakeSelect();
    } catch (err) {
      showToast('Failed to load nodes: ' + err.message, 'error');
    }
  }

  function renderNodesTable() {
    const tbody = document.getElementById('nodes-tbody');
    if (!tbody) return;

    const countEl = document.querySelector('.node-count');
    if (countEl) countEl.textContent = state.nodes.length;

    if (state.nodes.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="empty-message">No nodes configured. Add one above.</td></tr>';
      return;
    }

    tbody.innerHTML = state.nodes.map(function (node) {
      const enabledBadge = node.enabled
        ? '<span class="badge badge-success">Enabled</span>'
        : '<span class="badge badge-secondary">Disabled</span>';
      const wakeDisabled = node.enabled ? '' : ' disabled';
      return (
        '<tr data-id="' + node.id + '">' +
        '<td>' + escapeHtml(node.mac_address) + '</td>' +
        '<td>' + escapeHtml(node.hostname || '—') + '</td>' +
        '<td>' + escapeHtml(node.ip_address || '—') + '</td>' +
        '<td>' + enabledBadge + '</td>' +
        '<td>' + escapeHtml(formatDate(node.last_wol)) + '</td>' +
        '<td class="actions">' +
          '<button class="btn btn-sm btn-success wake-btn"' +
            ' data-id="' + node.id + '"' + wakeDisabled + '>' +
            '<i class="fas fa-power-off"></i> Wake' +
          '</button> ' +
          '<button class="btn btn-sm btn-secondary edit-btn"' +
            ' data-id="' + node.id + '">' +
            '<i class="fas fa-edit"></i>' +
          '</button> ' +
          '<button class="btn btn-sm btn-danger delete-btn"' +
            ' data-id="' + node.id + '"' +
            ' data-mac="' + escapeHtml(node.mac_address) + '">' +
            '<i class="fas fa-trash"></i>' +
          '</button>' +
        '</td>' +
        '</tr>'
      );
    }).join('');

    tbody.querySelectorAll('.wake-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        wakeNode(parseInt(btn.dataset.id, 10));
      });
    });
    tbody.querySelectorAll('.edit-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openEditModal(parseInt(btn.dataset.id, 10));
      });
    });
    tbody.querySelectorAll('.delete-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        openDeleteModal(parseInt(btn.dataset.id, 10), btn.dataset.mac);
      });
    });
  }

  function updateWakeSelect() {
    const sel = document.getElementById('wake-select');
    if (!sel) return;
    const enabled = state.nodes.filter(function (n) { return n.enabled; });
    sel.innerHTML =
      '<option value="">-- Select a node to wake --</option>' +
      enabled.map(function (n) {
        return '<option value="' + n.id + '">' +
          escapeHtml(n.hostname || n.mac_address) +
          '</option>';
      }).join('');
  }

  // ===== Wake =====

  async function wakeNode(nodeId) {
    const node = state.nodes.find(function (n) { return n.id === nodeId; });
    const label = node ? (node.hostname || node.mac_address) : nodeId;
    try {
      const data = await apiFetch(API.wakeNode(nodeId), { method: 'POST' });
      showToast(
        (data.success ? 'Wake packet sent to ' : 'Wake failed for ') + label,
        data.success ? 'success' : 'warning'
      );
      if (data.success) await loadNodes();
    } catch (err) {
      showToast('Wake error: ' + err.message, 'error');
    }
  }

  // ===== Add node form =====

  async function handleAddNode(evt) {
    evt.preventDefault();
    const form = evt.target;
    const submitBtn = form.querySelector('[type=submit]');

    const payload = {
      mac_address: form.mac_address.value.trim(),
      hostname: form.hostname.value.trim(),
      ip_address: form.ip.value.trim(),
      description: form.description.value.trim(),
      enabled: form.enabled.checked,
    };

    submitBtn.disabled = true;
    submitBtn.textContent = 'Adding...';

    try {
      await apiFetch(API.nodes, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      showToast('Node added successfully', 'success');
      form.reset();
      await loadNodes();
    } catch (err) {
      showToast('Failed to add node: ' + err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-plus"></i> Add Node';
    }
  }

  // ===== Delete node =====

  let pendingDeleteId = null;

  function openDeleteModal(nodeId, mac) {
    pendingDeleteId = nodeId;
    const display = document.getElementById('delete-mac-display');
    if (display) display.textContent = mac;
    document.getElementById('delete-modal').style.display = 'block';
  }

  async function confirmDelete(evt) {
    evt.preventDefault();
    if (pendingDeleteId === null) return;
    const id = pendingDeleteId;
    pendingDeleteId = null;
    try {
      await apiFetch(API.nodeById(id), { method: 'DELETE' });
      showToast('Node deleted', 'success');
      document.getElementById('delete-modal').style.display = 'none';
      await loadNodes();
    } catch (err) {
      showToast('Delete failed: ' + err.message, 'error');
    }
  }

  // ===== Edit node =====

  let editingNodeId = null;

  function openEditModal(nodeId) {
    const node = state.nodes.find(function (n) { return n.id === nodeId; });
    if (!node) return;
    editingNodeId = nodeId;

    document.getElementById('modal-mac').value = node.mac_address || '';
    document.getElementById('modal-hostname').value = node.hostname || '';
    document.getElementById('modal-ip').value = node.ip_address || '';
    document.getElementById('modal-description').value = node.description || '';
    document.getElementById('modal-enabled').checked = !!node.enabled;

    const title = document.getElementById('modal-title');
    if (title) title.textContent = 'Edit Node — ' + (node.hostname || node.mac_address);

    document.getElementById('node-modal').style.display = 'block';
  }

  async function handleSaveNode(evt) {
    evt.preventDefault();
    if (editingNodeId === null) return;
    const id = editingNodeId;
    const submitBtn = evt.target.querySelector('[type=submit]');

    const payload = {
      mac_address: document.getElementById('modal-mac').value.trim(),
      hostname: document.getElementById('modal-hostname').value.trim(),
      ip_address: document.getElementById('modal-ip').value.trim(),
      description: document.getElementById('modal-description').value.trim(),
      enabled: document.getElementById('modal-enabled').checked,
    };

    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';

    try {
      await apiFetch(API.nodeById(id), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      showToast('Node updated', 'success');
      document.getElementById('node-modal').style.display = 'none';
      editingNodeId = null;
      await loadNodes();
    } catch (err) {
      showToast('Save failed: ' + err.message, 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-save"></i> Save';
    }
  }

  // ===== Interfaces =====

  async function loadInterfaces() {
    const tbody = document.getElementById('interfaces-tbody');
    if (!tbody) return;
    try {
      const data = await apiFetch(API.interfaces);
      if (!Array.isArray(data) || data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="empty-message">No interfaces found</td></tr>';
        return;
      }
      tbody.innerHTML = data.map(function (iface) {
        const stateBadge = iface.state === 'UP'
          ? '<span class="badge badge-success">UP</span>'
          : '<span class="badge badge-secondary">' + escapeHtml(iface.state) + '</span>';
        return (
          '<tr>' +
          '<td>' + escapeHtml(iface.name) + '</td>' +
          '<td>' + escapeHtml(iface.ip || '—') + '</td>' +
          '<td>' + stateBadge + '</td>' +
          '</tr>'
        );
      }).join('');
    } catch (err) {
      tbody.innerHTML = '<tr><td colspan="3" class="empty-message">Failed to load interfaces</td></tr>';
      console.error('Interfaces error:', err);
    }
  }

  // ===== Modal helpers =====

  function initModals() {
    document.querySelectorAll('.modal .close').forEach(function (btn) {
      btn.addEventListener('click', function () {
        btn.closest('.modal').style.display = 'none';
      });
    });
    document.querySelectorAll('.modal').forEach(function (modal) {
      modal.addEventListener('click', function (e) {
        if (e.target === modal) modal.style.display = 'none';
      });
    });
  }

  // ===== Initialization =====

  async function init() {
    initModals();

    const addForm = document.getElementById('add-node-form');
    if (addForm) addForm.addEventListener('submit', handleAddNode);

    const editForm = document.getElementById('node-details-form');
    if (editForm) editForm.addEventListener('submit', handleSaveNode);

    const deleteForm = document.getElementById('delete-form');
    if (deleteForm) deleteForm.addEventListener('submit', confirmDelete);

    const wakeBtn = document.getElementById('wake-btn');
    if (wakeBtn) {
      wakeBtn.addEventListener('click', function () {
        const sel = document.getElementById('wake-select');
        const val = sel && sel.value ? parseInt(sel.value, 10) : null;
        if (!val) { showToast('Please select a node first', 'warning'); return; }
        wakeNode(val);
      });
    }

    const refreshNodesBtn = document.getElementById('refresh-nodes-btn');
    if (refreshNodesBtn) refreshNodesBtn.addEventListener('click', loadNodes);

    document.querySelectorAll('.refresh-interfaces').forEach(function (btn) {
      btn.addEventListener('click', loadInterfaces);
    });

    await checkStatus();
    await loadNodes();
    await loadInterfaces();

    // Poll server status every 30 s
    setInterval(checkStatus, 30000);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
