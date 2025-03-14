/**
 * Network Monitoring System - Main JavaScript
 */

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Setup sidebar toggle for mobile view
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            document.body.classList.toggle('sidebar-collapsed');
        });
    }
    
    // Auto-refresh timer for dashboard
    setupAutoRefresh();
    
    // Add event listeners for device toggles
    setupDeviceToggles();
    
    // Setup search functionality
    setupSearch();
});

/**
 * Setup auto-refresh functionality
 */
function setupAutoRefresh() {
    const refreshToggle = document.getElementById('refreshToggle');
    const refreshIndicator = document.getElementById('refreshIndicator');
    const refreshIntervalSelect = document.getElementById('refreshInterval');
    
    let refreshInterval = null;
    let refreshSeconds = 30; // Default refresh interval
    
    // Check if elements exist
    if (!refreshToggle || !refreshIndicator) return;
    
    if (refreshIntervalSelect) {
        refreshIntervalSelect.addEventListener('change', function() {
            refreshSeconds = parseInt(this.value, 10);
            
            // If auto-refresh is enabled, restart the timer with new interval
            if (refreshInterval) {
                clearInterval(refreshInterval);
                startRefreshTimer();
            }
        });
    }
    
    // Toggle auto-refresh
    refreshToggle.addEventListener('change', function() {
        if (this.checked) {
            startRefreshTimer();
        } else {
            clearInterval(refreshInterval);
            refreshInterval = null;
            refreshIndicator.textContent = 'Off';
            refreshIndicator.classList.remove('text-success');
            refreshIndicator.classList.add('text-danger');
        }
    });
    
    // Start the refresh timer
    function startRefreshTimer() {
        let timeLeft = refreshSeconds;
        refreshIndicator.textContent = timeLeft + 's';
        refreshIndicator.classList.remove('text-danger');
        refreshIndicator.classList.add('text-success');
        
        refreshInterval = setInterval(function() {
            timeLeft--;
            
            if (timeLeft <= 0) {
                // Refresh the page or fetch new data
                timeLeft = refreshSeconds;
                fetchUpdatedData();
            }
            
            refreshIndicator.textContent = timeLeft + 's';
        }, 1000);
    }
    
    // Fetch updated data without page refresh
    function fetchUpdatedData() {
        // Get the current page
        const currentPath = window.location.pathname;
        
        if (currentPath === '/' || currentPath === '/index') {
            // Dashboard page - update dashboard data
            fetch('/api/dashboard-data')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error fetching dashboard data:', error));
        } else if (currentPath.includes('/devices/')) {
            // Device details page - update device data
            const deviceId = currentPath.split('/').pop();
            fetch(`/api/devices/${deviceId}`)
                .then(response => response.json())
                .then(data => updateDeviceDetails(data))
                .catch(error => console.error('Error fetching device data:', error));
        } else if (currentPath === '/alerts') {
            // Alerts page - update alerts data
            fetch('/api/alerts')
                .then(response => response.json())
                .then(data => updateAlerts(data))
                .catch(error => console.error('Error fetching alerts data:', error));
        }
    }
    
    // Update dashboard with new data
    function updateDashboard(data) {
        // Update device counts
        if (data.device_count !== undefined) {
            const totalDevicesElement = document.getElementById('total-devices');
            if (totalDevicesElement) totalDevicesElement.textContent = data.device_count;
        }
        
        if (data.online_count !== undefined) {
            const onlineDevicesElement = document.getElementById('online-devices');
            if (onlineDevicesElement) onlineDevicesElement.textContent = data.online_count;
        }
        
        if (data.warning_count !== undefined) {
            const warningDevicesElement = document.getElementById('warning-devices');
            if (warningDevicesElement) warningDevicesElement.textContent = data.warning_count;
        }
        
        if (data.critical_count !== undefined) {
            const criticalAlertsElement = document.getElementById('critical-alerts');
            if (criticalAlertsElement) criticalAlertsElement.textContent = data.critical_count;
        }
        
        // Update charts
        updateCharts(data);
    }
    
    // Update device details page
    function updateDeviceDetails(data) {
        // Update status
        if (data.status) {
            const statusElement = document.querySelector('.device-status');
            if (statusElement) {
                const statusClass = 'status-' + data.status.toLowerCase();
                
                // Remove all status classes and add the current one
                statusElement.classList.remove('status-online', 'status-warning', 'status-critical', 'status-offline');
                statusElement.classList.add(statusClass);
                
                // Update status text
                const statusText = statusElement.querySelector('.status-text');
                if (statusText) statusText.textContent = data.status;
            }
        }
        
        // Update metrics
        if (data.cpu !== undefined) {
            const cpuElement = document.getElementById('cpu-value');
            if (cpuElement) cpuElement.textContent = data.cpu + '%';
        }
        
        if (data.memory !== undefined) {
            const memoryElement = document.getElementById('memory-value');
            if (memoryElement) memoryElement.textContent = data.memory + '%';
        }
        
        // Update charts
        updateDeviceCharts(data);
    }
    
    // Update alerts page
    function updateAlerts(data) {
        // This function would update the alerts table without refreshing the page
        // Implementation depends on the specific structure of your alerts table
    }
    
    // Update dashboard charts
    function updateCharts(data) {
        // CPU Chart
        if (data.cpu_data && data.cpu_labels) {
            const cpuChart = Chart.getChart('cpu-chart');
            if (cpuChart) {
                cpuChart.data.labels = data.cpu_labels;
                cpuChart.data.datasets[0].data = data.cpu_data;
                cpuChart.update();
            }
        }
        
        // Memory Chart
        if (data.memory_data && data.memory_labels) {
            const memoryChart = Chart.getChart('memory-chart');
            if (memoryChart) {
                memoryChart.data.labels = data.memory_labels;
                memoryChart.data.datasets[0].data = data.memory_data;
                memoryChart.update();
            }
        }
    }
    
    // Update device details charts
    function updateDeviceCharts(data) {
        // This function would update charts on the device details page
        // Implementation depends on the specific charts you have
    }
}

/**
 * Setup device toggle functionality
 */
function setupDeviceToggles() {
    const deviceToggles = document.querySelectorAll('.device-toggle');
    
    deviceToggles.forEach(toggle => {
        toggle.addEventListener('change', function() {
            const deviceId = this.getAttribute('data-device-id');
            const enabled = this.checked;
            
            // Send request to enable/disable device
            fetch(`/api/devices/${deviceId}/toggle`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ enabled: enabled })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    // If failed, revert the toggle
                    this.checked = !enabled;
                    alert('Failed to toggle device: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                // Revert the toggle on error
                this.checked = !enabled;
                alert('An error occurred while toggling device');
            });
        });
    });
}

/**
 * Setup search functionality
 */
function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;
    
    searchInput.addEventListener('keyup', function() {
        const searchValue = this.value.toLowerCase();
        
        // Determine what type of items to search based on the page
        const currentPath = window.location.pathname;
        
        if (currentPath === '/devices') {
            // Search devices
            searchDevices(searchValue);
        } else if (currentPath === '/alerts') {
            // Search alerts
            searchAlerts(searchValue);
        }
    });
    
    // Search devices
    function searchDevices(searchValue) {
        const deviceItems = document.querySelectorAll('.device-item');
        
        deviceItems.forEach(item => {
            const deviceName = item.querySelector('.device-name').textContent.toLowerCase();
            const deviceIp = item.querySelector('.device-ip').textContent.toLowerCase();
            const deviceType = item.querySelector('.device-type').textContent.toLowerCase();
            
            if (deviceName.includes(searchValue) || deviceIp.includes(searchValue) || deviceType.includes(searchValue)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    // Search alerts
    function searchAlerts(searchValue) {
        const alertItems = document.querySelectorAll('.alert-item');
        
        alertItems.forEach(item => {
            const alertDevice = item.querySelector('.alert-device').textContent.toLowerCase();
            const alertType = item.querySelector('.alert-type').textContent.toLowerCase();
            const alertMessage = item.querySelector('.alert-message').textContent.toLowerCase();
            
            if (alertDevice.includes(searchValue) || alertType.includes(searchValue) || alertMessage.includes(searchValue)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    }
}

/**
 * Create a network map visualization
 * @param {string} containerId - ID of the container element
 * @param {Array} nodes - Array of node objects
 * @param {Array} edges - Array of edge objects
 */
function createNetworkMap(containerId, nodes, edges) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Clear previous map
    container.innerHTML = '';
    
    // Calculate container dimensions
    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;
    
    // Create nodes
    nodes.forEach(node => {
        const nodeElement = document.createElement('div');
        nodeElement.className = `node ${node.type}`;
        nodeElement.style.left = `${node.x}px`;
        nodeElement.style.top = `${node.y}px`;
        nodeElement.setAttribute('data-node-id', node.id);
        
        // Add icon based on node type
        let iconClass = 'bi-question-circle';
        if (node.type === 'router') iconClass = 'bi-router';
        else if (node.type === 'switch') iconClass = 'bi-hdd-network';
        else if (node.type === 'server') iconClass = 'bi-server';
        else if (node.type === 'wireless') iconClass = 'bi-wifi';
        
        nodeElement.innerHTML = `
            <i class="bi ${iconClass}"></i>
            <span>${node.name}</span>
        `;
        
        // Add status class
        if (node.status) {
            nodeElement.classList.add(`status-${node.status}`);
        }
        
        // Add click event to show node details
        nodeElement.addEventListener('click', function() {
            showNodeDetails(node);
        });
        
        container.appendChild(nodeElement);
    });
    
    // Create edges
    edges.forEach(edge => {
        const sourceNode = nodes.find(node => node.id === edge.source);
        const targetNode = nodes.find(node => node.id === edge.target);
        
        if (!sourceNode || !targetNode) return;
        
        // Calculate edge coordinates
        const x1 = sourceNode.x + 40; // half of node width
        const y1 = sourceNode.y + 40; // half of node height
        const x2 = targetNode.x + 40;
        const y2 = targetNode.y + 40;
        
        const edgeElement = document.createElement('div');
        edgeElement.className = `edge ${edge.active ? 'active' : ''}`;
        
        // Calculate edge length and angle
        const length = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
        const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
        
        // Position and rotate edge
        edgeElement.style.width = `${length}px`;
        edgeElement.style.height = '2px';
        edgeElement.style.left = `${x1}px`;
        edgeElement.style.top = `${y1}px`;
        edgeElement.style.transform = `rotate(${angle}deg)`;
        
        container.appendChild(edgeElement);
    });
    
    // Function to show node details
    function showNodeDetails(node) {
        // Implement a modal or sidebar to show node details
        // This depends on your UI design
    }
}

/**
 * Format bytes to a human-readable string
 * @param {number} bytes - The bytes value to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @return {string} - Formatted string
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

/**
 * Format a date string
 * @param {string} dateString - The date string to format
 * @param {boolean} includeTime - Whether to include time in the format
 * @return {string} - Formatted date string
 */
function formatDate(dateString, includeTime = false) {
    const date = new Date(dateString);
    
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };
    
    if (includeTime) {
        options.hour = '2-digit';
        options.minute = '2-digit';
        options.second = '2-digit';
    }
    
    return date.toLocaleDateString('en-US', options);
}

/**
 * Convert milliseconds to a human-readable duration
 * @param {number} ms - The duration in milliseconds
 * @return {string} - Formatted duration string
 */
function formatDuration(ms) {
    if (ms < 1000) return ms + ' ms';
    
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
        return days + 'd ' + (hours % 24) + 'h';
    } else if (hours > 0) {
        return hours + 'h ' + (minutes % 60) + 'm';
    } else if (minutes > 0) {
        return minutes + 'm ' + (seconds % 60) + 's';
    } else {
        return seconds + 's';
    }
}