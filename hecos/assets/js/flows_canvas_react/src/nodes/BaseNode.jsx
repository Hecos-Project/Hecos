import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { CATEGORY_COLORS, getCategoryFromAction } from './nodeTypeMap.js';

/**
 * BaseNode — shared rendering logic for all Hecos Flow nodes.
 * Accepts:
 *   data.stepId, data.action, data.params, data.outputAs,
 *   data.execState ('running'|'done'|'error'|null)
 *   headerColor, badgeBg, badgeText, icon, showTrueOutput, showFalseOutput
 */
export function BaseNode({
  data,
  selected,
  headerColor = '#0c4a6e',
  showInputHandle = true,
  showOutputHandle = true,
  showTrueOutput = false,
  showFalseOutput = false,
  children,
}) {
  const cat = getCategoryFromAction(data.action);
  const catColor = CATEGORY_COLORS[cat] || { bg: '#1a1a1a', text: '#aaa' };
  const actionMethod = data.action?.split('__')[1] || data.action || '';

  // Params preview (first 2 entries)
  const paramEntries = Object.entries(data.params || {}).slice(0, 2);
  const paramPreview = paramEntries.map(([k, v]) => {
    const val = typeof v === 'object' ? JSON.stringify(v) : String(v);
    return `${k}: ${val.length > 20 ? val.slice(0, 20) + '…' : val}`;
  }).join('  ·  ');

  const stateClass = data.execState ? `state-${data.execState}` : '';

  return (
    <div className={`hc-node ${stateClass} ${selected ? 'selected' : ''}`}
         style={{ '--hc-header-color': headerColor }}>

      {showInputHandle && (
        <Handle type="target" position={Position.Left} id="in"
          style={{ top: '50%' }} />
      )}

      <div className="hc-node-header" style={{ background: headerColor }}>
        <span className="icon">{data.icon || '⚡'}</span>
        <span className="title" title={data.action}>{actionMethod}</span>
        <span className="badge" style={{ background: catColor.bg, color: catColor.text }}>
          {cat}
        </span>
      </div>

      <div className="hc-node-body">
        <div className="step-id" title={data.stepId}>{data.stepId}</div>
        {paramPreview && <div className="param-preview">{paramPreview}</div>}
        {data.outputAs && (
          <div className="param-preview" style={{ color: 'rgba(0,212,255,0.5)', marginTop: 2 }}>
            → {data.outputAs}
          </div>
        )}
        {children}
      </div>

      {showOutputHandle && !showTrueOutput && (
        <Handle type="source" position={Position.Right} id="out"
          style={{ top: '50%' }} />
      )}

      {/* Dual outputs for logic nodes */}
      {showTrueOutput && (
        <Handle type="source" position={Position.Right} id="true"
          style={{ top: '33%', background: '#22c55e' }}
          title="True / Success" />
      )}
      {showFalseOutput && (
        <Handle type="source" position={Position.Right} id="false"
          style={{ top: '67%', background: '#ef4444' }}
          title="False / Fail" />
      )}
    </div>
  );
}
