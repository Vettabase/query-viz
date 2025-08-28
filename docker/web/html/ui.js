// DOM element IDs
const ELEMENT_IDS = {
    UPDATE_TIME: 'update-time',
    REFRESH_BTN: 'refresh-btn',
    ERROR_MESSAGE: 'error-message',
    AUTO_REFRESH_SELECT: 'auto-refresh-select',
    CUSTOM_INTERVAL_INPUT: 'custom-interval',
    AUTOREFRESH_STATUS_INDICATOR: 'autorefresh-status-indicator',
    LOADING_MESSAGE_BOX: 'loading-message-box'
};

// Files created by the backend
const PATHS = {
    CHART_INDEX: '/plots/_CHART_INDEX',
    PLOTS_BASE: '/plots/'
};

// Default values
const DEFAULTS = {
    // milliseconds
    AUTO_REFRESH_INTERVAL: 30000,
    INDEX_RELOAD_INTERVAL: 60000
};

// Event types
const EVENTS = {
    ENTER_KEY: 'Enter'
};

// Allowed autorefresh status values
const AUTOREFRESH_STATUS = {
    ENABLED: 'enabled',
    DISABLED: 'disabled',
    ERROR: 'error'
};

// Error messages
const ERROR_MESSAGES = {
    CHART_UNAVAILABLE: 'Chart not available. The data generator may still be starting up or experiencing issues.',
    INVALID_INTERVAL: 'Please enter a valid refresh interval in seconds.',
    LOAD_FAILED: 'Failed to load chart. Try refreshing the page.',
    INDEX_NOT_FOUND: 'Chart index not found. The data generator may not be running or no charts have been generated yet.',
    NO_CHARTS_AVAILABLE: 'No charts available in the index file.'
};

document.addEventListener('DOMContentLoaded', function() {
    const updateTime = document.getElementById(ELEMENT_IDS.UPDATE_TIME);
    const refreshBtn = document.getElementById(ELEMENT_IDS.REFRESH_BTN);
    const errorMessage = document.getElementById(ELEMENT_IDS.ERROR_MESSAGE);
    const autoRefreshSelect = document.getElementById(ELEMENT_IDS.AUTO_REFRESH_SELECT);
    const customIntervalInput = document.getElementById(ELEMENT_IDS.CUSTOM_INTERVAL_INPUT);
    const statusIndicator = document.getElementById(ELEMENT_IDS.AUTOREFRESH_STATUS_INDICATOR);
    const loadingMessageBox = document.getElementById(ELEMENT_IDS.LOADING_MESSAGE_BOX);
    const chartContainer = document.querySelector('.chart-container');
    
    let chartRefreshInterval = null;
    let indexReloadInterval = null;
    // chart images paths
    let currentChartPaths = [];
    // Track if index has ever loaded successfully
    let hasIndexLoadedOnce = false;
    
    function updateAutorefreshStatusIndicator(status) {
        statusIndicator.className = `autorefresh-status-indicator ${status}`;
        
        // Update tooltip text
        const statusText = {
            [AUTOREFRESH_STATUS.ENABLED]: 'Autorefresh is enabled',
            [AUTOREFRESH_STATUS.DISABLED]: 'Autorefresh is disabled',
            [AUTOREFRESH_STATUS.ERROR]: 'Autorefresh disabled due to error'
        };
        statusIndicator.title = statusText[status] || 'Autorefresh status';
    }
    
    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
        loadingMessageBox.style.display = 'none';
        // FIXME: We should somehow mark the charts that are failing
    }
    
    function hideError() {
        errorMessage.style.display = 'none';
    }
    
    function hideLoadingMessage() {
        loadingMessageBox.style.display = 'none';
    }
    
    function showLoadingMessage() {
        loadingMessageBox.style.display = 'block';
    }
    
    function enableChartAutorefreshControls() {
        autoRefreshSelect.disabled = false;
        refreshBtn.disabled = false;
    }
    
    function disableChartAutorefreshControls() {
        autoRefreshSelect.disabled = true;
        refreshBtn.disabled = true;
    }
    
    function createChartElements(chartPaths) {
        // FIXME: We shouldn't recreate all charts when any of them changed. We should:
        //        - Delete the charts that were removed
        //        - Add new charts
        //        - Recreate charts that changed
        //        To know when a chart configuration changed, we should store
        //        each chart configuration's checksum

        // Hide loading message just before loading charts
        hideLoadingMessage();
        
        // Clear existing charts
        const existingCharts = chartContainer.querySelectorAll('.chart-image');
        existingCharts.forEach(chart => chart.remove());
        
        // Create new chart elements
        chartPaths.forEach((chartPath, index) => {
            // Assign a (most likely) unique id
            // by replacing the URL's special chars
            chartId = chartPath.replace(/[^a-zA-Z0-9]/g, '_');
            
            // Create a picrow
            const permalinkDiv = document.createElement('div');
            permalinkDiv.className = 'chart-permalink';
            const permalink = document.createElement('a');
            permalink.href = '#permalink_' + chartId;
            permalink.id = 'permalink_' + chartId;
            permalink.textContent = '¶';
            
            permalinkDiv.appendChild(permalink);
            
            const chartImage = document.createElement('img');
            chartImage.className = 'chart-image';
            chartImage.alt = `Chart ${index + 1}`;
            chartImage.style.marginBottom = index < chartPaths.length - 1 ? '20px' : '0';
            chartImage.id = 'chart_' + chartId;
            
            // Handle image load error
            chartImage.addEventListener('error', function() {
                showError(ERROR_MESSAGES.CHART_UNAVAILABLE);
            });
            
            // Handle image load success
            chartImage.addEventListener('load', function() {
                hideError();
            });
            
            // Insert before error message
            chartContainer.insertBefore(permalinkDiv, errorMessage);
            chartContainer.insertBefore(chartImage, errorMessage);
        });
    }
    
    function loadChartIndex() {
        return fetch(PATHS.CHART_INDEX)
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
                
                const chartsChanged = JSON.stringify(currentChartPaths) !== JSON.stringify(charts);
                currentChartPaths = charts;
                
                // First successful load OR chart list changed
                if (!hasIndexLoadedOnce || chartsChanged) {
                    createChartElements(currentChartPaths);
                    
                    if (!hasIndexLoadedOnce) {
                        hasIndexLoadedOnce = true;
                        enableChartAutorefreshControls();
                        setupAutoRefresh(parseInt(autoRefreshSelect.value));
                    }
                }
                
                return charts;
            });
    }
    
    function refreshChart() {
        const timestamp = new Date().getTime();
        const chartImages = chartContainer.querySelectorAll('.chart-image');
        
        chartImages.forEach((chartImage, index) => {
            if (index < currentChartPaths.length) {
                chartImage.src = `${PATHS.PLOTS_BASE}${currentChartPaths[index]}?t=${timestamp}`;
            }
        });
        
        updateTime.textContent = new Date().toLocaleTimeString();
    }
    
    function setupAutoRefresh(intervalMs) {
        // Clear existing interval before creating a new one
        // or we would end up having 2 intervals
        if (chartRefreshInterval) {
            clearInterval(chartRefreshInterval);
            chartRefreshInterval = null;
        }
        
        // Set up new interval if not disabled
        if (intervalMs > 0) {
            chartRefreshInterval = setInterval(refreshChart, intervalMs);
            updateAutorefreshStatusIndicator(AUTOREFRESH_STATUS.ENABLED);
        } else {
            updateAutorefreshStatusIndicator(AUTOREFRESH_STATUS.DISABLED);
        }
    }
    
    function setupIndexReload() {
        indexReloadInterval = setInterval(() => {
            loadChartIndex().catch(error => {
                // Only disable dropdown and show error if the index was never loaded
                if (!hasIndexLoadedOnce) {
                    disableChartAutorefreshControls();
                    updateAutorefreshStatusIndicator(AUTOREFRESH_STATUS.ERROR);
                    showError(ERROR_MESSAGES.INDEX_NOT_FOUND);
                }
            });
        }, DEFAULTS.INDEX_RELOAD_INTERVAL);
    }
    
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
        if (e.key === EVENTS.ENTER_KEY) {
            const seconds = parseInt(this.value);
            if (seconds && seconds > 0) {
                setupAutoRefresh(seconds * 1000);
                this.blur(); // Remove focus
            } else {
                showError(ERROR_MESSAGES.INVALID_INTERVAL);
            }
        }
    });
    
    // Handle blur event (when user clicks away)
    customIntervalInput.addEventListener('blur', function() {
        if (this.value.trim() !== '') {
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
    
    updateAutorefreshStatusIndicator(AUTOREFRESH_STATUS.DISABLED);
    disableChartAutorefreshControls();
    showLoadingMessage();
    
    // Always set up periodic reload regardless of initial success
    setupIndexReload();
    
    loadChartIndex()
        .then(() => {
            console.log('Images found:', chartContainer.querySelectorAll('.chart-image').length);
            refreshChart();
        })
        .catch(error => {
            // First load failed - dropdown remains disabled, error shown
            updateAutorefreshStatusIndicator(AUTOREFRESH_STATUS.ERROR);
            if (error.message === 'Index file not found') {
                showError(ERROR_MESSAGES.INDEX_NOT_FOUND);
            } else if (error.message === 'No charts in index') {
                showError(ERROR_MESSAGES.NO_CHARTS_AVAILABLE);
            } else {
                showError(ERROR_MESSAGES.CHART_UNAVAILABLE);
            }
        });
});
