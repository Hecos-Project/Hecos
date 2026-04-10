/**
 * Zentra Core WebUI - Routing Configuration Logic
 * Handles dynamic key-value pairs for routing overrides.
 */

window.routingOverrides = {};

async function loadRoutingOverrides() {
  try {
    const res = await fetch('/zentra/config/routing');
    if (res.ok) {
      window.routingOverrides = await res.json();
      renderRoutingOverrides();
    }
  } catch (e) {
    console.error("Error loading routing overrides:", e);
  }
}

function renderRoutingOverrides() {
  const container = document.getElementById('routing-overrides-list');
  if (!container) return;
  
  container.innerHTML = '';
  
  const entries = Object.entries(window.routingOverrides);
  if (entries.length === 0) {
    container.innerHTML = '<div class="muted" style="padding:10px; font-size:12px;">Nessun override personalizzato definito.</div>';
    return;
  }
  
  entries.forEach(([tag, instruction]) => {
    const row = document.createElement('div');
    row.className = 'override-row';
    row.style.display = 'flex';
    row.style.gap = '10px';
    row.style.marginBottom = '10px';
    row.style.alignItems = 'flex-start';
    
    row.innerHTML = `
      <div style="flex: 0 0 120px;">
        <input type="text" value="${tag}" class="override-tag" style="width:100%; text-transform:uppercase; font-weight:bold; color:var(--cyan);" onchange="updateOverrideKey('${tag}', this.value)">
      </div>
      <div style="flex: 1;">
        <textarea class="override-instr" style="width:100%; min-height:40px; resize:vertical;" onchange="updateOverrideValue('${tag}', this.value)">${instruction}</textarea>
      </div>
      <button type="button" class="btn btn-secondary" style="padding:4px 8px; color:var(--red);" onclick="deleteOverride('${tag}')">×</button>
    `;
    container.appendChild(row);
  });
}

function updateOverrideKey(oldKey, newKey) {
  newKey = newKey.toUpperCase().trim();
  if (newKey === oldKey) return;
  if (!newKey) { renderRoutingOverrides(); return; }
  
  const val = window.routingOverrides[oldKey];
  delete window.routingOverrides[oldKey];
  window.routingOverrides[newKey] = val;
  renderRoutingOverrides();
}

function updateOverrideValue(key, newVal) {
  window.routingOverrides[key] = newVal;
}

function addOverride() {
  const newTag = "NEW_TAG_" + Date.now();
  window.routingOverrides[newTag] = "";
  renderRoutingOverrides();
  // Focus the new input if possible
  setTimeout(() => {
    const inputs = document.querySelectorAll('.override-tag');
    if (inputs.length) inputs[inputs.length - 1].focus();
  }, 50);
}

function deleteOverride(key) {
  delete window.routingOverrides[key];
  renderRoutingOverrides();
}

async function saveRoutingOverrides() {
  setSaveMsg('Saving overrides...', 'muted');
  try {
    const res = await fetch('/zentra/config/routing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(window.routingOverrides)
    });
    if (res.ok) {
        setSaveMsg('Overrides saved!', 'ok');
    } else {
        setSaveMsg('Error saving overrides.', 'err');
    }
  } catch (e) {
    setSaveMsg('Network error: ' + e, 'err');
  }
}

// Hook into the main initAll
const originalInitAll = window.initAll;
window.initAll = async function() {
  if (originalInitAll) await originalInitAll();
  await loadRoutingOverrides();
};

window.addOverride = addOverride;
window.deleteOverride = deleteOverride;
window.saveRoutingOverrides = saveRoutingOverrides;
window.updateOverrideKey = updateOverrideKey;
window.updateOverrideValue = updateOverrideValue;
