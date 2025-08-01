// Error message constants
const ERROR_MESSAGES = {
    CHART_UNAVAILABLE: 'Chart not available. The data generator may still be starting up or experiencing issues.',
    INVALID_INTERVAL: 'Please enter a valid refresh interval in seconds.',
    LOAD_FAILED: 'Failed to load chart. Please try refreshing the page.'
};

document.addEventListener('DOMContentLoaded', function() {
    const chartImage = document.getElementById('chart-image');
    const updateTime = document.getElementById('update-time');
    const refreshBtn = document.getElementById('refresh-btn');
    const errorMessage = document.getElementById('error-message');
    const autoRefreshSelect = document.getElementById('auto-refresh-select');
    const customIntervalInput = document.getElementById('custom-interval');
    
    let refreshInterval = null;
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        chartImage.style.display = 'none';
    }
    
    function hideError() {
        errorMessage.style.display = 'none';
        chartImage.style.display = 'block';
    }
    
    function refreshChart() {
        const timestamp = new Date().getTime();
        chartImage.src = `/plots/mariadb_metrics.png?t=${timestamp}`;
        updateTime.textContent = new Date().toLocaleTimeString();
    }
    
    function setupAutoRefresh(intervalMs) {
        // Clear existing interval
        if (refreshInterval) {
            clearInterval(refreshInterval);
            refreshInterval = null;
        }
        
        // Set up new interval if not disabled
        if (intervalMs > 0) {
            refreshInterval = setInterval(refreshChart, intervalMs);
        }
    }
    
    // Handle image load error
    chartImage.addEventListener('error', function() {
        showError(ERROR_MESSAGES.CHART_UNAVAILABLE);
    });
    
    // Handle image load success
    chartImage.addEventListener('load', function() {
        hideError();
    });
    
    // Handle auto-refresh dropdown change
    autoRefreshSelect.addEventListener('change', function() {
        if (this.value === 'other') {
            customIntervalInput.style.display = 'inline-block';
            customIntervalInput.focus();
        } else {
            customIntervalInput.style.display = 'none';
            const selectedInterval = parseInt(this.value);
            setupAutoRefresh(selectedInterval);
        }
    });
    
    // Handle custom interval input
    customIntervalInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const seconds = parseInt(this.value);
            if (seconds && seconds > 0) {
                setupAutoRefresh(seconds * 1000);
            } else {
                showError(ERROR_MESSAGES.INVALID_INTERVAL);
            }
        }
    });
    
    // Manual refresh button
    refreshBtn.addEventListener('click', refreshChart);
    
    // Initial setup
    refreshChart();
    setupAutoRefresh(parseInt(autoRefreshSelect.value));
});