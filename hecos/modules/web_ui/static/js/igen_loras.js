/**
 * image_gen — LoRA UI Logic
 * Handles rendering the LoRA visual cards, filtering, and model compatibility.
 */

window._selectedLoras = new Set();

window.renderLoRAList = function(filterText) {
    var container  = document.getElementById('igen-loras-list');
    var countEl    = document.getElementById('igen-lora-count');
    var lSel       = document.getElementById('igen-loras');
    if (!container) return;

    var allLoras   = window._swarmui_loras_data || [];
    var modelSel   = document.getElementById('igen-model');
    var modelName  = modelSel ? modelSel.value : '';
    var modelCompat = '';
    if (window._swarmui_compat && window._swarmui_compat.models) {
        for (var i=0; i<window._swarmui_compat.models.length; i++) {
            if (window._swarmui_compat.models[i].name === modelName) {
                modelCompat = window._swarmui_compat.models[i].compat_class || '';
                break;
            }
        }
    }

    var filter = (filterText || '').toLowerCase().trim();

    if (!allLoras.length) {
        container.innerHTML = '<div style="padding:20px; text-align:center; color:var(--muted); font-size:12px;">No LoRAs found in SwarmUI.</div>';
        if (countEl) countEl.textContent = '';
        return;
    }

    // Restore selected from hidden select on first render
    if (window._selectedLoras.size === 0 && lSel) {
        Array.from(lSel.selectedOptions).forEach(function(o) {
            window._selectedLoras.add(o.value);
        });
    }

    var html = '';
    var shown = 0, compatCount = 0;

    allLoras.forEach(function(lora) {
        var loraCompat = lora.compat_class || '';
        var isCompatible, dotColor, badgeText, badgeBg;

        if (!modelCompat || !loraCompat) {
            // One side unknown = maybe compatible
            isCompatible = true;
            dotColor  = '#f59e0b';
            badgeBg   = 'rgba(245,158,11,0.15)';
            badgeText = loraCompat || 'General';
        } else if (modelCompat === loraCompat) {
            isCompatible = true;
            dotColor  = '#34d399';
            badgeBg   = 'rgba(52,211,153,0.12)';
            badgeText = loraCompat;
            compatCount++;
        } else {
            isCompatible = false;
            dotColor  = '#e74c3c';
            badgeBg   = 'rgba(231,76,60,0.12)';
            badgeText = loraCompat;
        }

        var name    = lora.name || '';
        var title   = lora.title || name;
        var trigger = lora.trigger_phrase || '';
        // Truncate trigger to ~80 chars for display
        if (trigger.length > 80) trigger = trigger.slice(0, 80) + '...';

        if (filter && name.toLowerCase().indexOf(filter) === -1 && title.toLowerCase().indexOf(filter) === -1) return;
        shown++;

        var isSelected = window._selectedLoras.has(name);
        var classes    = 'igen-lora-card' + (isSelected ? ' selected' : '') + (!isCompatible ? ' incompatible' : '');
        var dataName   = name.replace(/"/g, '&quot;');

        html += '<div class="' + classes + '" '
            + (isCompatible ? 'onclick="window._loraCardClick(event, \'' + dataName.replace(/'/g, "\\'") + '\')"' : 'title="Not compatible with the selected model"')
            + '>';
        html += '<span class="igen-lora-dot" style="background:' + dotColor + ';"></span>';
        html += '<span class="igen-lora-name" title="' + name.replace(/"/g, '&quot;') + '">' + title + '</span>';
        if (trigger) html += '<span class="igen-lora-trigger" title="Trigger: ' + trigger.replace(/"/g, '&quot;') + '">' + trigger + '</span>';
        html += '<span class="igen-lora-badge" style="background:' + badgeBg + '; color:' + dotColor + ';">' + badgeText + '</span>';
        if (!isCompatible) html += '<span style="font-size:10px; color:#e74c3c; white-space:nowrap;">Not for this model</span>';
        html += '<i class="fas fa-check igen-lora-checkmark"></i>';
        html += '</div>';
    });

    container.innerHTML = html || '<div style="padding:12px; text-align:center; color:var(--muted); font-size:12px;">No results.</div>';
    if (countEl) countEl.textContent = shown + '/' + allLoras.length + ' LoRAs';
};

window._loraCardClick = function(evt, name) {
    if (evt.ctrlKey || evt.metaKey) {
        // Multi-select
        if (window._selectedLoras.has(name)) window._selectedLoras.delete(name);
        else window._selectedLoras.add(name);
    } else {
        // Single select (toggle)
        var wasSelected = window._selectedLoras.has(name);
        window._selectedLoras.clear();
        if (!wasSelected) window._selectedLoras.add(name);
    }
    _syncLoraSelectToHidden();
    window.renderLoRAList(document.getElementById('igen-lora-search')?.value);
    if (typeof _igenDebounceSave !== 'undefined') _igenDebounceSave();
};

function _syncLoraSelectToHidden() {
    var lSel = document.getElementById('igen-loras');
    if (!lSel) return;
    Array.from(lSel.options).forEach(function(o) {
        o.selected = window._selectedLoras.has(o.value);
    });
}

window.filterLoRAList = function(text) {
    window.renderLoRAList(text);
};

window.clearLoRASelection = function() {
    window._selectedLoras.clear();
    _syncLoraSelectToHidden();
    window.renderLoRAList(document.getElementById('igen-lora-search')?.value);
    if (typeof _igenDebounceSave !== 'undefined') _igenDebounceSave();
};

window.updateLoRACompatibility = function() {
    // Just re-render — compatibility is computed inside renderLoRAList
    window.renderLoRAList(document.getElementById('igen-lora-search')?.value);
};
