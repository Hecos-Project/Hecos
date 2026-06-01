// ── Node Palette ─────────────────────────────────────────────────────────────
// flows_palette.js — draggable toolbox for creating canvas nodes from catalog

const CATEGORY_ICONS = {
  AUDIO: 'fa-volume-up',       LOGIC: 'fa-code-branch',
  TRIGGER: 'fa-clock',         MAIL: 'fa-envelope',
  MESSAGING: 'fa-comment',     DATA: 'fa-cloud',
  TIME: 'fa-calendar',         MEDIA: 'fa-photo-video',
  SYSTEM: 'fa-terminal',       BROWSER: 'fa-globe',
  VISION: 'fa-camera',         MEMORY: 'fa-brain',
  AUTOMATION: 'fa-robot',      PLUGINS: 'fa-plug',
  AI: 'fa-magic',              GENERAL: 'fa-bolt',
};

const CATEGORY_NODE_TYPE = {
  AUDIO: 'hecos/speak', LOGIC: 'hecos/if_else', TRIGGER: 'hecos/trigger',
  TIME: 'hecos/delay',  SYSTEM: 'hecos/action', GENERAL: 'hecos/action',
};

let _paletteLoaded = false;
let _paletteCatalog = null;
let _paletteOpen = false;
let _paletteDrag = { x: 0, y: 0, ox: 0, oy: 0, active: false };

// ── Public API ────────────────────────────────────────────────────────────────

async function initPalette() {
  if (_paletteLoaded) return;
  try {
    const res = await fetch('/api/flows/actions/catalog');
    const d = await res.json();
    if (!d.ok) return;
    _paletteCatalog = d.catalog;
    _renderPalette(d.catalog);
    _bindCanvasDrop();
    _paletteLoaded = true;
  } catch (e) { console.error('[Palette] Load error:', e); }
}

function togglePalette() {
  const panel = document.getElementById('palette-panel');
  if (!panel) return;
  _paletteOpen = !_paletteOpen;
  panel.style.display = _paletteOpen ? 'flex' : 'none';
  const btn = document.getElementById('btn-palette');
  if (btn) btn.classList.toggle('active', _paletteOpen);

  if (_paletteOpen && !_paletteLoaded) initPalette();
}

// ── Render ────────────────────────────────────────────────────────────────────

function _renderPalette(catalog) {
  const body = document.getElementById('palette-body');
  if (!body) return;
  body.innerHTML = '';

  const sorted = Object.entries(catalog).sort(([a], [b]) => a.localeCompare(b));
  for (const [cat, actions] of sorted) {
    const icon = CATEGORY_ICONS[cat] || 'fa-bolt';
    const section = document.createElement('div');
    section.className = 'pal-section';
    section.innerHTML = `
      <div class="pal-cat" onclick="this.parentElement.classList.toggle('collapsed')">
        <i class="fas ${icon}"></i> ${cat}
        <i class="fas fa-chevron-down pal-chevron"></i>
      </div>
      <div class="pal-items">
        ${actions.map(a => `
          <div class="pal-item" draggable="true"
            data-action="${a.name}"
            data-icon="${a.icon || '⚡'}"
            data-desc="${(a.description || '').slice(0, 80)}"
            title="${a.description || a.name}"
            ondragstart="_onPaletteDragStart(event, '${a.name}')">
            <span class="pal-item-icon">${a.icon || '⚡'}</span>
            <span class="pal-item-name">${a.name.replace(/^[^_]+__/, '')}</span>
          </div>
        `).join('')}
      </div>`;
    body.appendChild(section);
  }
}

// ── Drag & Drop ───────────────────────────────────────────────────────────────

function _onPaletteDragStart(e, actionName) {
  e.dataTransfer.setData('text/plain', actionName);
  e.dataTransfer.effectAllowed = 'copy';
}

function _bindCanvasDrop() {
  const wrap = document.getElementById('canvas-wrap');
  if (!wrap) return;

  wrap.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
  wrap.addEventListener('drop', e => {
    e.preventDefault();
    const actionName = e.dataTransfer.getData('text/plain');
    if (!actionName || !lgcanvas || !lgraph) return;

    // Convert screen coords to LiteGraph canvas coords
    const rect = wrap.getBoundingClientRect();
    const canvasX = (e.clientX - rect.left - lgcanvas.ds.offset[0]) / lgcanvas.ds.scale;
    const canvasY = (e.clientY - rect.top  - lgcanvas.ds.offset[1]) / lgcanvas.ds.scale;

    _createNodeFromAction(actionName, canvasX, canvasY);
  });
}

function _createNodeFromAction(actionName, x, y) {
  if (!lgraph || typeof LiteGraph === 'undefined') return;

  // Pick a suitable node type from the category prefix
  const prefix = actionName.split('__')[0];
  const nodeType = CATEGORY_NODE_TYPE[prefix] || 'hecos/action';
  const node = LiteGraph.createNode(nodeType);
  if (!node) return;

  // Give it a clean, incrementing ID as title
  const baseName = actionName.replace(/[^a-z0-9_]/gi, '_').toLowerCase();
  let count = 1;
  let stepId = `${baseName}_${count}`;
  while (lgraph._nodes.some(n => n.title === stepId)) {
    count++;
    stepId = `${baseName}_${count}`;
  }
  
  node.title = stepId;
  // Look up action definition to generate a starting boilerplate for parameters
  let defaultParams = {};
  if (_paletteCatalog) {
    for (const cat of Object.keys(_paletteCatalog)) {
      const act = _paletteCatalog[cat].find(a => a.name === actionName);
      if (act && act.params) {
        for (const [key, typeDesc] of Object.entries(act.params)) {
          const lowerType = String(typeDesc).toLowerCase();
          if (lowerType.includes('number') || lowerType.includes('integer') || lowerType.includes('seconds')) {
            defaultParams[key] = 0;
          } else if (lowerType.includes('dict')) {
            defaultParams[key] = {};
          } else if (lowerType.includes('list')) {
            defaultParams[key] = [];
          } else {
            defaultParams[key] = `<${typeDesc.split(' ')[0]}>`;
          }
        }
        break;
      }
    }
  }

  node.properties = {
    action: actionName,
    params: Object.keys(defaultParams).length > 0 ? JSON.stringify(defaultParams) : '{}',
    output_as: '',
    depends_on: '',
  };

  lgraph.add(node);

  // Expose to node map so state tracking works
  _nodeMap[stepId] = node;
  _nodeOrigColors[stepId] = { color: node.color, bgcolor: node.bgcolor };

  lgcanvas.draw(true, true);
  if (typeof syncCanvasToYaml === 'function') syncCanvasToYaml();

  if (typeof toast === 'function') toast('ok', `Node added: ${actionName}`);
}

// ── Panel drag-to-move ────────────────────────────────────────────────────────

function _initPanelDrag() {
  const panel  = document.getElementById('palette-panel');
  const header = document.getElementById('palette-header');
  if (!panel || !header) return;

  header.addEventListener('mousedown', e => {
    _paletteDrag.active = true;
    _paletteDrag.ox = e.clientX - panel.offsetLeft;
    _paletteDrag.oy = e.clientY - panel.offsetTop;
    document.body.style.userSelect = 'none';
  });
  document.addEventListener('mousemove', e => {
    if (!_paletteDrag.active) return;
    panel.style.left = (e.clientX - _paletteDrag.ox) + 'px';
    panel.style.top  = (e.clientY - _paletteDrag.oy) + 'px';
    panel.style.right = 'auto';
  });
  document.addEventListener('mouseup', () => {
    _paletteDrag.active = false;
    document.body.style.userSelect = '';
  });
}

document.addEventListener('DOMContentLoaded', _initPanelDrag);

// ── Search filter ─────────────────────────────────────────────────────────────

function _filterPalette(query) {
  const q = query.toLowerCase().trim();
  const sections = document.querySelectorAll('#palette-body .pal-section');
  sections.forEach(section => {
    const items = section.querySelectorAll('.pal-item');
    let visible = 0;
    items.forEach(item => {
      const match = !q || item.dataset.action.toLowerCase().includes(q) || (item.dataset.desc || '').toLowerCase().includes(q);
      item.classList.toggle('hidden', !match);
      if (match) visible++;
    });
    // Auto-expand sections with matches, collapse empty ones
    section.classList.toggle('collapsed', visible === 0 && q.length > 0);
    if (q.length > 0 && visible > 0) section.classList.remove('collapsed');
  });
}
