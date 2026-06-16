import React, { useState, useEffect, useMemo } from 'react';

/**
 * Custom sound selection field taking advantage of the system explorer APIs.
 */
function SoundField({ label, value, onChange }) {
  const [sounds, setSounds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isPicking, setIsPicking] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = React.useRef(null);

  useEffect(() => {
    fetch('/api/system/explorer/ls', {
      method: 'POST',
      body: JSON.stringify({ path: 'C:\\Hecos\\hecos\\assets\\sounds' })
    }).then(r => r.json()).then(data => {
      if (data.ok && data.entries) {
        setSounds(data.entries.filter(e => e.type === 'file' && e.name.match(/\.(wav|mp3|ogg)$/i)).map(e => e.name));
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handleBrowse = async () => {
    setIsPicking(true);
    try {
      const res = await fetch("/api/system/explorer/pick-native", {
        method: "POST",
        body: JSON.stringify({
          title: "Hecos — Select Sound File",
          initialdir: "C:\\Hecos\\hecos\\assets\\sounds",
          filetypes: [["Audio Files", "*.wav *.mp3 *.ogg"], ["All Files", "*.*"]]
        })
      });
      const data = await res.json();
      if (data.ok && data.path) {
        const base = data.path.split('\\\\').pop().split('/').pop();
        if (!sounds.includes(base)) setSounds(s => [...s, base]);
        onChange(base);
      }
    } catch(e) { console.error(e); }
    setIsPicking(false);
  };

  const togglePlay = () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setIsPlaying(false);
      return;
    }
    if (!value) return;
    
    if (audioRef.current) audioRef.current.pause();
    
    const audio = new Audio('/assets/sounds/' + value);
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => setIsPlaying(false);
    audioRef.current = audio;
    setIsPlaying(true);
    audio.play().catch(() => setIsPlaying(false));
  };

  return (
    <div className="hc-field">
      <label>{label}</label>
      <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
        <select style={{ flex: 1, minWidth: 0 }} value={value || ''} onChange={e => onChange(e.target.value)}>
          <option value="">-- Select a sound --</option>
          {loading && <option disabled>Loading...</option>}
          {sounds.map(s => <option key={s} value={s}>{s}</option>)}
          {value && !sounds.includes(value) && <option value={value}>{value}</option>}
        </select>
        <button type="button" className="hc-btn secondary" style={{ flex: 'none', padding: '0 8px', color: isPlaying ? '#ef4444' : undefined }} title={isPlaying ? "Stop Audio" : "Preview Audio"} onClick={togglePlay}>
          <i className={isPlaying ? "fas fa-stop" : "fas fa-play"} />
        </button>
        <button type="button" className="hc-btn secondary" style={{ flex: 'none', padding: '0 8px' }} onClick={handleBrowse} disabled={isPicking}>
          {isPicking ? <i className="fas fa-spinner fa-spin" /> : <i className="fas fa-folder-open" />}
        </button>
      </div>
    </div>
  );
}

function LogicBuilderField({ label, value, onChange, allVariables }) {
  const [v1, setV1] = useState('');
  const [op, setOp] = useState('==');
  const [v2, setV2] = useState('');

  const handleUpdate = (newV1, newOp, newV2) => {
    setV1(newV1); setOp(newOp); setV2(newV2);
    if (!newV1) return;
    
    // Auto-detect if newV2 is a number or string
    let formattedV2 = newV2;
    if (newV2 && isNaN(Number(newV2))) {
      formattedV2 = `'${newV2}'`;
    }
    
    onChange(`{{ ${newV1} }} ${newOp} ${formattedV2}`);
  };

  return (
    <div className="hc-field" style={{ marginBottom: 15 }}>
      <label style={{ color: 'var(--accent)', fontWeight: 'bold' }}>
        <i className="fas fa-magic" style={{ marginRight: 6 }}></i> Logic Builder
      </label>
      <div style={{ display: 'flex', gap: '6px', padding: '12px', background: 'rgba(0, 212, 255, 0.05)', border: '1px solid rgba(0, 212, 255, 0.2)', borderRadius: '6px', marginBottom: '8px' }}>
        <select style={{ flex: 2, minWidth: '100px' }} value={v1} onChange={e => handleUpdate(e.target.value, op, v2)}>
          <option value="">— Variable —</option>
          {allVariables.map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <select style={{ flex: 1, minWidth: '60px' }} value={op} onChange={e => handleUpdate(v1, e.target.value, v2)}>
          <option value="==">==</option>
          <option value="!=">!=</option>
          <option value=">">&gt;</option>
          <option value="<">&lt;</option>
          <option value=">=">&gt;=</option>
          <option value="<=">&lt;=</option>
        </select>
        <input type="text" style={{ flex: 2, minWidth: '80px' }} value={v2} onChange={e => handleUpdate(v1, op, e.target.value)} placeholder="Value..." />
      </div>
      <label style={{ fontSize: '0.75rem', opacity: 0.8 }}>Generated Expression (Editable)</label>
      <input type="text" value={value ?? ''} onChange={e => onChange(e.target.value)} placeholder="e.g. {{ var }} > 5" style={{ fontFamily: 'monospace' }} />
    </div>
  );
}

/**
 * Node Edit Panel — slides in from right when a node is double-clicked.
 * Shows a dynamic form generated from the action's params definition in the catalog.
 */
export default function NodeEditPanel({ node, catalog, allNodeIds, allVariables, onSave, onClose }) {
  const data = node.data || {};
  const [stepId, setStepId]     = useState(data.stepId || node.id || '');
  const [action, setAction]     = useState(data.action || '');
  const [params, setParams]     = useState(data.params || {});
  const [outputAs, setOutputAs] = useState(data.outputAs || '');
  const [dependsOn, setDependsOn] = useState((data.dependsOn || []).join(', '));
  const [disableMode, setDisableMode] = useState(data.disableMode || (action === 'CONTROL__start' ? 'stop' : 'skip'));

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
    const finalStepId = stepId.trim() || node.id;
    if (finalStepId !== node.id && allNodeIds.includes(finalStepId)) {
      if (window.toast) window.toast('error', `Step ID '${finalStepId}' is already in use.`);
      else alert(`Step ID '${finalStepId}' is already in use.`);
      return;
    }
    onSave(node.id, {
      stepId: finalStepId,
      action,
      params,
      outputAs: outputAs.trim(),
      dependsOn: depsArray,
      disableMode: disableMode,
      icon: actionDef?.icon || data.icon || '⚡',
      description: actionDef?.description || data.description || '',
    });
  };

  const renderVarPicker = (key) => {
    const hasVars = allVariables && allVariables.length > 0;
    return (
      <select 
         style={{ 
           width: 'auto', padding: '2px 4px', fontSize: '0.6rem', 
           background: 'rgba(255,255,255,0.08)', color: 'rgba(0,212,255,0.8)', 
           border: 'none', borderRadius: '4px', outline: 'none', 
           cursor: hasVars ? 'pointer' : 'not-allowed', 
           opacity: hasVars ? 1 : 0.4 
         }}
         value="" 
         onChange={e => { if (e.target.value) { setParam(key, (params[key] || '') + `{{ ${e.target.value} }}`); } }}
         title="Insert Variable"
         disabled={!hasVars}
      >
        <option value="" disabled>+ {'{}'}</option>
        {hasVars ? (
          allVariables.map(v => <option key={v} value={v}>{v}</option>)
        ) : (
          <option value="" disabled>(No output_as nodes)</option>
        )}
      </select>
    );
  };

  const renderParamField = (key, typeDesc) => {
    const t = String(typeDesc).toLowerCase();
    const val = params[key];
    const label = key.replace(/_/g, ' ');

    if (key === 'sound' || t.includes('sound file')) {
      return <SoundField key={key} label={label} value={val} onChange={(v) => setParam(key, v)} />;
    }

    if (action === 'LOGIC__if_else' && key === 'condition') {
      return <LogicBuilderField key={key} label={label} value={val} onChange={(v) => setParam(key, v)} allVariables={allVariables} />;
    }

    if (t.includes('select:')) {
      const optionsStr = t.split('select:')[1].split(' ')[0];
      const options = optionsStr.split('|');
      // If there's no current value, set it to the first option
      const currentVal = val ?? options[0];
      return (
        <div className="hc-field" key={key}>
          <label>{label}</label>
          <select value={currentVal} onChange={e => setParam(key, e.target.value)}>
            {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>
      );
    }

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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <label style={{ marginBottom: 0 }}>{label} <span style={{ opacity: 0.4, fontSize: '0.6rem' }}>JSON</span></label>
            {renderVarPicker(key)}
          </div>
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <label style={{ marginBottom: 0 }}>{label} <span style={{ opacity: 0.4, fontSize: '0.6rem' }}>{typeDesc.split(' ')[0]}</span></label>
          {renderVarPicker(key)}
        </div>
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
        {action !== 'LOGIC__set_variable' && action !== 'CONTROL__start' && action !== 'FLOWS__run_flow' && (
          <div className="hc-field">
            <label>Output As (variable)</label>
            <input
              type="text"
              value={outputAs}
              onChange={e => setOutputAs(e.target.value)}
              placeholder="e.g. result_var"
            />
          </div>
        )}

        {/* Disable Mode */}
        <div className="hc-field">
          <label>Disable Mode (when node is disabled)</label>
          <select value={disableMode} onChange={e => setDisableMode(e.target.value)}>
            <option value="skip">Skip (Bypass node, run children)</option>
            <option value="stop">Stop (Halt execution of this branch)</option>
          </select>
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
