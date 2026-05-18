/**
 * config_mapper_utils.js
 * DOM helper utilities shared by all config_mapper sub-modules.
 * Must be loaded FIRST before any other config_mapper_*.js file.
 */

const RESTART_FIELDS = [
  'sys-https-enabled'
];

/**
 * Utility to populate a <select> element from a list or object.
 */
function populateSelect(id, list, currentValue, isFilenameOnly = false) {
  const el = document.getElementById(id);
  if (!el) return;

  el.innerHTML = '';

  let items = list;
  if (list && typeof list === 'object' && !Array.isArray(list)) {
      items = Object.entries(list).map(([k, v]) => ({
          id: v,
          name: k.match(/^\d+$/) ? String(v).replace('.yaml', '') : k
      }));
  }

  if (!items || (Array.isArray(items) && items.length === 0)) {
    if (typeof isInitialLoading !== 'undefined' && isInitialLoading) {
      const opt = document.createElement('option');
      opt.textContent = "Loading...";
      opt.disabled = true;
      el.appendChild(opt);
    }
    return;
  }

  let cleanValue = currentValue;
  if (isFilenameOnly && currentValue && (currentValue.includes('\\') || currentValue.includes('/'))) {
    cleanValue = currentValue.split(/[\\/]/).pop();
  }

  const itemsArr = Array.isArray(items) ? items : [items];
  itemsArr.forEach(item => {
    const opt = document.createElement('option');
    let val, text;
    if (typeof item === 'object' && item !== null) {
        val = item.id || item.value || '';
        text = item.name || item.text || val;
    } else {
        val = item;
        text = item;
    }

    const shortText = (isFilenameOnly && (text.includes('\\') || text.includes('/'))) ? text.split(/[\\/]/).pop() : text;
    const shortVal  = (isFilenameOnly && (val.includes('\\')  || val.includes('/')))  ? val.split(/[\\/]/).pop()  : val;

    opt.value = val;
    opt.textContent = shortText;

    if (cleanValue) {
        if (val === cleanValue || shortVal === cleanValue ||
            val.toLowerCase() === cleanValue.toLowerCase() ||
            shortVal.toLowerCase() === cleanValue.toLowerCase()) {
            opt.selected = true;
        }
    }
    el.appendChild(opt);
  });

  if (cleanValue && !el.value) {
      for (let i = 0; i < el.options.length; i++) {
          if (el.options[i].value.toLowerCase().includes(cleanValue.toLowerCase().replace('.yaml',''))) {
              el.selectedIndex = i;
              break;
          }
      }
  }
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

function isRestartNeeded() {
  return document.querySelectorAll('.restart-badge.visible').length > 0;
}

function initRestartIndicators() {
  console.log("[CONFIG] Initializing Restart Indicators for:", RESTART_FIELDS);
  RESTART_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (!el) {
      console.warn("[CONFIG] Element not found for restart indicator:", id);
      return;
    }

    let badge = document.getElementById('badge-' + id);
    if (!badge) {
      badge = document.createElement('span');
      badge.id = 'badge-' + id;
      badge.className = 'restart-badge';
      badge.textContent = 'Restart Required';

      const parentField  = el.closest('.field');
      const parentToggle = el.closest('.toggle-row');

      if (parentField) {
        const label = parentField.querySelector('label');
        if (label) label.appendChild(badge);
        else parentField.appendChild(badge);
      } else if (parentToggle) {
        const info = parentToggle.querySelector('.toggle-info');
        if (info) info.appendChild(badge);
        else parentToggle.appendChild(badge);
      } else {
        el.parentElement.appendChild(badge);
      }
    }

    const initialValue = el.type === 'checkbox' ? el.checked : el.value;
    const check = () => {
      const current = el.type === 'checkbox' ? el.checked : el.value;
      badge.classList.toggle('visible', current !== initialValue);
    };
    el.addEventListener('change', check);
    el.addEventListener('input', check);
  });
}

// Global exports
window.populateSelect = populateSelect;
window.setVal         = setVal;
window.setCheck       = setCheck;
window.getV           = getV;
window.getC           = getC;
window.isRestartNeeded    = isRestartNeeded;
window.initRestartIndicators = initRestartIndicators;
