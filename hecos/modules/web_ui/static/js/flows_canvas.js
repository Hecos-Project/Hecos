// ── Init LiteGraph ────────────────────────────────────────────────
function initCanvas() {
  lgraph = new LGraph();
  lgcanvas = new LGraphCanvas('#flows-canvas', lgraph);
  lgcanvas.background_image = null;
  lgcanvas.render_canvas_border = false;
  lgcanvas.render_connections_border = false;
  lgcanvas.default_link_color = '#00d4ff55';

  // Register node types
  _registerNodeTypes();

  // Resize canvas to container
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
  const wrap = document.getElementById('canvas-wrap');
  const cv = document.getElementById('flows-canvas');
  if (!wrap || !cv) return;
  cv.width = wrap.clientWidth;
  cv.height = wrap.clientHeight;
  if (lgcanvas) lgcanvas.resize();
}

// ── Node type definitions ─────────────────────────────────────────
function _registerNodeTypes() {
  const types = [
    { type:'hecos/trigger',  title:'TRIGGER',   color:'#4c1d95', labelColor:'#c4b5fd' },
    { type:'hecos/action',   title:'ACTION',    color:'#0c4a6e', labelColor:'#7dd3fc' },
    { type:'hecos/if_else',  title:'IF / ELSE', color:'#78350f', labelColor:'#fcd34d' },
    { type:'hecos/loop',     title:'LOOP',      color:'#064e3b', labelColor:'#6ee7b7' },
    { type:'hecos/delay',    title:'DELAY',     color:'#1e1b4b', labelColor:'#a5b4fc' },
    { type:'hecos/speak',    title:'SPEAK',     color:'#134e4a', labelColor:'#5eead4' },
    { type:'hecos/http',     title:'HTTP REQ',  color:'#172554', labelColor:'#93c5fd' },
    { type:'hecos/variable', title:'VARIABLE',  color:'#3f3f46', labelColor:'#d4d4d8' },
  ];
  types.forEach(t => {
    function Node() {
      this.addOutput('out', 'flow');
      this.addInput('in', 'flow');
      this.title = t.title;
      this.size = [200, 60];
      this.bgcolor = t.color;
    }
    Node.title = t.title;
    Node.title_color = t.labelColor || '#fff';
    LiteGraph.registerNodeType(t.type, Node);
  });
}

// ── Canvas renderer ───────────────────────────────────────────────
function renderCanvasFromFlow(flow) {
  if (!lgraph) return;
  lgraph.clear();
  const steps = flow.pipeline || [];
  const posMap = {};
  let x = 80, y = 80;
  
  steps.forEach((step, i) => {
    const action = step.action || '';
    let nodeType = 'hecos/action';
    if (action.startsWith('LOGIC__if')) nodeType = 'hecos/if_else';
    else if (action.startsWith('LOGIC__loop')) nodeType = 'hecos/loop';
    else if (action.startsWith('LOGIC__delay')) nodeType = 'hecos/delay';
    else if (action.startsWith('LOGIC__set_var')) nodeType = 'hecos/variable';
    else if (action.startsWith('AUDIO__speak')) nodeType = 'hecos/speak';
    else if (action.startsWith('LOGIC__http')) nodeType = 'hecos/http';
    else if (action.startsWith('TRIGGER__')) nodeType = 'hecos/trigger';

    const node = LiteGraph.createNode(nodeType);
    node.title = step.id;
    node.pos = [x + (i % 3) * 250, y + Math.floor(i/3) * 120];
    node.properties = { action, params: JSON.stringify(step.params||{}), output_as: step.output_as||'' };
    posMap[step.id] = node;
    lgraph.add(node);
  });

  // Wire depends_on connections
  steps.forEach(step => {
    const deps = step.depends_on || [];
    deps.forEach(dep => {
      const src = posMap[dep];
      const dst = posMap[step.id];
      if (src && dst) src.connect(0, dst, 0);
    });
  });

  if (lgcanvas) lgcanvas.draw(true, true);
}

// ── Timeline renderer ─────────────────────────────────────────────
function renderTimeline(flow) {
  const empty = document.getElementById('timeline-empty');
  const steps = document.getElementById('timeline-steps');
  if (!empty || !steps) return;
  
  if (!flow || !flow.pipeline?.length) {
    empty.style.display='flex'; steps.style.display='none'; return;
  }
  empty.style.display='none'; steps.style.display='flex';
  steps.innerHTML = flow.pipeline.map(step => {
    const action = step.action||'';
    let cls = 'action', icon = 'fa-bolt';
    if (action.startsWith('TRIGGER__')) { cls='trigger'; icon='fa-clock'; }
    else if (action.startsWith('LOGIC__')) { cls='logic'; icon='fa-code-branch'; }
    const paramsStr = Object.entries(step.params||{}).slice(0,3)
      .map(([k,v])=>`${k}: ${typeof v==='string'?v:JSON.stringify(v)}`).join(' · ');
    return `
      <div class="tl-step">
        <div class="tl-dot ${cls}"><i class="fas ${icon}"></i></div>
        <div class="tl-info">
          <span class="tl-action">${action}</span>
          <span class="tl-id">id: ${step.id}${step.output_as?' → '+step.output_as:''}</span>
          ${paramsStr ? `<span class="tl-params">${paramsStr}</span>` : ''}
        </div>
      </div>`;
  }).join('');
}
