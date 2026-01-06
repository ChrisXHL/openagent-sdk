// API utility functions
const API = {
    async get(endpoint) {
        const response = await fetch(endpoint);
        return response.json();
    },

    async post(endpoint, data = {}) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return response.json();
    }
};

// Status functions
async function getStatus() {
    return API.get('/api/status');
}

async function createPlan(goal, phases) {
    return API.post('/api/plan', { goal, phases });
}

async function startPhase(phaseName) {
    return API.post('/api/phase/start', { phase_name: phaseName });
}

async function completePhase(phaseName) {
    return API.post('/api/phase/complete', { phase_name: phaseName });
}

async function getNotes(section = null) {
    const url = section ? `/api/notes?section=${encodeURIComponent(section)}` : '/api/notes';
    return API.get(url);
}

async function addNote(content, section = null) {
    return API.post('/api/notes', { content, section });
}

async function getDecisions() {
    return API.get('/api/decisions');
}

async function addDecision(decision, rationale) {
    return API.post('/api/decisions', { decision, rationale });
}

async function getErrors() {
    return API.get('/api/errors');
}

async function logError(error, resolution = '') {
    return API.post('/api/errors', { error, resolution });
}

async function clearAll() {
    return API.post('/api/clear');
}
