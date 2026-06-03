/**
 * flows_canvas_shim.js
 * ====================
 * Drop-in replacement for the old flows_canvas.js (LiteGraph-based).
 *
 * Exposes the SAME global function API that flows_api.js, flows_editor.js
 * and flows_logs.js already call — but internally delegates to the
 * ReactFlow bridge (window.HecosFlowsBridge) that is mounted by the
 * React bundle.
 *
 * Function parity with old flows_canvas.js:
 *   initCanvas()                 → no-op (React self-initialises)
 *   renderCanvasFromFlow(flow)   → bridge.renderCanvasFromFlow
 *   syncCanvasToYaml()           → bridge.exportFlowFromCanvas → js-yaml dump
 *   setNodeState(id, state)      → bridge.setNodeState
 *   resetNodeStates()            → bridge.resetNodeStates
 *   deleteSelectedNodes()        → bridge.deleteSelectedNodes
 *   resizeCanvas()               → no-op (React handles resize)
 */

// ── Wait for bridge to be ready ───────────────────────────────────────────────
function _withBridge(fn) {
  if (window.HecosFlowsBridge?._api) {
    fn(window.HecosFlowsBridge);
  } else {
    // Retry up to 3 s, React bundle may still be loading
    let tries = 0;
    const iv = setInterval(() => {
      if (window.HecosFlowsBridge?._api) {
        clearInterval(iv);
        fn(window.HecosFlowsBridge);
      } else if (++tries > 30) {
        clearInterval(iv);
        console.warn('[FlowsShim] ReactFlow bridge not ready after 3s');
      }
    }, 100);
  }
}

// ── No-op stubs for functions that LiteGraph had but React handles internally ─
function initCanvas() {}
function resizeCanvas() {}

// ── Main API ──────────────────────────────────────────────────────────────────

function renderCanvasFromFlow(flowObj) {
  _withBridge(b => b.renderCanvasFromFlow(flowObj));
  // Also render timeline (unchanged)
  if (typeof renderTimeline === 'function') renderTimeline(flowObj);
}

function syncCanvasToYaml() {
  _withBridge(b => {
    const flowObj = b.exportFlowFromCanvas();
    if (!flowObj || !cmEditor || typeof jsyaml === 'undefined') return;

    // Preserve existing top-level YAML keys (name, id, trigger, variables, etc.)
    let existing = {};
    try { existing = jsyaml.load(cmEditor.getValue()) || {}; } catch(e) {}

    const merged = { ...existing, ...flowObj };
    if (!merged.id && typeof currentFlowId !== 'undefined' && currentFlowId) {
      merged.id = currentFlowId;
    }

    const newYaml = jsyaml.dump(merged, { indent: 2, lineWidth: -1 });
    const scrollInfo = cmEditor.getScrollInfo();
    cmEditor.setValue(newYaml);
    cmEditor.scrollTo(scrollInfo.left, scrollInfo.top);
  });
}

function setNodeState(stepId, state) {
  _withBridge(b => b.setNodeState(stepId, state));
}

function resetNodeStates() {
  _withBridge(b => b.resetNodeStates());
}

function deleteSelectedNodes() {
  _withBridge(b => b.deleteSelectedNodes());
}

// ── Wire YAML editor → canvas sync ───────────────────────────────────────────
// Called once the React bundle is ready; wires up onGraphChange
// so that canvas changes automatically update the YAML CodeMirror editor.
function _initBridgeSync() {
  if (!window.HecosFlowsBridge) return;
  window.HecosFlowsBridge.onGraphChange = (flowObj) => {
    if (!cmEditor || typeof jsyaml === 'undefined') return;
    let existing = {};
    try { existing = jsyaml.load(cmEditor.getValue()) || {}; } catch(e) {}
    const merged = { ...existing, ...flowObj };
    if (!merged.id && typeof currentFlowId !== 'undefined' && currentFlowId) {
      merged.id = currentFlowId;
    }
    const newYaml = jsyaml.dump(merged, { indent: 2, lineWidth: -1 });
    const scrollInfo = cmEditor.getScrollInfo();
    cmEditor.setValue(newYaml);
    cmEditor.scrollTo(scrollInfo.left, scrollInfo.top);
    if (typeof validateYaml === 'function') validateYaml(newYaml);
  };
}

// Try immediately and on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  // Give the React bundle a moment to mount
  setTimeout(_initBridgeSync, 500);
});

// Legacy timeline renderer ── kept for the Timeline tab (unchanged)
function renderTimeline(flow) {
  const empty = document.getElementById('timeline-empty');
  const steps = document.getElementById('timeline-steps');
  if (!empty || !steps) return;

  if (!flow || !flow.pipeline?.length) {
    empty.style.display = 'flex'; steps.style.display = 'none'; return;
  }
  empty.style.display = 'none'; steps.style.display = 'flex';
  steps.innerHTML = flow.pipeline.map((step, index) => {
    const action = step.action || '';
    let cls = 'action', icon = 'fa-bolt';
    if (action.startsWith('TRIGGER__')) { cls = 'trigger'; icon = 'fa-clock'; }
    else if (action.startsWith('LOGIC__')) { cls = 'logic'; icon = 'fa-code-branch'; }
    else if (action.startsWith('AI__')) { cls = 'ai'; icon = 'fa-magic'; }
    const paramsStr = Object.entries(step.params || {}).slice(0, 3)
      .map(([k, v]) => `${k}: ${typeof v === 'string' ? v : JSON.stringify(v)}`).join(' · ');
    const isLast = index === flow.pipeline.length - 1;
    const arrow = isLast ? '' : `<div class="tl-arrow"><i class="fas fa-arrow-down"></i></div>`;
    return `
      <div class="tl-step-wrapper">
        <div class="tl-step">
          <div class="tl-num">${index + 1}</div>
          <div class="tl-dot ${cls}"><i class="fas ${icon}"></i></div>
          <div class="tl-info">
            <span class="tl-action">${action}</span>
            <span class="tl-id">id: ${step.id}${step.output_as ? ' → ' + step.output_as : ''}</span>
            ${paramsStr ? `<span class="tl-params">${paramsStr}</span>` : ''}
          </div>
        </div>
        ${arrow}
      </div>`;
  }).join('');
}
