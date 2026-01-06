// Decisions page logic
document.addEventListener('DOMContentLoaded', loadDecisions);

async function loadDecisions() {
    try {
        const decisions = await getDecisions();
        renderDecisions(decisions);
    } catch (error) {
        console.error('Failed to load decisions:', error);
        document.getElementById('decisions-list').innerHTML = '<p class="loading">Error loading decisions</p>';
    }
}

function renderDecisions(decisions) {
    const container = document.getElementById('decisions-list');
    
    if (!decisions || decisions.length === 0) {
        container.innerHTML = '<p>No decisions recorded yet. Record your first decision!</p>';
        return;
    }

    container.innerHTML = decisions.map(decision => `
        <div class="list-item">
            <div class="list-item-header">
                <span class="list-item-title">${escapeHtml(decision.decision)}</span>
                <span class="list-item-meta">${formatDate(decision.created_at)}</span>
            </div>
            <div class="list-item-content">
                <strong>Rationale:</strong> ${escapeHtml(decision.rationale)}
            </div>
        </div>
    `).join('');
}

function showAddDecisionModal() {
    document.getElementById('add-decision-modal').classList.add('active');
}

function hideAddDecisionModal() {
    document.getElementById('add-decision-modal').classList.remove('active');
}

async function addDecisionSubmit(event) {
    event.preventDefault();
    
    const decision = document.getElementById('decision-text').value;
    const rationale = document.getElementById('decision-rationale').value;
    
    try {
        await addDecision(decision, rationale);
        hideAddDecisionModal();
        document.getElementById('decision-text').value = '';
        document.getElementById('decision-rationale').value = '';
        loadDecisions();
    } catch (error) {
        console.error('Failed to add decision:', error);
        alert('Failed to add decision');
    }
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
