import React, { useState, useEffect, useMemo } from 'react';

/**
 * Node Edit Panel — slides in from right when a node is double-clicked.
 * Shows a dynamic form generated from the action's params definition in the catalog.
 */
export default function NodeEditPanel({ node, catalog, allNodeIds, onSave, onClose }) {
  const data = node.data || {};
  const [stepId, setStepId]     = useState(data.stepId || node.id || '');
  const [action, setAction]     = useState(data.action || '');
  const [params, setParams]     = useState(data.params || {});
  const [outputAs, setOutputAs] = useState(data.outputAs || '');
  const [dependsOn, setDependsOn] = useState((data.dependsOn || []).join(', '));

  // Flat list of all actions
  const allActions = useMemo(() =>
    Object.values(catalog).flat().sort((a, b) => a.name.localeCompare(b.name)),
    [catalog]
  );

  // Current action definition
  const actionDef = useMemo(() =>
    allActions.find(a => a.name === action),
    [allActions, action]
  );

  // When action changes, reset params to defaults
  useEffect(() => {
    if (!actionDef) return;
    const defaults = {};
    for (const [key, typeDesc] of Object.entries(actionDef.params || {})) {
      const t = String(typeDesc).toLowerCase();
      // Preserve existing value if key already exists, otherwise use default
      if (params[key] !== undefined) { defaults[key] = params[key]; continue; }
      if (t.includes('number') || t.includes('integer') || t.includes('seconds')) defaults[key] = 0;
      else if (t.includes('bool')) defaults[key] = false;
      else if (t.includes('dict') || t.includes('object')) defaults[key] = {};
      else if (t.includes('list')) defaults[key] = [];
      else defaults[key] = '';
    }
    setParams(defaults);
  }, [action]); // eslint-disable-line

  const setParam = (key, value) => {
    setParams(p => ({ ...p, [key]: value }));
  };

  const handleSave = () => {
    const depsArray = dependsOn.split(',').map(s => s.trim()).filter(Boolean);
    onSave(node.id, {
      stepId: stepId.trim() || node.id,
      action,
      params,
      outputAs: outputAs.trim(),
      dependsOn: depsArray,
      icon: actionDef?.icon || data.icon || '⚡',
      description: actionDef?.description || data.description || '',
    });
  };

  const renderParamField = (key, typeDesc) => {
    const t = String(typeDesc).toLowerCase();
    const val = params[key];
    const label = key.replace(/_/g, ' ');

    if (t.includes('bool')) {
      return (
        <div className="hc-field" key={key}>
          <label>{label}</label>
          <select value={String(val ?? 'true')} onChange={e => setParam(key, e.target.value === 'true')}>
            <option value="true">true</option>
            <option value="false">false</option>
          </select>
        </div>
      );
    }
    if (t.includes('number') || t.includes('integer') || t.includes('seconds')) {
      return (
        <div className="hc-field" key={key}>
          <label>{label} <span style={{ opacity: 0.4, fontSize: '0.6rem' }}>{typeDesc}</span></label>
          <input type="number" value={val ?? 0} onChange={e => setParam(key, Number(e.target.value))} />
        </div>
      );
    }
    if (t.includes('dict') || t.includes('object') || t.includes('list')) {
      return (
        <div className="hc-field" key={key}>
          <label>{label} <span style={{ opacity: 0.4, fontSize: '0.6rem' }}>JSON</span></label>
          <textarea
            rows={3}
            value={typeof val === 'object' ? JSON.stringify(val, null, 2) : val}
            onChange={e => {
              try { setParam(key, JSON.parse(e.target.value)); }
              catch { setParam(key, e.target.value); }
            }}
          />
        </div>
      );
    }
    // Long strings (template, prompt)
    const isLong = ['template', 'prompt', 'body', 'text', 'message', 'description'].includes(key);
    return (
      <div className="hc-field" key={key}>
        <label>{label} <span style={{ opacity: 0.4, fontSize: '0.6rem' }}>{typeDesc.split(' ')[0]}</span></label>
        {isLong
          ? <textarea rows={3} value={val ?? ''} onChange={e => setParam(key, e.target.value)} />
          : <input type="text" value={val ?? ''} onChange={e => setParam(key, e.target.value)} placeholder={typeDesc} />
        }
      </div>
    );
  };

  return (
    <div className="hc-edit-panel">
      <div className="hc-edit-panel-header">
        <h3>
          <span style={{ marginRight: 6 }}>{actionDef?.icon || '⚡'}</span>
          Edit Node
        </h3>
        <button className="close-btn" onClick={onClose}>
          <i className="fas fa-times" />
        </button>
      </div>

      <div className="hc-edit-panel-body">
        {/* Step ID */}
        <div className="hc-field">
          <label>Step ID</label>
          <input
            type="text"
            value={stepId}
            onChange={e => setStepId(e.target.value)}
            placeholder="unique_step_id"
          />
        </div>

        {/* Action selector */}
        <div className="hc-field">
          <label>Action</label>
          <div className="hc-action-select">
            <select value={action} onChange={e => setAction(e.target.value)}>
              <option value="">— select action —</option>
              {Object.entries(
                allActions.reduce((acc, a) => {
                  const cat = a.name.split('__')[0];
                  if (!acc[cat]) acc[cat] = [];
                  acc[cat].push(a);
                  return acc;
                }, {})
              ).sort().map(([cat, acts]) => (
                <optgroup key={cat} label={cat}>
                  {acts.map(a => (
                    <option key={a.name} value={a.name}>
                      {a.icon} {a.name.replace(/^[^_]+__/, '')}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          {actionDef?.description && (
            <span style={{ fontSize: '0.62rem', color: 'rgba(255,255,255,0.3)', marginTop: 2 }}>
              {actionDef.description.slice(0, 100)}
            </span>
          )}
        </div>

        {/* Dynamic param fields */}
        {actionDef && Object.keys(actionDef.params || {}).length > 0 && (
          <>
            <hr className="hc-divider" />
            {Object.entries(actionDef.params).map(([key, typeDesc]) =>
              renderParamField(key, typeDesc)
            )}
          </>
        )}

        <hr className="hc-divider" />

        {/* Output As */}
        <div className="hc-field">
          <label>Output As (variable)</label>
          <input
            type="text"
            value={outputAs}
            onChange={e => setOutputAs(e.target.value)}
            placeholder="e.g. result_var"
          />
        </div>

        {/* Depends On */}
        <div className="hc-field">
          <label>Depends On (comma-separated IDs)</label>
          <input
            type="text"
            value={dependsOn}
            onChange={e => setDependsOn(e.target.value)}
            placeholder="step1, step2"
          />
          {allNodeIds.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 5 }}>
              {allNodeIds.map(id => (
                <span
                  key={id}
                  onClick={() => {
                    const current = dependsOn.split(',').map(s => s.trim()).filter(Boolean);
                    if (!current.includes(id)) {
                      setDependsOn([...current, id].join(', '));
                    }
                  }}
                  style={{
                    fontSize: '0.6rem',
                    padding: '2px 6px',
                    background: 'rgba(255,255,255,0.06)',
                    borderRadius: 4,
                    cursor: 'pointer',
                    color: 'rgba(255,255,255,0.45)',
                    border: '1px solid rgba(255,255,255,0.08)',
                  }}
                  title={`Add ${id} to depends_on`}
                >
                  {id}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="hc-edit-panel-footer">
        <button className="hc-btn secondary" onClick={onClose}>Cancel</button>
        <button className="hc-btn primary" onClick={handleSave}>
          <i className="fas fa-check" style={{ marginRight: 5 }} />Save Node
        </button>
      </div>
    </div>
  );
}
