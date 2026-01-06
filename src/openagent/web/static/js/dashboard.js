// Dashboard page logic
document.addEventListener('DOMContentLoaded', loadDashboard);

async function loadDashboard() {
    try {
        const status = await getStatus();
        updateStatus(status);
        updateStats(status);
        updateProgress(status);
    } catch (error) {
        console.error('Failed to load dashboard:', error);
        document.getElementById('status-content').innerHTML = '<p class="loading">Error loading status</p>';
    }
}

function updateStatus(status) {
    const container = document.getElementById('status-content');
    
    if (!status.has_plan) {
        container.innerHTML = `
            <p>No active plan</p>
            <button class="btn btn-primary" onclick="showCreatePlanModal()">Create Plan</button>
        `;
        return;
    }

    const plan = status.plan;
    container.innerHTML = `
        <h4>${escapeHtml(plan.goal)}</h4>
        <div class="phase-timeline">
            ${plan.phases.map(phase => `
                <span class="phase-item ${phase.status.toLowerCase()}">${escapeHtml(phase.name)}</span>
            `).join('')}
        </div>
    `;
}

function updateStats(status) {
    document.getElementById('notes-count').textContent = status.notes_count || 0;
    document.getElementById('decisions-count').textContent = status.decisions_count || 0;
    document.getElementById('errors-count').textContent = status.errors_count || 0;
}

function updateProgress(status) {
    const progress = status.progress || 0;
    document.getElementById('progress-fill').style.width = `${progress}%`;
    document.getElementById('progress-text').textContent = `${progress.toFixed(0)}%`;
}

function updateCurrentPhase(status) {
    const container = document.getElementById('current-phase');
    
    if (!status.has_plan || !status.current_phase) {
        container.innerHTML = '<p>No active phase</p>';
        return;
    }

    container.innerHTML = `
        <h4>${escapeHtml(status.current_phase)}</h4>
        <p>${status.progress.toFixed(0)}% complete</p>
    `;
}

async function clearAll() {
    if (confirm('Are you sure you want to clear all data?')) {
        await clearAll();
        location.reload();
    }
}

function showCreatePlanModal() {
    document.getElementById('create-plan-modal').classList.add('active');
}

function hideCreatePlanModal() {
    document.getElementById('create-plan-modal').classList.remove('active');
}

async function createPlanSubmit(event) {
    event.preventDefault();
    
    const goal = document.getElementById('plan-goal').value;
    const phasesText = document.getElementById('plan-phases').value;
    const phases = phasesText.split(',').map(p => p.trim()).filter(p => p);
    
    try {
        await createPlan(goal, phases);
        hideCreatePlanModal();
        loadDashboard();
    } catch (error) {
        console.error('Failed to create plan:', error);
        alert('Failed to create plan');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
