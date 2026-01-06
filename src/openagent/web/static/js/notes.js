// Notes page logic
document.addEventListener('DOMContentLoaded', loadNotes);

async function loadNotes() {
    try {
        const notes = await getNotes();
        renderNotes(notes);
    } catch (error) {
        console.error('Failed to load notes:', error);
        document.getElementById('notes-list').innerHTML = '<p class="loading">Error loading notes</p>';
    }
}

function renderNotes(notes) {
    const container = document.getElementById('notes-list');
    
    if (!notes || notes.length === 0) {
        container.innerHTML = '<p>No notes yet. Add one to get started!</p>';
        return;
    }

    container.innerHTML = notes.map(note => `
        <div class="list-item">
            <div class="list-item-header">
                <span class="list-item-title">${escapeHtml(note.content.substring(0, 50))}${note.content.length > 50 ? '...' : ''}</span>
                <span class="list-item-meta">${formatDate(note.created_at)}${note.section ? ` • ${escapeHtml(note.section)}` : ''}</span>
            </div>
            <div class="list-item-content">${escapeHtml(note.content)}</div>
        </div>
    `).join('');
}

function showAddNoteModal() {
    document.getElementById('add-note-modal').classList.add('active');
}

function hideAddNoteModal() {
    document.getElementById('add-note-modal').classList.remove('active');
}

async function addNoteSubmit(event) {
    event.preventDefault();
    
    const content = document.getElementById('note-content').value;
    const section = document.getElementById('note-section').value || null;
    
    try {
        await addNote(content, section);
        hideAddNoteModal();
        document.getElementById('note-content').value = '';
        document.getElementById('note-section').value = '';
        loadNotes();
    } catch (error) {
        console.error('Failed to add note:', error);
        alert('Failed to add note');
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
