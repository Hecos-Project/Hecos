import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Panel,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import './styles/flow.css';

import bridge from './bridge.js';
import { nodeTypes } from './nodes/index.jsx';
import NodePalette from './components/NodePalette.jsx';
import NodeEditPanel from './components/NodeEditPanel.jsx';
import { catalogToNodes, flowToRFNodes, rfNodesToFlow } from './utils/conversion.js';
import { ACTION_TYPE_MAP } from './nodes/nodeTypeMap.js';

const DEFAULT_EDGE_OPTIONS = {
  type: 'smoothstep',
  animated: false,
  style: { stroke: 'rgba(0,212,255,0.35)', strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(0,212,255,0.5)' },
};

export default function FlowsApp() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [editNode, setEditNode] = useState(null);   // node being edited
  const [catalog, setCatalog] = useState({});
  const reactFlowWrapper = useRef(null);
  const [rfInstance, setRfInstance] = useState(null);
  // Execution states: stepId -> 'running'|'done'|'error'
  const execStateRef = useRef({});

  // ── Load catalog ──────────────────────────────────────────────────────────
  useEffect(() => {
    fetch('/api/flows/actions/catalog')
      .then(r => r.json())
      .then(d => { if (d.ok) setCatalog(d.catalog); })
      .catch(() => {});
  }, []);

  // ── Export flow from canvas ───────────────────────────────────────────────
  const exportFlow = useCallback(() => {
    return rfNodesToFlow(nodes, edges);
  }, [nodes, edges]);

  // ── Notify YAML editor when graph changes ─────────────────────────────────
  const notifyChange = useCallback((newNodes, newEdges) => {
    const flow = rfNodesToFlow(newNodes !== undefined ? newNodes : nodes,
                               newEdges  !== undefined ? newEdges  : edges);
    bridge._notifyGraphChange(flow);
  }, [nodes, edges]);

  // ── Edge connection ───────────────────────────────────────────────────────
  const onConnect = useCallback((params) => {
    setEdges(eds => {
      const newEdges = addEdge({ ...params, ...DEFAULT_EDGE_OPTIONS }, eds);
      notifyChange(undefined, newEdges);
      return newEdges;
    });
  }, [notifyChange]);

  // ── Node change with YAML sync ────────────────────────────────────────────
  const handleNodesChange = useCallback((changes) => {
    onNodesChange(changes);
    // Defer sync slightly to let state settle
    setTimeout(() => notifyChange(), 50);
  }, [onNodesChange, notifyChange]);

  const handleEdgesChange = useCallback((changes) => {
    onEdgesChange(changes);
    setTimeout(() => notifyChange(), 50);
  }, [onEdgesChange, notifyChange]);

  // ── Drop from palette ─────────────────────────────────────────────────────
  const onDrop = useCallback((event) => {
    event.preventDefault();
    if (!rfInstance || !reactFlowWrapper.current) return;

    const actionName = event.dataTransfer.getData('application/hecos-action');
    if (!actionName) return;

    const rect = reactFlowWrapper.current.getBoundingClientRect();
    const position = rfInstance.screenToFlowPosition({
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    });

    const nodeType = ACTION_TYPE_MAP[actionName.split('__')[0]] || 'actionNode';
    const baseName = actionName.replace(/[^a-z0-9_]/gi, '_').toLowerCase();
    const existingCount = nodes.filter(n => n.data.stepId?.startsWith(baseName)).length;
    const stepId = `${baseName}_${existingCount + 1}`;

    // Build default params from catalog
    let defaultParams = {};
    const catEntry = Object.values(catalog).flat().find(a => a.name === actionName);
    if (catEntry?.params) {
      for (const [key, typeDesc] of Object.entries(catEntry.params)) {
        const t = String(typeDesc).toLowerCase();
        if (t.includes('number') || t.includes('integer') || t.includes('seconds')) defaultParams[key] = 0;
        else if (t.includes('bool')) defaultParams[key] = true;
        else if (t.includes('dict') || t.includes('object')) defaultParams[key] = {};
        else if (t.includes('list')) defaultParams[key] = [];
        else defaultParams[key] = '';
      }
    }

    const newNode = {
      id: stepId,
      type: nodeType,
      position,
      data: {
        stepId,
        action: actionName,
        params: defaultParams,
        outputAs: '',
        dependsOn: [],
        description: catEntry?.description || '',
        icon: catEntry?.icon || '⚡',
      },
    };

    setNodes(nds => {
      const updated = [...nds, newNode];
      notifyChange(updated, undefined);
      return updated;
    });
  }, [rfInstance, reactFlowWrapper, nodes, catalog, notifyChange]);

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  // ── Node double-click → open edit panel ───────────────────────────────────
  const onNodeDoubleClick = useCallback((_, node) => {
    setEditNode(node);
  }, []);

  // ── Save from edit panel ──────────────────────────────────────────────────
  const onSaveNode = useCallback((nodeId, updatedData) => {
    setNodes(nds => {
      const updated = nds.map(n => n.id === nodeId ? { ...n, id: updatedData.stepId, data: updatedData } : n);
      // Also remap edges if stepId changed
      notifyChange(updated, undefined);
      return updated;
    });
    // If stepId changed, update edges
    if (nodeId !== updatedData.stepId) {
      setEdges(eds => eds.map(e => ({
        ...e,
        source: e.source === nodeId ? updatedData.stepId : e.source,
        target: e.target === nodeId ? updatedData.stepId : e.target,
      })));
    }
    setEditNode(null);
  }, [setNodes, setEdges, notifyChange]);

  // ── Delete selected nodes ─────────────────────────────────────────────────
  const deleteSelected = useCallback(() => {
    setNodes(nds => {
      const selectedIds = new Set(nds.filter(n => n.selected).map(n => n.id));
      const updated = nds.filter(n => !selectedIds.has(n.id));
      setEdges(eds => eds.filter(e => !selectedIds.has(e.source) && !selectedIds.has(e.target)));
      notifyChange(updated, undefined);
      return updated;
    });
  }, [setNodes, setEdges, notifyChange]);

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && !['INPUT','TEXTAREA'].includes(document.activeElement?.tagName)) {
        deleteSelected();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [deleteSelected]);

  // ── Wire HecosFlowsBridge ─────────────────────────────────────────────────
  useEffect(() => {
    bridge._api = {
      renderCanvasFromFlow(flowObj) {
        const { nodes: rNodes, edges: rEdges } = flowToRFNodes(flowObj);
        setNodes(rNodes);
        setEdges(rEdges);
        execStateRef.current = {};
      },
      exportFlowFromCanvas: exportFlow,
      setNodeState(stepId, state) {
        execStateRef.current[stepId] = state;
        setNodes(nds => nds.map(n => n.id === stepId
          ? { ...n, data: { ...n.data, execState: state } }
          : n
        ));
      },
      resetNodeStates() {
        execStateRef.current = {};
        setNodes(nds => nds.map(n => ({ ...n, data: { ...n.data, execState: null } })));
      },
      deleteSelectedNodes: deleteSelected,
    };

    // Expose palette toggle for old toolbar button
    window.togglePalette = () => setPaletteOpen(p => !p);

    return () => { bridge._api = null; };
  }, [setNodes, setEdges, exportFlow, deleteSelected]);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div ref={reactFlowWrapper} style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onInit={setRfInstance}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeDoubleClick={onNodeDoubleClick}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={DEFAULT_EDGE_OPTIONS}
        fitView
        proOptions={{ hideAttribution: true }}
        deleteKeyCode={null}  // we handle delete ourselves
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1a1a2e" />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={(n) => {
            const t = n.type || '';
            if (t === 'triggerNode') return '#7c3aed';
            if (t === 'aiNode')      return '#c026d3';
            if (t === 'logicNode')   return '#f59e0b';
            if (t === 'httpNode')    return '#14b8a6';
            if (t === 'delayNode')   return '#818cf8';
            if (t === 'varNode')     return '#22c55e';
            return '#0ea5e9';
          }}
          maskColor="rgba(0,0,0,0.4)"
          style={{ bottom: 50, right: 12 }}
        />

        {/* Empty hint */}
        {nodes.length === 0 && (
          <Panel position="center" style={{ pointerEvents: 'none' }}>
            <div className="rf-empty-hint">
              <i className="fas fa-project-diagram" />
              <p>Select a flow from the sidebar<br />or drag a node from the Palette</p>
            </div>
          </Panel>
        )}
      </ReactFlow>

      {/* Palette */}
      {paletteOpen && (
        <NodePalette
          catalog={catalog}
          onClose={() => setPaletteOpen(false)}
        />
      )}

      {/* Edit panel (slides in from right) */}
      {editNode && (
        <NodeEditPanel
          node={editNode}
          catalog={catalog}
          allNodeIds={nodes.map(n => n.id).filter(id => id !== editNode.id)}
          onSave={onSaveNode}
          onClose={() => setEditNode(null)}
        />
      )}
    </div>
  );
}
