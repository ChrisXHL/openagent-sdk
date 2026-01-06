// Plan page logic
document.addEventListener('DOMContentLoaded', loadPlan);

async function loadPlan() {
    try {
        const status = await getStatus();
        updatePlan(status);
        updateActions(status);
    } catch (error) {
        console.error('Failed to load plan:', error);
        document.getElementById('plan-content').innerHTML = '<p class="loading">Error loading plan</p>';
    }
}

function updatePlan(status) {
    const container = document.getElementById('plan-content');
    
    if (!status.has_plan) {
        container.innerHTML = '<p>No active plan. Create one to get started!</p>';
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
        <p style="margin-top: 15px; color: #666;">Progress: ${status.progress.toFixed(0)}%</p>
    `;
}

function updateActions(status) {
    const container = document.getElementById('plan-actions');
    
    if (!status.has_plan) {
        container.innerHTML = '<p>No actions available</p>';
        return;
    }

    const plan = status.plan;
    const currentPhase = plan.phases.find(p => p.status === 'in_progress');
    const completedCount = plan.phases.filter(p => p.status === 'completed').length;
    
    let actionsHtml = '';
    
    if (currentPhase) {
        actionsHtml += `
            <div style="margin-bottom: 15px;">
                <h4>Current Phase: ${escapeHtml(currentPhase.name)}</h4>
                <button class="btn btn-primary" onclick="completePhase('${escapeHtml(currentPhase.name)}')">
                    Complete Phase
                </button>
            </div>
        `;
    }
    
    // Show next pending phase
    const nextPhase = plan.phases.find(p => p.status === 'pending');
    if (nextPhase) {
        actionsHtml += `
            <div style="margin-bottom: 15px;">
                <h4>Next Phase: ${escapeHtml(nextPhase.name)}</h4>
                <button class="btn btn-primary" onclick="startPhase('${escapeHtml(nextPhase.name)}')">
                    Start Phase
                </button>
            </div>
        `;
    }

    if (!actionsHtml) {
        actionsHtml = '<p>All phases completed! 🎉</p>';
    }

    container.innerHTML = actionsHtml;
}

async function startPhase(phaseName) {
    try {
        await startPhase(phaseName);
        loadPlan();
    } catch (error) {
        console.error('Failed to start phase:', error);
        alert('Failed to start phase');
    }
}

async function completePhase(phaseName) {
    try {
        await completePhase(phaseName);
        loadPlan();
    } catch (error) {
        console.error('Failed to complete phase:', error);
        alert('Failed to complete phase');
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
        loadPlan();
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
