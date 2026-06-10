/**
 * Conversion utilities: Hecos flow YAML dict ↔ ReactFlow nodes/edges
 */
import { MarkerType } from '@xyflow/react';
import { getNodeTypeFromAction } from '../nodes/nodeTypeMap.js';

const EDGE_STYLE = {
  type: 'smoothstep',
  animated: false,
  style: { stroke: 'rgba(0,212,255,0.35)', strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(0,212,255,0.5)' },
};

/**
 * Compute an auto-layout grid position for index i.
 */
export function autoPosition(i, cols = 3, xGap = 280, yGap = 150) {
  return { x: 60 + (i % cols) * xGap, y: 60 + Math.floor(i / cols) * yGap };
}

/**
 * Re-apply auto-layout to a list of (non-area) RF nodes.
 * Returns a new array with recalculated positions.
 */
export function autoLayoutNodes(rfNodes) {
  let i = 0;
  return rfNodes.map(n => {
    if (n.type === 'areaNode') return n; // keep areas where they are
    return { ...n, position: autoPosition(i++) };
  });
}

/**
 * flowObj (parsed YAML) → { nodes: RF[], edges: RF[] }
 */
export function flowToRFNodes(flowObj) {
  if (!flowObj) return { nodes: [], edges: [] };

  const steps = Array.isArray(flowObj.pipeline) ? flowObj.pipeline : [];
  const flowAreas = Array.isArray(flowObj.areas) ? flowObj.areas : [];

  const rfNodes = steps.map((step, i) => {
    const nodeType = getNodeTypeFromAction(step.action);
    // Use saved position from YAML if available, otherwise fall back to grid
    const position = (step.position && typeof step.position.x === 'number')
      ? { x: step.position.x, y: step.position.y }
      : autoPosition(i);
    return {
      id: step.id,
      type: nodeType,
      position,
      data: {
        stepId: step.id,
        action: step.action || '',
        params: step.params || {},
        outputAs: step.output_as || '',
        dependsOn: step.depends_on || [],
        note: step.note || '',
        disabled: step.disabled === true,
        execState: null,
      },
    };
  });

  // Build edges from depends_on
  const rfEdges = [];
  steps.forEach(step => {
    (step.depends_on || []).forEach((dep, idx) => {
      rfEdges.push({
        id: `${dep}→${step.id}`,
        source: dep,
        target: step.id,
        ...EDGE_STYLE,
      });
    });
  });

  // Build area nodes
  flowAreas.forEach((area, i) => {
    rfNodes.push({
      id: area.id || `area_${i}`,
      type: 'areaNode',
      position: area.position || { x: 0, y: 0 },
      data: {
        areaId: area.id || `area_${i}`,
        title: area.title || '',
        description: area.description || '',
        color: area.color || '#1a1a2e',
        backgroundImage: area.backgroundImage || '',
        width: area.width || 400,
        height: area.height || 400
      },
      style: { width: area.width || 400, height: area.height || 400, zIndex: -1 }
    });
  });

  return { nodes: rfNodes, edges: rfEdges };
}

/**
 * ReactFlow nodes + edges → Hecos flow pipeline array
 */
export function rfNodesToFlow(rfNodes, rfEdges) {
  if (!rfNodes?.length) return { pipeline: [], areas: [] };

  // Build adjacency: target → [source] from edges
  const incomingMap = {};
  (rfEdges || []).forEach(e => {
    if (!incomingMap[e.target]) incomingMap[e.target] = [];
    incomingMap[e.target].push(e.source);
  });

  // Sort nodes by Y then X for a readable YAML order
  const sorted = [...rfNodes].sort((a, b) => {
    const dy = a.position.y - b.position.y;
    if (Math.abs(dy) > 80) return dy;
    return a.position.x - b.position.x;
  });

  const pipeline = [];
  const areas = [];

  sorted.forEach(node => {
    if (node.type === 'areaNode') {
      const d = node.data || {};
      areas.push({
        id: node.id,
        title: d.title || '',
        description: d.description || '',
        color: d.color || '#1a1a2e',
        backgroundImage: d.backgroundImage || '',
        position: { x: Math.round(node.position.x), y: Math.round(node.position.y) },
        width: Math.round(node.width || d.width || node.style?.width || 400),
        height: Math.round(node.height || d.height || node.style?.height || 400)
      });
      return;
    }

    const d = node.data || {};
    const step = {
      id: node.id,
      action: d.action || 'LOGIC__delay',
      // Always persist the current canvas position in the YAML
      position: { x: Math.round(node.position.x), y: Math.round(node.position.y) },
    };
    if (d.params && Object.keys(d.params).length) step.params = d.params;
    if (d.outputAs) step.output_as = d.outputAs;
    if (d.note) step.note = d.note;
    if (d.disabled) step.disabled = true;

    const deps = incomingMap[node.id] || [];
    if (deps.length) step.depends_on = deps;

    pipeline.push(step);
  });

  return { pipeline, areas };
}
