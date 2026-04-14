// Montex - Server Monitoring Application JavaScript

// State
let currentView = 'dashboard';
let servers = [];
let settings = {};
let currentFilter = 'all';
let searchQuery = '';
let currentDetailServerId = null;
let metricsChart = null;

// DOM Elements
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const viewTitle = document.getElementById('viewTitle');
const lastUpdated = document.getElementById('lastUpdated');
const serversGrid = document.getElementById('serversGrid');
const serversTableBody = document.getElementById('serversTableBody');
const serverModal = document.getElementById('serverModal');
const serverDetailModal = document.getElementById('serverDetailModal');
const serverForm = document.getElementById('serverForm');
const toastContainer = document.getElementById('toastContainer');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupEventListeners();
    startAutoRefresh();
});

// Event Listeners
function setupEventListeners() {
    // Sidebar toggle
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });
    
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            switchView(view);
        });
    });
    
    // Add server button
    document.getElementById('addServerBtn').addEventListener('click', () => {
        openServerModal();
    });
    
    // Refresh button
    document.getElementById('refreshBtn').addEventListener('click', () => {
        loadData();
    });
    
    // Modal close
    document.getElementById('closeModal').addEventListener('click', () => {
        closeServerModal();
    });
    
    serverModal.addEventListener('click', (e) => {
        if (e.target === serverModal) {
            closeServerModal();
        }
    });
    
    // Server detail modal
    document.getElementById('closeDetailModal').addEventListener('click', () => {
        closeServerDetailModal();
    });
    
    serverDetailModal.addEventListener('click', (e) => {
        if (e.target === serverDetailModal) {
            closeServerDetailModal();
        }
    });
    
    // Chart tabs
    document.querySelectorAll('.chart-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            loadServerDetailChart(currentDetailServerId, parseInt(tab.dataset.range));
        });
    });
    
    // Server form
    serverForm.addEventListener('submit', (e) => {
        e.preventDefault();
        saveServer();
    });
    
    // Auth type toggle
    document.querySelectorAll('input[name="authType"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            toggleAuthFields(e.target.value);
        });
    });
    
    // Test connection
    document.getElementById('testConnectionBtn').addEventListener('click', () => {
        testConnection();
    });
    
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderServers();
        });
    });
    
    // Search
    document.getElementById('searchInput').addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase();
        renderServers();
    });
    
    // Threshold sliders
    document.getElementById('cpuThreshold').addEventListener('input', (e) => {
        document.getElementById('cpuThresholdValue').textContent = e.target.value;
    });
    
    document.getElementById('memoryThreshold').addEventListener('input', (e) => {
        document.getElementById('memoryThresholdValue').textContent = e.target.value;
    });
    
    document.getElementById('storageThreshold').addEventListener('input', (e) => {
        document.getElementById('storageThresholdValue').textContent = e.target.value;
    });
    
    // Save settings
    document.getElementById('saveSettingsBtn').addEventListener('click', () => {
        saveSettings();

    // Change password
    document.getElementById('changePasswordBtn').addEventListener('click', () => {
        changePassword();
    });
    });
    
    // Test Telegram
    document.getElementById('testTelegramBtn').addEventListener('click', () => {
        testTelegram();
    });
}

// Data Loading
async function loadData() {
    try {
        await Promise.all([
            loadServers(),
            loadSettings()
        ]);
        updateLastUpdated();
    } catch (error) {
        showToast('Failed to load data', 'error');
    }
}

async function loadServers() {
    const response = await fetch('/api/servers');
    servers = await response.json();
    renderServers();
    updateStats();
}

async function loadSettings() {
    const response = await fetch('/api/settings');
    settings = await response.json();
    applySettings();
}

function updateLastUpdated() {
    const now = new Date();
    lastUpdated.textContent = `Last updated: ${now.toLocaleTimeString()}`;
}

// View Management
function switchView(view) {
    currentView = view;
    
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === view);
    });
    
    // Update view title
    const titles = {
        dashboard: 'Dashboard',
        servers: 'Servers',
        settings: 'Settings'
    };
    viewTitle.textContent = titles[view] || 'Dashboard';
    
    // Show/hide views
    document.querySelectorAll('.view-content').forEach(v => {
        v.classList.add('hidden');
    });
    document.getElementById(`${view}View`).classList.remove('hidden');
    
    // Close sidebar on mobile
    if (window.innerWidth <= 1024) {
        sidebar.classList.remove('open');
    }
}

// Server Rendering
function renderServers() {
    const filtered = filterServers(servers);
    
    if (currentView === 'dashboard') {
        renderServerCards(filtered);
    } else {
        renderServerTable(filtered);
    }
}

function filterServers(list) {
    return list.filter(server => {
        // Filter by status
        let statusMatch = true;
        if (currentFilter !== 'all') {
            statusMatch = getServerStatus(server) === currentFilter;
        }
        
        // Filter by search
        let searchMatch = true;
        if (searchQuery) {
            const name = server.name.toLowerCase();
            const hostname = server.hostname.toLowerCase();
            searchMatch = name.includes(searchQuery) || hostname.includes(searchQuery);
        }
        
        return statusMatch && searchMatch;
    });
}

function getServerStatus(server) {
    if (!server.metrics || !server.metrics.is_online) {
        return 'offline';
    }
    
    const cpu = server.metrics.cpu_percent || 0;
    const memory = server.metrics.memory_percent || 0;
    const storage = server.metrics.storage_percent || 0;
    
    if (cpu >= 90 || memory >= 90 || storage >= 95) {
        return 'critical';
    }
    if (cpu >= 80 || memory >= 85 || storage >= 90) {
        return 'warning';
    }
    
    return 'online';
}

function getStatusClass(server) {
    const status = getServerStatus(server);
    return status;
}

function renderServerCards(list) {
    if (list.length === 0) {
        serversGrid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
                    <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
                    <line x1="6" y1="6" x2="6.01" y2="6"/>
                    <line x1="6" y1="18" x2="6.01" y2="18"/>
                </svg>
                <h3>No servers found</h3>
                <p>Add your first server to start monitoring</p>
                <button class="btn-primary" onclick="openServerModal()">Add Server</button>
            </div>
        `;
        return;
    }
    
    serversGrid.innerHTML = list.map(server => {
        const status = getServerStatus(server);
        const metrics = server.metrics || {};
        
        return `
            <div class="server-card ${status}" data-id="${server.id}">
                <div class="server-card-header">
                    <div class="server-info">
                        <h3>${escapeHtml(server.name)}</h3>
                        <p>${escapeHtml(server.hostname)}</p>
                    </div>
                    <div class="server-status ${status}"></div>
                </div>
                <div class="server-metrics">
                    <div class="metric-item">
                        <div class="metric-label">CPU</div>
                        <div class="metric-value ${getMetricClass(metrics.cpu_percent)}">${formatPercent(metrics.cpu_percent)}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill ${getMetricClass(metrics.cpu_percent)}" style="width: ${Math.min(100, metrics.cpu_percent || 0)}%"></div>
                        </div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Memory</div>
                        <div class="metric-value ${getMetricClass(metrics.memory_percent)}">${formatPercent(metrics.memory_percent)}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill ${getMetricClass(metrics.memory_percent)}" style="width: ${Math.min(100, metrics.memory_percent || 0)}%"></div>
                        </div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">Storage</div>
                        <div class="metric-value ${getMetricClass(metrics.storage_percent)}">${formatPercent(metrics.storage_percent)}%</div>
                        <div class="progress-bar">
                            <div class="progress-fill ${getMetricClass(metrics.storage_percent)}" style="width: ${Math.min(100, metrics.storage_percent || 0)}%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers
    serversGrid.querySelectorAll('.server-card').forEach(card => {
        card.addEventListener('click', (e) => {
            if (e.target.closest('.server-actions')) return;
            const serverId = card.dataset.id;
            openServerDetailModal(parseInt(serverId));
        });
    });
}

function renderServerTable(list) {
    if (list.length === 0) {
        serversTableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    No servers found
                </td>
            </tr>
        `;
        return;
    }
    
    serversTableBody.innerHTML = list.map(server => {
        const status = getServerStatus(server);
        const metrics = server.metrics || {};
        
        return `
            <tr>
                <td><span class="table-status server-status ${status}"></span></td>
                <td><strong>${escapeHtml(server.name)}</strong></td>
                <td>${escapeHtml(server.hostname)}</td>
                <td class="table-metric ${getMetricClass(metrics.cpu_percent)}">${formatPercent(metrics.cpu_percent)}%</td>
                <td class="table-metric ${getMetricClass(metrics.memory_percent)}">${formatPercent(metrics.memory_percent)}%</td>
                <td class="table-metric ${getMetricClass(metrics.storage_percent)}">${formatPercent(metrics.storage_percent)}%</td>
                <td>${formatTimestamp(metrics.collected_at)}</td>
                <td class="table-actions">
                    <button onclick="openServerModal(${server.id})" title="Edit">✏️</button>
                    <button onclick="deleteServer(${server.id})" class="danger" title="Delete">🗑️</button>
                </td>
            </tr>
        `;
    }).join('');
}

// Stats
function updateStats() {
    let online = 0, warning = 0, critical = 0, offline = 0;
    
    servers.forEach(server => {
        const status = getServerStatus(server);
        if (status === 'online') online++;
        else if (status === 'warning') warning++;
        else if (status === 'critical') critical++;
        else if (status === 'offline') offline++;
    });
    
    document.getElementById('onlineCount').textContent = online;
    document.getElementById('warningCount').textContent = warning;
    document.getElementById('criticalCount').textContent = critical;
    document.getElementById('offlineCount').textContent = offline;
}

// Settings
function applySettings() {
    if (settings.telegram_token && settings.telegram_token !== '') {
        document.getElementById('telegramToken').value = '***';
    }
    if (settings.telegram_chat_id) {
        document.getElementById('telegramChatId').value = settings.telegram_chat_id;
    }
    if (settings.cpu_threshold) {
        document.getElementById('cpuThreshold').value = settings.cpu_threshold;
        document.getElementById('cpuThresholdValue').textContent = settings.cpu_threshold;
    }
    if (settings.cpu_datapoints) {
        document.getElementById('cpuDatapoints').value = settings.cpu_datapoints;
    }
    if (settings.cpu_evaluation_minutes) {
        document.getElementById('cpuEvaluationMinutes').value = settings.cpu_evaluation_minutes;
    }
    if (settings.memory_threshold) {
        document.getElementById('memoryThreshold').value = settings.memory_threshold;
        document.getElementById('memoryThresholdValue').textContent = settings.memory_threshold;
    }
    if (settings.memory_datapoints) {
        document.getElementById('memoryDatapoints').value = settings.memory_datapoints;
    }
    if (settings.memory_evaluation_minutes) {
        document.getElementById('memoryEvaluationMinutes').value = settings.memory_evaluation_minutes;
    }
    if (settings.storage_threshold) {
        document.getElementById('storageThreshold').value = settings.storage_threshold;
        document.getElementById('storageThresholdValue').textContent = settings.storage_threshold;
    }
    if (settings.storage_datapoints) {
        document.getElementById('storageDatapoints').value = settings.storage_datapoints;
    }
    if (settings.storage_evaluation_minutes) {
        document.getElementById('storageEvaluationMinutes').value = settings.storage_evaluation_minutes;
    }
}

async function saveSettings() {
    const data = {
        telegram_token: document.getElementById('telegramToken').value,
        telegram_chat_id: document.getElementById('telegramChatId').value,
        // CPU settings
        cpu_threshold: parseInt(document.getElementById('cpuThreshold').value),
        cpu_datapoints: parseInt(document.getElementById('cpuDatapoints').value),
        cpu_evaluation_minutes: parseInt(document.getElementById('cpuEvaluationMinutes').value),
        // Memory settings
        memory_threshold: parseInt(document.getElementById('memoryThreshold').value),
        memory_datapoints: parseInt(document.getElementById('memoryDatapoints').value),
        memory_evaluation_minutes: parseInt(document.getElementById('memoryEvaluationMinutes').value),
        // Storage settings
        storage_threshold: parseInt(document.getElementById('storageThreshold').value),
        storage_datapoints: parseInt(document.getElementById('storageDatapoints').value),
        storage_evaluation_minutes: parseInt(document.getElementById('storageEvaluationMinutes').value)
    };
    
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        if (result.success) {
            showToast('Settings saved successfully', 'success');
        } else {
            showToast(result.message || 'Failed to save settings', 'error');
        }
    } catch (error) {
        showToast('Failed to save settings', 'error');
    }
}

async function changePassword() {
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (!currentPassword || !newPassword || !confirmPassword) {
        showToast('Please fill all password fields', 'error');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showToast('New passwords do not match', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                old_password: currentPassword,
                new_password: newPassword
            })
        });
        
        const result = await response.json();
        if (result.success) {
            showToast('Password changed successfully', 'success');
            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
        } else {
            showToast(result.message || 'Failed to change password', 'error');
        }
    } catch (error) {
        showToast('Failed to change password', 'error');
    }
}

async function testTelegram() {
    const token = document.getElementById('telegramToken').value;
    const chatId = document.getElementById('telegramChatId').value;
    
    if (!token || !chatId) {
        showToast('Please enter both token and chat ID', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/test-telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, chat_id: chatId })
        });
        
        const result = await response.json();
        if (result.success) {
            showToast('Test notification sent!', 'success');
        } else {
            showToast(result.message || 'Failed to send test', 'error');
        }
    } catch (error) {
        showToast('Failed to send test notification', 'error');
    }
}

// Server Modal
function openServerModal(serverId = null) {
    const modal = document.getElementById('serverModal');
    const title = document.getElementById('modalTitle');
    
    if (serverId) {
        const server = servers.find(s => s.id === serverId);
        if (server) {
            title.textContent = 'Edit Server';
            document.getElementById('serverId').value = server.id;
            document.getElementById('serverName').value = server.name;
            document.getElementById('serverHostname').value = server.hostname;
            document.getElementById('serverPort').value = server.port;
            document.getElementById('serverUsername').value = server.username;
            document.getElementById('serverTags').value = server.tags || '';
            
            // Set auth type
            const authType = server.auth_type;
            document.querySelector(`input[name="authType"][value="${authType}"]`).checked = true;
            toggleAuthFields(authType);
        }
    } else {
        title.textContent = 'Add Server';
        serverForm.reset();
        document.getElementById('serverId').value = '';
        document.getElementById('serverPort').value = '22';
        toggleAuthFields('password');
    }
    
    modal.classList.add('active');
}

function closeServerModal() {
    serverModal.classList.remove('active');
}

function toggleAuthFields(type) {
    const passwordField = document.getElementById('passwordField');
    const keyField = document.getElementById('keyField');
    
    if (type === 'password') {
        passwordField.classList.remove('hidden');
        keyField.classList.add('hidden');
    } else {
        passwordField.classList.add('hidden');
        keyField.classList.remove('hidden');
    }
}

async function saveServer() {
    const serverId = document.getElementById('serverId').value;
    
    const data = {
        name: document.getElementById('serverName').value,
        hostname: document.getElementById('serverHostname').value,
        port: parseInt(document.getElementById('serverPort').value),
        username: document.getElementById('serverUsername').value,
        auth_type: document.querySelector('input[name="authType"]:checked').value,
        password: document.getElementById('serverPassword').value,
        key: document.getElementById('serverKey').value,
        tags: document.getElementById('serverTags').value
    };
    
    // Don't send empty password/key
    if (!data.password) delete data.password;
    if (!data.key) delete data.key;
    
    try {
        let response;
        if (serverId) {
            response = await fetch(`/api/servers/${serverId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } else {
            response = await fetch('/api/servers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            showToast(serverId ? 'Server updated successfully' : 'Server added successfully', 'success');
            closeServerModal();
            loadServers();
        } else {
            showToast(result.message || 'Failed to save server', 'error');
        }
    } catch (error) {
        showToast('Failed to save server', 'error');
    }
}

async function testConnection() {
    const btn = document.getElementById('testConnectionBtn');
    btn.disabled = true;
    btn.textContent = 'Testing...';
    
    const data = {
        hostname: document.getElementById('serverHostname').value,
        port: parseInt(document.getElementById('serverPort').value),
        username: document.getElementById('serverUsername').value,
        auth_type: document.querySelector('input[name="authType"]:checked').value,
        password: document.getElementById('serverPassword').value,
        key: document.getElementById('serverKey').value
    };
    
    try {
        const response = await fetch('/api/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(result.message || 'Connection successful!', 'success');
        } else {
            showToast(result.message || 'Connection failed', 'error');
        }
    } catch (error) {
        showToast('Connection test failed', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Test Connection';
    }
}

async function deleteServer(serverId) {
    if (!confirm('Are you sure you want to delete this server?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/servers/${serverId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('Server deleted', 'success');
            loadServers();
        } else {
            showToast(result.message || 'Failed to delete server', 'error');
        }
    } catch (error) {
        showToast('Failed to delete server', 'error');
    }
}

// Auto Refresh
function startAutoRefresh() {
    setInterval(() => {
        loadServers();
    }, 5000); // 5 seconds
}

// Utility Functions
function formatPercent(value) {
    if (value === null || value === undefined || isNaN(value)) return '0';
    return Math.round(value);
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    
    // Handle both formats: "2026-04-02 16:55:04" and ISO format
    let date;
    if (timestamp.includes(' ')) {
        // Format: "2026-04-02 16:55:04" - parse as local time
        const [d, t] = timestamp.split(' ');
        const [y, m, day] = d.split('-').map(Number);
        const [h, min, s] = t.split(':').map(Number);
        date = new Date(y, m - 1, day, h, min, s);
    } else {
        date = new Date(timestamp);
    }
    
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    
    return date.toLocaleDateString();
}

function getMetricClass(value) {
    if (value === null || value === undefined) return 'normal';
    if (value >= 90) return 'critical';
    if (value >= 80) return 'warning';
    return 'normal';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 10l4 4 8-8"/></svg>',
        error: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="10" cy="10" r="8"/><path d="M6 6l8 8M14 6l-8 8"/></svg>',
        warning: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 6v4M10 14h.01"/><path d="M10 2l7 12H3L10 2z"/></svg>'
    };
    
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <span class="toast-message">${escapeHtml(message)}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// Make functions global
window.openServerModal = openServerModal;
window.deleteServer = deleteServer;
window.openServerDetailModal = openServerDetailModal;

// Server Detail Modal Functions
async function openServerDetailModal(serverId) {
    currentDetailServerId = serverId;
    const server = servers.find(s => s.id === serverId);
    if (!server) return;
    
    const modal = document.getElementById('serverDetailModal');
    document.getElementById('detailServerName').textContent = server.name;
    document.getElementById('detailHostname').textContent = server.hostname;
    
    // Get current metrics
    const response = await fetch(`/api/servers/${serverId}/metrics`);
    const data = await response.json();
    
    if (data.success && data.latest) {
        const m = data.latest;
        const status = m.is_online ? 'online' : 'offline';
        
        document.getElementById('detailStatus').textContent = status.charAt(0).toUpperCase() + status.slice(1);
        document.getElementById('detailStatus').className = `detail-stat-value text-${status === 'online' ? 'success' : 'danger'}`;
        
        document.getElementById('detailLastCheck').textContent = formatTimestamp(m.collected_at);
        
        // Update metrics
        updateDetailMetric('Cpu', m.cpu_percent);
        updateDetailMetric('Memory', m.memory_percent);
        updateDetailMetric('Storage', m.storage_percent);
    }
    
    // Load chart with default 30 minutes
    loadServerDetailChart(serverId, 0.02);
    
    modal.classList.add('active');
}

function updateDetailMetric(name, value) {
    const cls = getMetricClass(value);
    document.getElementById(`detail${name}`).textContent = `${formatPercent(value)}%`;
    document.getElementById(`detail${name}`).className = `detail-metric-value ${cls}`;
    document.getElementById(`detail${name}Bar`).style.width = `${Math.min(100, value)}%`;
    document.getElementById(`detail${name}Bar`).className = `detail-metric-fill ${cls}`;
}

async function loadServerDetailChart(serverId, days) {
    try {
        // Convert days to hours for API
        const hours = Math.ceil(days * 24);
        const response = await fetch(`/api/servers/${serverId}/metrics?hours=${hours}`);
        const data = await response.json();
        
        if (!data.success || !data.history || data.history.length === 0) {
            showNoDataChart();
            return;
        }
        
        const history = data.history;
        const labels = history.map(m => {
            const date = new Date(m.collected_at);
            if (days <= 0.25) {
                // Less than 6 hours: show time only
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            } else if (days <= 1) {
                // Less than 24 hours: show hour:minute
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            } else {
                // More than 1 day: show date + time
                return date.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            }
        });
        
        const cpuData = history.map(m => m.cpu_percent);
        const memData = history.map(m => m.memory_percent);
        const diskData = history.map(m => m.storage_percent);
        
        renderChart(labels, cpuData, memData, diskData);
    } catch (error) {
        showNoDataChart();
    }
}

function showNoDataChart() {
    if (metricsChart) {
        metricsChart.destroy();
        metricsChart = null;
    }
    const ctx = document.getElementById('metricsChart').getContext('2d');
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.font = '14px IBM Plex Sans';
    ctx.fillStyle = '#8b949e';
    ctx.textAlign = 'center';
    ctx.fillText('No historical data available', ctx.canvas.width / 2, ctx.canvas.height / 2);
}

function renderChart(labels, cpuData, memData, diskData) {
    const ctx = document.getElementById('metricsChart').getContext('2d');
    
    if (metricsChart) {
        metricsChart.destroy();
    }
    
    metricsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'CPU',
                    data: cpuData,
                    borderColor: '#58a6ff',
                    backgroundColor: 'rgba(88, 166, 255, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Memory',
                    data: memData,
                    borderColor: '#3fb950',
                    backgroundColor: 'rgba(63, 185, 80, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Storage',
                    data: diskData,
                    borderColor: '#d29922',
                    backgroundColor: 'rgba(210, 153, 34, 0.1)',
                    fill: true,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#f0f6fc',
                        font: { family: 'IBM Plex Sans' }
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#8b949e' },
                    grid: { color: '#30363d' }
                },
                y: {
                    min: 0,
                    max: 100,
                    ticks: { 
                        color: '#8b949e',
                        callback: (value) => value + '%'
                    },
                    grid: { color: '#30363d' }
                }
            }
        }
    });
}

function closeServerDetailModal() {
    serverDetailModal.classList.remove('active');
    currentDetailServerId = null;
    if (metricsChart) {
        metricsChart.destroy();
        metricsChart = null;
    }
}

// Fetch alarm status for sidebar badge
let currentAlarms = [];

async function fetchAlarms() {
    try {
        const response = await fetch('/api/alarms');
        const data = await response.json();
        currentAlarms = data.alarms || [];
        
        const alarmBadge = document.getElementById('alarmBadge');
        const alarmCount = document.getElementById('alarmCount');
        
        if (data.count > 0) {
            alarmBadge.style.display = 'flex';
            alarmCount.textContent = data.count;
        } else {
            alarmBadge.style.display = 'none';
        }
    } catch (error) {
        console.error('Error fetching alarms:', error);
    }
}

function showAlarmsModal() {
    const modal = document.getElementById('alarmsModal');
    const list = document.getElementById('alarmsList');
    
    if (currentAlarms.length === 0) {
        list.innerHTML = '<p style="color: var(--text-secondary);">No alarms</p>';
    } else {
        list.innerHTML = currentAlarms.map(alarm => `
            <div class="alarm-item">
                <span>${alarm.server_name}</span>
                <span class="metric-label">${alarm.metric.toUpperCase()}</span>
            </div>
        `).join('');
    }
    
    modal.classList.add('active');
}

function closeAlarmsModal() {
    document.getElementById('alarmsModal').classList.remove('active');
}

// Add alarms modal close handler
document.getElementById('alarmsModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'alarmsModal') {
        closeAlarmsModal();
    }
});

// Initialize alarm polling on page load
fetchAlarms();
setInterval(fetchAlarms, 30000); // Every 30 seconds