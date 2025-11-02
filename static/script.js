class BotDashboard {
    constructor() {
        this.socket = io();
        this.isBotRunning = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupSocketListeners();
        this.updateStats();
        
        // Update stats every 10 seconds
        setInterval(() => this.updateStats(), 10000);
    }

    setupEventListeners() {
        document.getElementById('startBot').addEventListener('click', () => this.startBot());
        document.getElementById('stopBot').addEventListener('click', () => this.stopBot());
        document.getElementById('manualPost').addEventListener('click', () => this.manualPost());
        document.getElementById('manualEngage').addEventListener('click', () => this.manualEngage());
    }

    setupSocketListeners() {
        this.socket.on('connect', () => {
            this.addLog('🔗 Connected to bot dashboard');
        });

        this.socket.on('disconnect', () => {
            this.addLog('🔌 Disconnected from server');
        });

        this.socket.on('log_update', (data) => {
            this.addLog(data.message);
        });

        this.socket.on('bot_status', (data) => {
            this.updateBotStatus(data.status);
        });
    }

    async startBot() {
        this.setLoading('startBot', true);
        try {
            const response = await fetch('/api/start', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.showAlert(result.message, 'success');
                this.updateBotStatus('running');
            } else {
                this.showAlert(result.message, 'error');
            }
        } catch (error) {
            this.showAlert('Failed to start bot: ' + error.message, 'error');
        } finally {
            this.setLoading('startBot', false);
        }
    }

    async stopBot() {
        this.setLoading('stopBot', true);
        try {
            const response = await fetch('/api/stop', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.showAlert(result.message, 'success');
                this.updateBotStatus('stopped');
            } else {
                this.showAlert(result.message, 'error');
            }
        } catch (error) {
            this.showAlert('Failed to stop bot: ' + error.message, 'error');
        } finally {
            this.setLoading('stopBot', false);
        }
    }

    async manualPost() {
        this.setLoading('manualPost', true);
        try {
            const response = await fetch('/api/post', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.showAlert(result.message, 'success');
                this.updateStats();
            } else {
                this.showAlert(result.message, 'error');
            }
        } catch (error) {
            this.showAlert('Failed to create post: ' + error.message, 'error');
        } finally {
            this.setLoading('manualPost', false);
        }
    }

    async manualEngage() {
        this.setLoading('manualEngage', true);
        try {
            const response = await fetch('/api/engage', { method: 'POST' });
            const result = await response.json();
            
            if (result.success) {
                this.showAlert(result.message, 'success');
                this.updateStats();
            } else {
                this.showAlert(result.message, 'error');
            }
        } catch (error) {
            this.showAlert('Failed to engage: ' + error.message, 'error');
        } finally {
            this.setLoading('manualEngage', false);
        }
    }

    async updateStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            this.updateDisplay('status', this.formatStatus(stats.status));
            this.updateDisplay('lastPost', stats.last_post || 'Never');
            this.updateDisplay('postsToday', stats.posts_today || 0);
            this.updateDisplay('engagementsToday', stats.engagements_today || 0);
            
            this.updateBotStatus(stats.status);
        } catch (error) {
            console.error('Failed to update stats:', error);
        }
    }

    updateBotStatus(status) {
        this.isBotRunning = status === 'running';
        
        const startBtn = document.getElementById('startBot');
        const stopBtn = document.getElementById('stopBot');
        
        startBtn.disabled = this.isBotRunning;
        stopBtn.disabled = !this.isBotRunning;
    }

    formatStatus(status) {
        const statusMap = {
            'running': '<span class="status-indicator status-running"></span> Running',
            'stopped': '<span class="status-indicator status-stopped"></span> Stopped',
            'error': '<span class="status-indicator status-error"></span> Error'
        };
        return statusMap[status] || '<span class="status-indicator status-stopped"></span> Unknown';
    }

    updateDisplay(elementId, content) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = content;
        }
    }

    addLog(message) {
        const logContainer = document.getElementById('logContainer');
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';
        
        const timestamp = new Date().toLocaleTimeString();
        logEntry.innerHTML = `<strong>[${timestamp}]</strong> ${message}`;
        
        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Keep only last 100 logs
        const logs = logContainer.getElementsByClassName('log-entry');
        if (logs.length > 100) {
            logs[0].remove();
        }
    }

    showAlert(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        const controls = document.querySelector('.controls');
        controls.parentNode.insertBefore(alert, controls);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }

    setLoading(buttonId, isLoading) {
        const button = document.getElementById(buttonId);
        const originalText = button.textContent;
        
        if (isLoading) {
            button.innerHTML = `<span class="spinner"></span> Loading...`;
            button.disabled = true;
        } else {
            button.textContent = originalText.replace('<span class="spinner"></span> Loading...', '');
            button.disabled = false;
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new BotDashboard();
});