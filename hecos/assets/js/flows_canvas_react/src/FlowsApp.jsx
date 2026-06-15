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
import AreaEditPanel from './components/AreaEditPanel.jsx';
import ContextMenu from './components/ContextMenu.jsx';
import { flowToRFNodes, rfNodesToFlow, autoLayoutNodes } from './utils/conversion.js';
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
  const [editNode, setEditNode] = useState(null);
  const [catalog, setCatalog] = useState({});
  const reactFlowWrapper = useRef(null);
  const [rfInstance, setRfInstance] = useState(null);
  const [menu, setMenu] = useState(null);
  const execStateRef = useRef({});

  // Keep live refs to current nodes/edges so callbacks always see fresh state
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);
  useEffect(() => { nodesRef.current = nodes; }, [nodes]);
  useEffect(() => { edgesRef.current = edges; }, [edges]);

  // ── Load catalog ──────────────────────────────────────────────────────────
  useEffect(() => {
    fetch('/api/flows/actions/catalog')
      .then(r => r.json())
      .then(d => { if (d.ok) setCatalog(d.catalog); })
      .catch(() => {});
  }, []);

  // ── Export flow from canvas (always reads live state via refs) ────────────
  const exportFlow = useCallback(() => {
    return rfNodesToFlow(nodesRef.current, edgesRef.current);
  }, []);

  // ── notifyChange: tells the bridge (→ CodeMirror) about a graph change ───
  // Only call this AFTER a logical mutation is complete (not during drag frames).
  const notifyTimeoutRef = useRef(null);
  const notifyChange = useCallback((newNodes, newEdges) => {
    if (notifyTimeoutRef.current) clearTimeout(notifyTimeoutRef.current);
    notifyTimeoutRef.current = setTimeout(() => {
      const n = newNodes !== undefined ? newNodes : nodesRef.current;
      const e = newEdges !== undefined ? newEdges  : edgesRef.current;
      const flow = rfNodesToFlow(n, e);
      bridge._notifyGraphChange(flow);
    }, 300);
  }, []);

  // ── Standard ReactFlow change handlers (no sync during drag) ─────────────
  const handleNodesChange = useCallback((changes) => {
    onNodesChange(changes);
  }, [onNodesChange]);

  const handleEdgesChange = useCallback((changes) => {
    onEdgesChange(changes);
  }, [onEdgesChange]);

  // ── Sync positions ONCE when drag ends (single event, not per-frame) ──────
  const onNodeDragStop = useCallback((_event, _node, _draggedNodes) => {
    // _draggedNodes contains ONLY the dragged nodes, not all nodes!
    // Since useNodesState already updates nodes on every drag frame, 
    // nodesRef.current will have the updated positions.
    notifyChange(undefined, undefined);
  }, [notifyChange]);

  // ── Edge connection ───────────────────────────────────────────────────────
  const onConnect = useCallback((params) => {
    setEdges(eds => {
      const newEdges = addEdge({ ...params, ...DEFAULT_EDGE_OPTIONS }, eds);
      notifyChange(undefined, newEdges);
      return newEdges;
    });
  }, [notifyChange]);

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
    const existingCount = nodesRef.current.filter(n => n.data.stepId?.startsWith(baseName)).length;
    const stepId = `${baseName}_${existingCount + 1}`;

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
  }, [rfInstance, reactFlowWrapper, catalog, notifyChange]);

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  // ── Node single-click / double-click ──────────────────────────────────────
  const onNodeClick = useCallback((_, node) => {
    if (editNode && editNode.id !== node.id) {
      setEditNode(node);
    }
  }, [editNode]);

  const onNodeDoubleClick = useCallback((_, node) => {
    setEditNode(node);
  }, []);

  // ── Context Menu handlers ─────────────────────────────────────────────────
  const onNodeContextMenu = useCallback(
    (event, node) => {
      event.preventDefault();
      const rect = reactFlowWrapper.current.getBoundingClientRect();
      setMenu({
        node,
        type: 'node',
        top: event.clientY - rect.top,
        left: event.clientX - rect.left,
      });
    },
    [reactFlowWrapper]
  );

  const onEdgeContextMenu = useCallback(
    (event, edge) => {
      event.preventDefault();
      const rect = reactFlowWrapper.current.getBoundingClientRect();
      setMenu({
        edge,
        type: 'edge',
        top: event.clientY - rect.top,
        left: event.clientX - rect.left,
      });
    },
    [reactFlowWrapper]
  );

  const onPaneContextMenu = useCallback(
    (event) => {
      event.preventDefault();
      const rect = reactFlowWrapper.current.getBoundingClientRect();
      setMenu({
        type: 'pane',
        top: event.clientY - rect.top,
        left: event.clientX - rect.left,
      });
    },
    [reactFlowWrapper]
  );

  const handleContextMenuAction = useCallback((action, payload) => {
    if (action === 'EDIT') {
      setEditNode(payload);
    } else if (action === 'DELETE') {
      setNodes(nds => {
        const up = nds.filter(n => n.id !== payload.id);
        setEdges(eds => {
          const upEdges = eds.filter(e => e.source !== payload.id && e.target !== payload.id);
          notifyChange(up, upEdges);
          return upEdges;
        });
        return up;
      });
    } else if (action === 'DELETE_EDGE') {
      setEdges(eds => {
        const up = eds.filter(e => e.id !== payload.id);
        notifyChange(undefined, up);
        return up;
      });
    } else if (action === 'TOGGLE_DISABLE') {
      setNodes(nds => {
        const up = nds.map(n => n.id === payload.id
          ? { ...n, data: { ...n.data, disabled: !n.data.disabled } }
          : n
        );
        notifyChange(up, undefined);
        return up;
      });
    } else if (action === 'DUPLICATE') {
      const dupId = payload.id + '_copy' + Math.floor(Math.random() * 1000);
      const dupNode = {
        ...payload,
        id: dupId,
        position: { x: payload.position.x + 50, y: payload.position.y + 50 },
        data: { ...payload.data, stepId: dupId },
        selected: false
      };
      setNodes(nds => {
        const up = [...nds, dupNode];
        notifyChange(up, undefined);
        return up;
      });
    } else if (action === 'SHOW_PALETTE' || action === 'NEW_NODE') {
      setPaletteOpen(true);
    } else if (action === 'ADD_AREA') {
      const areaId = 'area_' + Math.floor(Math.random() * 10000);
      const pos = payload?.left !== undefined
        ? rfInstance.screenToFlowPosition({ x: payload.left, y: payload.top })
        : { x: 0, y: 0 };
      const newArea = {
        id: areaId,
        type: 'areaNode',
        position: pos,
        data: {
          areaId: areaId,
          title: 'New Area',
          description: '',
          color: '#1a1a2e',
          width: 400,
          height: 400
        },
        style: { width: 400, height: 400, zIndex: -1 }
      };
      setNodes(nds => {
        const up = [...nds, newArea];
        notifyChange(up, undefined);
        return up;
      });
    } else if (action === 'REARRANGE_NODES') {
      setNodes(nds => {
        const up = autoLayoutNodes(nds);
        notifyChange(up, undefined);
        return up;
      });
    }
    setMenu(null);
  }, [setNodes, setEdges, notifyChange, rfInstance]);

  // ── Save from edit panel ──────────────────────────────────────────────────
  const onSaveNode = useCallback((nodeId, updatedData) => {
    setNodes(nds => {
      const updatedNodes = nds.map(n =>
        n.id === nodeId ? { ...n, id: updatedData.stepId, data: updatedData } : n
      );
      setEdges(eds => {
        const updatedEdges = nodeId !== updatedData.stepId
          ? eds.map(e => ({
              ...e,
              source: e.source === nodeId ? updatedData.stepId : e.source,
              target: e.target === nodeId ? updatedData.stepId : e.target,
            }))
          : eds;
        notifyChange(updatedNodes, updatedEdges);
        return updatedEdges;
      });
      return updatedNodes;
    });
    setEditNode(null);
  }, [setNodes, setEdges, notifyChange]);

  const onSaveArea = useCallback((nodeId, updatedData) => {
    setNodes(nds => {
      const updatedNodes = nds.map(n =>
        n.id === nodeId ? { ...n, id: updatedData.areaId, data: updatedData } : n
      );
      notifyChange(updatedNodes, undefined);
      return updatedNodes;
    });
    setEditNode(null);
  }, [setNodes, notifyChange]);

  // ── Delete selected nodes/edges ───────────────────────────────────────────
  const deleteSelected = useCallback(() => {
    setNodes(nds => {
      const selectedIds = new Set(nds.filter(n => n.selected).map(n => n.id));
      const updatedNodes = nds.filter(n => !selectedIds.has(n.id));
      setEdges(eds => {
        const remainingEdges = eds.filter(e =>
          !e.selected &&
          !selectedIds.has(e.source) &&
          !selectedIds.has(e.target)
        );
        notifyChange(updatedNodes, remainingEdges);
        return remainingEdges;
      });
      return updatedNodes;
    });
  }, [setNodes, setEdges, notifyChange]);

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape') {
        setMenu(null);
        return;
      }
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;

      if (e.key === 'Delete' || e.key === 'Backspace') {
        deleteSelected();
      } else if (e.key.toLowerCase() === 'x' || e.key.toLowerCase() === 'd') {
        setNodes(nds => {
          const selectedNodes = nds.filter(n => n.selected);
          if (!selectedNodes.length) return nds;
          const anyEnabled = selectedNodes.some(n => !n.data.disabled);
          const up = nds.map(n => n.selected ? { ...n, data: { ...n.data, disabled: anyEnabled } } : n);
          notifyChange(up, undefined);
          return up;
        });
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [deleteSelected, setNodes, notifyChange]);

  // ── Wire HecosFlowsBridge ─────────────────────────────────────────────────
  useEffect(() => {
    bridge._api = {
      renderCanvasFromFlow(flowObj) {
        const { nodes: rNodes, edges: rEdges } = flowToRFNodes(flowObj);
        setNodes(rNodes);
        setEdges(rEdges);
        execStateRef.current = {};
        // fitView after React commits state — ensures all nodes are visible without refresh
        setTimeout(() => {
          if (rfInstance) rfInstance.fitView({ padding: 0.15, duration: 300 });
        }, 80);
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

    window.togglePalette = () => setPaletteOpen(p => !p);

    return () => { bridge._api = null; };
  }, [setNodes, setEdges, exportFlow, deleteSelected, rfInstance]);

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
        onNodeDragStop={onNodeDragStop}
        onNodeClick={onNodeClick}
        onNodeDoubleClick={onNodeDoubleClick}
        onNodeContextMenu={onNodeContextMenu}
        onEdgeContextMenu={onEdgeContextMenu}
        onPaneContextMenu={onPaneContextMenu}
        onPaneClick={() => setMenu(null)}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={DEFAULT_EDGE_OPTIONS}
        fitView
        proOptions={{ hideAttribution: true }}
        deleteKeyCode={null}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#1a1a2e" />
        <Controls showInteractive={false} />
        <MiniMap
          pannable
          zoomable
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

        {nodes.length === 0 && (
          <Panel position="center" style={{ pointerEvents: 'none', minWidth: '300px' }}>
            <div className="rf-empty-hint">
              <i className="fas fa-project-diagram" />
              <p>Select a flow from the sidebar<br />or drag a node from the Palette to start</p>
            </div>
          </Panel>
        )}
      </ReactFlow>

      {paletteOpen && (
        <NodePalette
          catalog={catalog}
          onClose={() => setPaletteOpen(false)}
        />
      )}

      {editNode && (() => {
        if (editNode.type === 'areaNode') {
          return (
            <AreaEditPanel
              key={editNode.id}
              node={editNode}
              allNodeIds={nodes.map(n => n.id).filter(id => id !== editNode.id)}
              onSave={onSaveArea}
              onClose={() => setEditNode(null)}
            />
          );
        }

        const allVariables = Array.from(new Set(nodes.map(n => n.data?.outputAs).filter(Boolean)));
        return (
          <NodeEditPanel
            key={editNode.id}
            node={editNode}
            catalog={catalog}
            allNodeIds={nodes.map(n => n.id).filter(id => id !== editNode.id)}
            allVariables={allVariables}
            onSave={onSaveNode}
            onClose={() => setEditNode(null)}
          />
        );
      })()}

      <ContextMenu
        menu={menu}
        onClose={() => setMenu(null)}
        onAction={handleContextMenuAction}
      />
    </div>
  );
}
