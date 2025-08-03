// Error message constants
const ERROR_MESSAGES = {
    CHART_UNAVAILABLE: 'Chart not available. The data generator may still be starting up or experiencing issues.',
    INVALID_INTERVAL: 'Please enter a valid refresh interval in seconds.',
    LOAD_FAILED: 'Failed to load chart. Try refreshing the page.',
    INDEX_NOT_FOUND: 'Chart index not found. The data generator may not be running or no charts have been generated yet.',
    NO_CHARTS_AVAILABLE: 'No charts available in the index file.'
};

document.addEventListener('DOMContentLoaded', function() {
    const chartImage = document.getElementById('chart-image');
    const updateTime = document.getElementById('update-time');
    const refreshBtn = document.getElementById('refresh-btn');
    const errorMessage = document.getElementById('error-message');
    const autoRefreshSelect = document.getElementById('auto-refresh-select');
    const customIntervalInput = document.getElementById('custom-interval');
    
    let refreshInterval = null;
    let currentChartPath = null;
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        chartImage.style.display = 'none';
    }
    
    function hideError() {
        errorMessage.style.display = 'none';
        chartImage.style.display = 'block';
    }
    
    function loadChartIndex() {
        return fetch('/plots/_CHART_INDEX')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Index file not found');
                }
                return response.text();
            })
            .then(text => {
                const charts = text.trim().split('\n').filter(line => line.trim());
                if (charts.length === 0) {
                    throw new Error('No charts in index');
                }
                // FIXME: We're only showing one chart
                return charts[0];
            });
    }
    
    function refreshChart() {
        if (currentChartPath) {
            // Use cached chart path
            const timestamp = new Date().getTime();
            chartImage.src = `/plots/${currentChartPath}?t=${timestamp}`;
            updateTime.textContent = new Date().toLocaleTimeString();
        } else {
            // Load chart index only once
            loadChartIndex()
                .then(chartFilename => {
                    currentChartPath = chartFilename;
                    const timestamp = new Date().getTime();
                    chartImage.src = `/plots/${chartFilename}?t=${timestamp}`;
                    updateTime.textContent = new Date().toLocaleTimeString();
                })
                .catch(error => {
                    if (error.message === 'Index file not found') {
                        showError(ERROR_MESSAGES.INDEX_NOT_FOUND);
                    } else if (error.message === 'No charts in index') {
                        showError(ERROR_MESSAGES.NO_CHARTS_AVAILABLE);
                    } else {
                        showError(ERROR_MESSAGES.CHART_UNAVAILABLE);
                    }
                });
        }
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