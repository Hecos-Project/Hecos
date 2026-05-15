/**
 * Hecos WebUI - Config Mapper Utilities
 * DOM helpers and shared logic.
 */

function populateSelect(id, options, current) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = '';
  options.forEach(opt => {
    const o = document.createElement('option');
    o.value = opt.value || opt;
    o.textContent = opt.label || opt.value || opt;
    if (o.value === current) o.selected = true;
    el.appendChild(o);
  });
}

function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) el.value = val ?? '';
}

function setCheck(id, val) {
  const el = document.getElementById(id);
  if (el) el.checked = !!val;
}

function getV(id, fallback = '') {
  const el = document.getElementById(id);
  return el ? el.value : fallback;
}

function getC(id, fallback = false) {
  const el = document.getElementById(id);
  return el ? el.checked : fallback;
}

window.HecosTextFilters = {
    populate: function(filters) {
        const container = document.getElementById('custom-filters-container');
        if (!container) return;
        container.innerHTML = '';
        if (Array.isArray(filters)) {
            filters.forEach(f => this.addPlaceholderRow(f.find, f.replace, f.target));
        }
    },
    extract: function() {
        const container = document.getElementById('custom-filters-container');
        if (!container) return [];
        const results = [];
        container.querySelectorAll('.custom-filter-row').forEach(row => {
            const find = row.querySelector('.cf-find').value;
            if (!find) return;
            const replace = row.querySelector('.cf-replace').value || '';
            const target = row.querySelector('.cf-target').value || 'both';
            results.push({ find, replace, target });
        });
        return results;
    },
    removeRow: function(btn) {
        if (!btn || !btn.parentElement) return;
        btn.parentElement.remove();
        if (typeof window.saveConfig === 'function') {
            window.saveConfig(true);
        }
    },
    addPlaceholderRow: function(find = '', replace = '', target = 'both') {
        const container = document.getElementById('custom-filters-container');
        if (!container) return;
        const div = document.createElement('div');
        div.className = 'custom-filter-row';
        div.style.display = 'flex';
        div.style.gap = '8px';
        div.style.alignItems = 'center';
        
        div.innerHTML = `
            <input type="text" class="config-input cf-find" placeholder="Find..." value="${find.replace(/"/g, '&quot;')}" style="flex: 2; padding:4px 8px; font-size:12px;">
            <input type="text" class="config-input cf-replace" placeholder="Replace..." value="${replace.replace(/"/g, '&quot;')}" style="flex: 2; padding:4px 8px; font-size:12px;">
            <select class="config-input cf-target" style="flex: 1.5; padding:4px 8px; font-size:12px;">
                <option value="both" ${target === 'both' ? 'selected' : ''}>Voice & Text</option>
                <option value="voice" ${target === 'voice' ? 'selected' : ''}>Voice Only</option>
                <option value="text" ${target === 'text' ? 'selected' : ''}>Text Only</option>
            </select>
            <button type="button" class="btn" onclick="HecosTextFilters.removeRow(this)" style="padding: 4px 8px; font-size: 10px; background: rgba(255,50,50,0.2); color:#ff5555;">X</button>
        `;
        container.appendChild(div);
    }
};

window.populateSelect = populateSelect;
window.setVal = setVal;
window.setCheck = setCheck;
window.getV = getV;
window.getC = getC;
