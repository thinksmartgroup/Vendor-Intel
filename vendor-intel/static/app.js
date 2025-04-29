// API endpoints
const API = {
    STATES: '/api/states',
    CITIES: '/api/cities',
    PROGRESS: '/get_progress',
    START: '/start',
    STOP: '/stop_processing',
    RESULTS: '/get_latest_results'
};

// DOM Elements
const elements = {
    processButton: document.getElementById('process-batch'),
    stopButton: document.getElementById('stop-processing'),
    loadingSpinner: document.getElementById('loading-spinner'),
    buttonText: document.getElementById('button-text'),
    progressBar: document.getElementById('progress-bar'),
    progressText: document.getElementById('progress-percentage'),
    processedCount: document.getElementById('total-processed'),
    successfulCount: document.getElementById('successful'),
    failedCount: document.getElementById('failed'),
    remainingCount: document.getElementById('remaining'),
    resultsSection: document.getElementById('results'),
    industrySelect: document.getElementById('industry-select'),
    stateSelect: document.getElementById('stateSelect'),
    citySelect: document.getElementById('citySelect')
};

// State Management
const state = {
    states: [],
    citiesByState: {},
    isProcessing: false
};

// API Calls
const api = {
    async getStates() {
        const response = await fetch(API.STATES);
        const data = await response.json();
        return data.states;
    },

    async getCities(selectedState) {
        const response = await fetch(`${API.CITIES}?state=${selectedState}`);
        const data = await response.json();
        return data.cities;
    },

    async getProgress() {
        const response = await fetch(API.PROGRESS);
        return await response.json();
    },

    async startProcessing(stateFilter, cityFilter) {
        const response = await fetch(API.START, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                state: stateFilter === "" ? null : stateFilter,
                city: cityFilter === "" ? null : cityFilter
            })
        });
        return await response.json();
    },

    async stopProcessing() {
        const response = await fetch(API.STOP, { method: 'POST' });
        return await response.json();
    },

    async getResults() {
        const response = await fetch(API.RESULTS);
        return await response.json();
    }
};

// UI Updates
const ui = {
    updateProgress(data) {
        const percentage = data.overall_progress || 0;
        elements.progressBar.style.width = `${percentage}%`;
        elements.progressText.textContent = `${percentage.toFixed(1)}%`;
        elements.processedCount.textContent = data.total_processed || 0;
        elements.remainingCount.textContent = data.remaining || 0;
        elements.successfulCount.textContent = data.successful || 0;
        elements.failedCount.textContent = data.failed || 0;
    },

    updateProcessingState(isProcessing) {
        elements.processButton.disabled = isProcessing;
        elements.stopButton.classList.toggle('hidden', !isProcessing);
        elements.buttonText.textContent = isProcessing ? 'Processing...' : 'Process Next Batch';
        elements.loadingSpinner.classList.toggle('hidden', !isProcessing);
    },

    showError(message) {
        elements.resultsSection.innerHTML = `
            <div class="bg-red-900/30 border border-red-500/20 rounded-lg p-4">
                <div class="flex items-center">
                    <svg class="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    <p class="ml-2 text-red-400">Error</p>
                </div>
                <p class="mt-2 text-sm text-gray-400">${message}</p>
            </div>
        `;
    },

    updateResults(results) {
        if (!results || results.length === 0) {
            elements.resultsSection.innerHTML = `
                <div class="text-center py-8">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p class="mt-2 text-gray-400">No results yet</p>
                </div>
            `;
            return;
        }

        const resultsHtml = results.map(result => `
            <div class="bg-gray-800/50 border border-gray-700 rounded-lg p-4 hover:bg-gray-800/70 transition-colors">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="font-medium text-indigo-300">${result.title}</h3>
                    <span class="text-xs text-gray-400">${result.location}</span>
                </div>
                <p class="text-sm text-gray-300 mb-2">${result.snippet}</p>
                <a href="${result.url}" target="_blank" class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                    Visit Website →
                </a>
            </div>
        `).join('');

        elements.resultsSection.innerHTML = resultsHtml;
    },

    populateStates() {
        elements.stateSelect.innerHTML = '<option value="">All States</option>';
        state.states.forEach(stateName => {
            const option = document.createElement('option');
            option.value = stateName;
            option.textContent = stateName;
            elements.stateSelect.appendChild(option);
        });
    },

    populateCities(selectedState) {
        elements.citySelect.innerHTML = '<option value="">All Cities</option>';
        if (state.citiesByState[selectedState]) {
            state.citiesByState[selectedState].forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                elements.citySelect.appendChild(option);
            });
        }
        elements.citySelect.disabled = !selectedState;
    }
};

// Event Handlers
async function handleStateChange() {
    const selectedState = elements.stateSelect.value;
    elements.citySelect.disabled = !selectedState;

    if (selectedState) {
        try {
            const cities = await api.getCities(selectedState);
            state.citiesByState[selectedState] = cities.sort();
            ui.populateCities(selectedState);
        } catch (error) {
            console.error('Error fetching cities:', error);
            ui.showError('Failed to fetch cities');
        }
    } else {
        elements.citySelect.innerHTML = '<option value="">All Cities</option>';
        elements.citySelect.disabled = true;
    }
}

async function handleProcessBatch() {
    try {
        ui.updateProcessingState(true);
        const stateFilter = elements.stateSelect.value;
        const cityFilter = elements.citySelect.value;
        
        const result = await api.startProcessing(stateFilter, cityFilter);
        if (result.status === 'Processing started') {
            state.isProcessing = true;
            updateProgress();
        }
    } catch (error) {
        console.error('Error processing batch:', error);
        ui.updateProcessingState(false);
        ui.showError(error.message);
    }
}

async function handleStopProcessing() {
    try {
        await api.stopProcessing();
        state.isProcessing = false;
        ui.updateProcessingState(false);
    } catch (error) {
        console.error('Error stopping process:', error);
        ui.showError('Failed to stop processing');
    }
}

async function updateProgress() {
    try {
        const data = await api.getProgress();
        ui.updateProgress(data);

        if (data.is_processing) {
            ui.updateProcessingState(true);
            setTimeout(updateProgress, 1000);
        } else {
            ui.updateProcessingState(false);
            const results = await api.getResults();
            ui.updateResults(results.results);
        }
    } catch (error) {
        console.error('Error updating progress:', error);
    }
}

// Initialize
async function initialize() {
    try {
        state.states = await api.getStates();
        ui.populateStates();
        updateProgress();
    } catch (error) {
        console.error('Error initializing:', error);
        ui.showError('Failed to initialize application');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', initialize);
elements.stateSelect.addEventListener('change', handleStateChange);
elements.processButton.addEventListener('click', handleProcessBatch);
elements.stopButton.addEventListener('click', handleStopProcessing); 