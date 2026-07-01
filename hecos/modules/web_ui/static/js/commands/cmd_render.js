/* cmd_render.js — HDCS Palette DOM Rendering */

export function renderPaletteHTML() {
    if (document.getElementById('cmd-palette-overlay')) return;

    const overlay = document.createElement('div');
    overlay.id = 'cmd-palette-overlay';
    
    overlay.innerHTML = `
        <div id="cmd-palette">
            <div id="cmd-input-container">
                <i class="fas fa-terminal" id="cmd-input-icon"></i>
                <input type="text" id="cmd-input" placeholder="Type a command or search..." autocomplete="off">
            </div>
            <div id="cmd-results"></div>
            <div id="cmd-footer">
                <div class="cmd-keys">
                    <span class="cmd-key-hint"><kbd>↑</kbd><kbd>↓</kbd> Navigate</span>
                    <span class="cmd-key-hint"><kbd>Enter</kbd> Execute</span>
                    <span class="cmd-key-hint"><kbd>Esc</kbd> Close</span>
                </div>
                <div>Hecos Direct Command System</div>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
}

export function renderResults(commands, selectedIndex, container) {
    container.innerHTML = '';
    
    if (commands.length === 0) {
        container.innerHTML = '<div style="padding: 20px; text-align: center; color: #666; font-size: 14px;">No commands found.</div>';
        return;
    }

    commands.forEach((cmd, i) => {
        const isSelected = i === selectedIndex;
        const div = document.createElement('div');
        div.className = `cmd-item ${isSelected ? 'selected' : ''}`;
        div.dataset.index = i;
        
        const catClass = cmd.category === 'CORE' ? 'core' : 'plugin';
        
        // Se c'è un alias che matcha perfettamente, mostralo, altrimenti mostra il primo
        const primaryAlias = cmd.aliases[0];
        
        div.innerHTML = `
            <div class="cmd-item-icon">${(function(ic){ return (ic && !ic.startsWith('fa-') && !ic.startsWith('fas ') && !ic.startsWith('<i ')) ? ic : '⚡'; })(cmd.icon)}</div>
            <div class="cmd-item-content">
                <div class="cmd-item-header">
                    <span class="cmd-item-alias">${primaryAlias}</span>
                    <div class="cmd-item-badges">
                        ${cmd.requires_auth === 'admin' ? '<span class="cmd-badge" style="background:rgba(244,67,54,0.15);color:#f44336">ADMIN</span>' : ''}
                        <span class="cmd-badge ${catClass}">${cmd.category}</span>
                    </div>
                </div>
                <div class="cmd-item-desc">${cmd.description}</div>
                ${isSelected && cmd.usage ? `<div class="cmd-item-usage">Example: ${cmd.example || cmd.usage}</div>` : ''}
            </div>
        `;
        
        container.appendChild(div);
    });

    // Ensure selected item is visible
    const selectedEl = container.querySelector('.selected');
    if (selectedEl) {
        selectedEl.scrollIntoView({ block: 'nearest' });
    }
}
