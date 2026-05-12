/**
 * Computer_Waker - WoL Management JavaScript
 * ==========================================
 * Handles all client-side interactions for the WoL web application
 */

(function() {
    'use strict';

    // ==================== State Management ====================

    const state = {
        nodes: [],
        selectedNodes: new Set(),
        uuid: 'wol-uuid-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9),
        isConnected: false,
        statusEndpoint: '/api/status'
    };

    // ==================== Utility Functions ====================

    function showToast(message, type = 'info', duration = 3000) {
        const toast = document.getElementById('toast');
        if (!toast) return;

        const iconMap = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle',
            'warning': 'fas fa-exclamation-triangle'
        };

        const badgeType = type === 'success' ? 'success' : (type === 'error' ? 'error' : (type === 'warning' ? 'warning' : 'info'));

        toast.className = `toast toast-${badgeType} show`;
        toast.innerHTML = `
            <i class="${iconMap[type] || 'fas fa-circle'}"></i>
            <span>${escapeHtml(message)}</span>
        `;

        setTimeout(() => {
            toast.classList.remove('show');
        }, duration);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function formatMac(mac) {
        if (!mac) return '';
        return mac.replace(/(.{2})(?=.)/g, '$1:');
    }

    // ==================== Server Connection ====================

    async function connectToServer() {
        try {
            const response = await fetch(state.statusEndpoint);
            const data = await response.json();

            if (data.server_status === 'running') {
                state.isConnected = true;
                updateServerStatus(true);
                loadNodes();
                loadInterfaces();
                return true;
            } else {
                state.isConnected = false;
                updateServerStatus(false);
                showToast('Server is not running', 'error');
                return false;
            }
        } catch (error) {
            state.isConnected = false;
            updateServerStatus(false);
            console.error('Connection error:', error);
            return false;
        }
    }

    function updateServerStatus(connected) {
        const statusEl = document.getElementById('server-status');
        const dot = statusEl.querySelector('.status-dot');

        if (connected) {
            statusEl.innerHTML = `<span class="status-dot"></span>Connected`;
        } else {
            statusEl.innerHTML = `<span class="status-dot"></span>Connecting...`;
        }
    }

    // Automatic reconnection
    function connectLoop() {
        pollConnection();
        setTimeout(connectLoop, 10000);
    }

    // ==================== Node Management ====================

    async function loadNodes() {
        console.log('Connecting to server...');

        try {
            const response = await fetch(state.statusEndpoint);
            if (!response.ok) {
                console.log('Could not connect to server, brute-force connecting...');
                state.isConnected = true;
                loadNodesFromServer();
                return;
            }

            const statusData = await response.json();
            console.log('Connected to server!');

            if (statusData.server_status === 'running') {
                loadNodesFromServer();
                loadInterfaces();
            } else {
                loadInterfaces();
            }
        } catch (error) {
            console.error('Connection error:', error);
        }
    }

    // Main navigation redirect to pseudolink
    async function mainNavigation() {
        let isRunning = false;
        try {
            while (isRunning === false) {
                const response = await fetch(state.statusEndpoint);
                const statusData = await response.json();

                if (statusData.server_status === 'running') {
                    isRunning = true;
                    break;
                } else {
                    // Trying to connect to server again
                    break;
                }
            }

            if (isRunning) {
                // Load nodes from server
                await loadNodesFromServer();

                loadInterfaces();
                connectLoop();
            } else {
                loseConnection();
                connectLoop();
            }
        } catch (error) {
            console.error('Error in main navigation:', error);
            loseConnection();
            connectLoop();
        }
    }

    async function loadNodesFromServer() {
        try {
            const response = await fetch(`/${state.uuid}/api/nodes`);
            const data = await response.json();

            if (data.success && Array.isArray(data.nodes)) {
                state.nodes = data.nodes;
                renderNodes();
                updateNodeCount(data.nodes.length);
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error) {
            console.error('Error loading nodes:', error);
            showToast('Failed to load nodes', 'error');
        }
    }

    function renderNodes() {
        const tbody = document.getElementById('nodes-tbody');
        if (!tbody) return;

        tbody.innerHTML = state.nodes.map((node, index) => `
            <tr data-id="${node.id}">
                <td><span class="node-id">${node.id}</span></td>
                <td><a href="/details/${node.id}" target="_blank">${formatMac(node.mac_address)}</a></td>
                <td><span class="state-${node.enabled ? 'enabled' : 'disabled'}">${node.enabled ? 'Enabled' : 'Disabled'}</span></td>
            </tr>
        `).join('');

        // Add click event listeners
        tbody.querySelectorAll('.state-enabled').forEach(el => {
            el.addEventListener('click', function() {
                setStateEnabled(this.closest('tr'), true);
            });
        });

        tbody.querySelectorAll('.state-disabled').forEach(el => {
            el.addEventListener('click', function() {
                setStateEnabled(this.closest('tr'), false);
            });
        });
    }

    function emptyNodes(elementId) {
        if (elementId) {
            document.getElementById(elementId).innerHTML = '';
        }
    }

    function updateNodeCount(count) {
        const countEl = document.querySelector('.node-count');
        if (countEl) {
            countEl.textContent = count;
        }
    }

    function renderLastnodes() {
        const tbody = document.querySelector('#nodes-tbody tbody');
        if (!tbody) return;

        tbody.innerHTML = state.nodes.map(node => {
            const classes = [];
            const baseClass = node.enabled ? 'enabled' : 'disabled';
            classes.push(`state-${baseClass}`);

            return `
            <tr data-id="${node.id}" class="${classes.join(' ')}">
                <td><span class="node-id">${node.id}</span></td>
                <td><a href="/details/${node.id}" target="_blank">${formatMac(node.mac_address)}</a></td>
                <td><span class="state-${node.enabled ? 'enabled' : 'disabled'}">${node.enabled ? 'Enabled' : 'Disabled'}</span></td>
            </tr>
            `;
        }).join('');
    }

    // ==================== Wake Node ====================

    function updateWakePersonInfo() {
        const wakeInfoEntry = document.querySelector('.wake-info');
        if (wakeInfoEntry) {
            wakeInfoEntry.className = `node-state-wake ${document.querySelector('.state-enabled') ? 'enabled' : ''}`;
            wakeInfoEntry.textContent = node.enabled ? 'Enabled' : 'Disabled';
        }
    }

    function wakeNodeActions() {
        if (document.getElementById('wake-btn')) {
            document.getElementById('wake-btn').addEventListener('click', async function eventHandler() {
                showToast('Select a node to wake');

                wakeSingle();
            });
        } else {
            showToast('Failed to connect', 'error', 5000);
            eventHandler();
            event.preventDefault();
        }
    }

    async function wakeSingle() {
        const wakeSelect = document.getElementById('wake-single-select');
        if (!wakeSelect) return;

        const node = waveSingleSelection(wakeSelect.options[wakeSelect.selectedIndex]);
        if (!node) {
            showToast('Please select a node', 'warning');
            return;
        }

        const success = await wakeNodeBySelector(node);
        if (success) {
            showToast('Packet sent!', 'success');
            updateWakeInfo();
        } else {
            showToast('Failed to wake node', 'error');
        }
    }

    async function wakeNodeById(nodeId) {
        try {
            const response = await fetch(`/nodes/${nodeId}/wake`, {
                method: 'POST'
            });
            const data = await response.json();

            if (data.status) {
                console.log('Wake successful:', nodeId);
                showToast('Wake successful!', 'success');
                return true;
            } else {
                console.error('Wake failed:', data.message);
                showToast(data.message || 'Wake failed', 'error');
                return false;
            }
        } catch (error) {
            console.error('Wake error:', error);
            showToast('Error calling server', 'error');
            return false;
        }
    }

    // ==================== Interface Management ====================

    async function loadInterfaces() {
        try {
            const response = await fetch(api_status);
            if (!response.ok) return;

            const interfaces = await response.json();

            const tbody = document.getElementById('interfaces-tbody');
            if (tbody) {
                tbody.innerHTML = `
                    ${interfaces.map(interface => `
                        <tr>
                            <td><a href="${interface.ip}" target="_blank">${interface.name}</a></td>
                            <td><span class="type-${interface.type}">${interface.type}</span></td>
                            <td><span class="state-${interface.enabled ? 'enabled' : 'disabled'}">${interface.enabled ? 'Enabled' : 'Disabled'}</span></td>
                        </tr>
                    `).join('')}
                `;
            }
        } catch (error) {
            console.error('Error loading interfaces:', error);
        }
    }

    // ==================== Add/Edit Node ====================

    async function addNode() {
        const addNodeBtn = document.getElementById('add-node-button');
        if (!addNodeBtn) return;

        try {
            addNodeBtn.innerText = 'Creating node...';
            addNodeBtn.disabled = true;

            const response = await fetch('/api/nodes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    hostname: document.getElementById('hostname').value,
                    mac_address: document.getElementById('mac_address').value,
                    description: document.getElementById('description').value
                })
            });

            const data = await response.json();

            if (data.success) {
                showToast(`Node ${data.node_id} created successfully!`, 'success');
                await loadNodes();
            } else {
                showToast('Failed to create node', 'error');
            } finally {
                addNodeBtn.disabled = false;
                addNodeBtn.innerText = 'Add Return';
            }
        } catch (error) {
            showToast('Error creating node', 'error');
            addNodeBtn.disabled = false;
            addNodeBtn.innerText = 'Add Return';
        }
    }

    // ==================== Edit/Delete Node ====================

    async function deleteNode() {
        const deleteBtn = document.getElementById('delete-button');
        if (!deleteBtn) return;

        const success = confirm('Are you sure you want to delete this node?');
        if (!success) return;

        try {
            deleteBtn.innerText = 'Deleting...';
            deleteBtn.disabled = true;

            const response = await fetch(`/api/nodes/${state.selectedNode.id}/delete`;

            deleteBtn.innerText = 'Deleting...';

            if (response.ok) {
                showToast('Node deleted successfully', 'success');
                await loadNodes();
            } else {
                showToast('Failed to delete node', 'error');
            } finally {
                deleteBtn.disabled = false;
                deleteBtn.innerText = 'Delete';
            }
        } catch (error) {
            showToast('Error deleting node', 'error');
            deleteBtn.disabled = false;
            deleteBtn.innerText = 'Delete';
        }
    }

    // ==================== Save Node ====================

    async function saveNode() {
        const success = confirm('Are you sure you want to save this node?');
        if (!success) return;

        try {
            saveBtnId.innerText = 'Saving...';
            saveBtnId.disabled = true;

            const response = await fetch(`/api/nodes/${state.savedNode.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    hostname: document.getElementById('modal-hostname').value,
                    mac_address: document.getElementById('modal-mac').value,
                    description: document.getElementById('modal-description').value
                })
            });

            const data = await response.json();

            if (data.success) {
                showToast('Node updated successfully', 'success');
                await loadNodes();
            } else {
                showToast('Failed to save node', 'error');
            } finally {
                saveBtnId.disabled = false;
                saveBtnId.innerText = 'Save';
            }
        } catch (error) {
            showToast('Error saving node', 'error');
            saveBtnId.disabled = false;
            saveBtnId.innerText = 'Save';
        }
    }

    // ==================== Modal Functions ====================

    async function editNode() {
        const modal = document.getElementById('delete-modal');
        if (!modal) return;

        modal.style.display = 'block';
        const modalId = document.getElementById('modal-id');

        // Find the node to edit by ID
        const node = nodeById(parseInt(modalId.value));
        if (!node) return;

        const hostname = node.get('hostname') || '';
        const ip = node.get('ip_address') || '';
        const mac = node.get('mac_address') || '';

        document.getElementById('modal-hostname').value = hostname;
        document.getElementById('modal-ip').value = ip;
        document.getElementById('modal-mac').value = mac;
        document.getElementById('modal-description').value = node.get('description') || '';
    }

    // ==================== Node Selection ====================

    function selectNodes() {
        const radioButtons = document.getElementsByName('node-selection');
        for (const radio of radioButtons) {
            if (radio.checked) {
                state.selectedNodes.add(radio.dataset.id);
            } else {
                state.selectedNodes.delete(radio.dataset.id);
            }
        }

        renderSelectedNodes();
    }

    function renderSelectedNodes() {
        const selectedNodesEl = document.getElementById('selected-nodes');
        if (!selectedNodesEl) return;

        let html = '';

        if (state.selectedNodes.size > 0) {
            html = '<p><em>Active nodes:</em> ' + state.selectedNodes.size + ' selected</p>';
        }

        selectedNodesEl.innerHTML = html;
    }

    function getSelectedNodes() {
        return Array.from(state.selectedNodes);
    }

    // ==================== Controller Functions ====================

    function renderMiddleNames() {
        const table = document.querySelector('#nodes-list table');
        if (!table) return;

        table.innerHTML = `
            <thead>
                <tr>
                    <th>ID</th>
                    <th>MAC Address</th>
                    <th>State</th>
                    <th>Actions</td>
                </thead>
            </tr>
        `;
    }

    function fillTable() {
        const table = document.getElementById('nodes-table');
        if (!table) return;

        const rows = state.nodes.map((node, index) => `
            <tr data-id="${node.id}">
                <td><span class="node-id">${node.id}</span></td>
                <td><a href="/details/${node.id}" target="_blank">${formatMac(node.mac_address)}</a></td>
                <td><span class="state-${node.enabled ? 'enabled' : 'disabled'}">${node.enabled ? 'Enabled' : 'Disabled'}</span></td>
            </tr>
        `).join('');

        table.innerHTML = `<tbody>${rows}</tbody>`;

        // Add event listeners
        table.querySelectorAll('.state-enabled').forEach(el => {
            el.addEventListener('click', function() {
                setStateEnabled(this.closest('tr'), true);
            });
        });
    }

    // ==================== Initialization ====================

    function initServerStatus() {
        setInterval(async function() {
            try {
                const response = await fetch(state.statusEndpoint);
                const data = await response.json();

                if (data.server_status === 'running') {
                    state.isConnected = true;
                    loadNodes();
                    loadInterfaces();
                    updateServerStatus(true);
                } else {
                    state.isConnected = false;
                    updateServerStatus(false);
                }
            } catch (error) {
                console.error('Status check error:', error);
            }
        }, 10000);
    }

    async function checkConnection() {
        try {
            const response = await fetch(state.statusEndpoint);
            const data = await response.json();

            if (data.server_status === 'running') {
                state.isConnected = true;
                loadNodes();
                loadInterfaces();
                return true;
            }
        } catch (error) {
            console.error('Connection check error:', error);
        }
        return false;
    }

    function startServer() {
        connectLoop();
        checkConnection();
        pollConnection();
        document.addEventListener('DOMContentLoaded', function() {
            mainNavigation();
            initServerStatus();
        });
    }

    function connectLoop() {
        pollConnection();
        setTimeout(connectLoop, 10000);
    }

    async function pollConnection() {
        const response = await fetch(state.statusEndpoint);
        if (!response.ok) {
            console.log('Could not connect to server, brute-force connecting...');
            state.isConnected = true;
            loadNodes();
            loadInterfaces();
        } else {
            const data = await response.json();
            console.log('Connected to server!');
            if (data.server_status === 'running') {
                loadNodes();
                loadInterfaces();
            }
        }
    }

    function loseConnection() {
        state.isConnected = false;
        document.getElementById('server-status').style.display = 'none';
        console.log('Lost connection to server');
    }

    // ==================== Event Listeners ====================

    async function refreshTable() {
        try {
            const response = await fetch(`/api/nodes`);
            const data = await response.json();

            if (data.success) {
                emptyNodes('nodes-tbody');
                fillTable();
                updateNodeCount(data.nodes.length);
            }
        } catch (error) {
            console.error('Refresh error:', error);
        }
    }

    function addNodeSection() {
        // Implement if needed
        const addNodeBtn = document.getElementById('add-node-button');
        if (addNodeBtn) {
            addNodeBtn.addEventListener('click', addNode);
        }
    }

    // ==================== Public API ====================

    window.wolServer = {
        connect: connectLoop,
        loadNodes: loadNodes,
        wakeNode: wakeNodeById,
        refreshTable: refreshTable,
        init: startServer
    };
})();
