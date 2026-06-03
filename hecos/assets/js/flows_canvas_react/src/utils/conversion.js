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
 * flowObj (parsed YAML) → { nodes: RF[], edges: RF[] }
 */
export function flowToRFNodes(flowObj) {
  if (!flowObj || !Array.isArray(flowObj.pipeline)) return { nodes: [], edges: [] };

  const steps = flowObj.pipeline;
  const cols = 3;
  const xGap = 280;
  const yGap = 150;

  const rfNodes = steps.map((step, i) => {
    const nodeType = getNodeTypeFromAction(step.action);
    return {
      id: step.id,
      type: nodeType,
      position: { x: 60 + (i % cols) * xGap, y: 60 + Math.floor(i / cols) * yGap },
      data: {
        stepId: step.id,
        action: step.action || '',
        params: step.params || {},
        outputAs: step.output_as || '',
        dependsOn: step.depends_on || [],
        note: step.note || '',
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

  return { nodes: rfNodes, edges: rfEdges };
}

/**
 * ReactFlow nodes + edges → Hecos flow pipeline array
 */
export function rfNodesToFlow(rfNodes, rfEdges) {
  if (!rfNodes?.length) return { pipeline: [] };

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

  const pipeline = sorted.map(node => {
    const d = node.data || {};
    const step = {
      id: node.id,
      action: d.action || 'LOGIC__delay',
    };
    if (d.params && Object.keys(d.params).length) step.params = d.params;
    if (d.outputAs) step.output_as = d.outputAs;
    if (d.note) step.note = d.note;

    const deps = incomingMap[node.id] || [];
    if (deps.length) step.depends_on = deps;

    return step;
  });

  return { pipeline };
}
