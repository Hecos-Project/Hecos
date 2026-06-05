import React, { useState, useMemo } from 'react';

const CATEGORY_ICONS = {
  AUDIO:      'fa-volume-up',
  LOGIC:      'fa-code-branch',
  TRIGGER:    'fa-clock',
  MAIL:       'fa-envelope',
  MESSAGING:  'fa-comment',
  DATA:       'fa-cloud',
  TIME:       'fa-calendar',
  MEDIA:      'fa-photo-video',
  SYSTEM:     'fa-terminal',
  BROWSER:    'fa-globe',
  VISION:     'fa-camera',
  MEMORY:     'fa-brain',
  AUTOMATION: 'fa-robot',
  PLUGINS:    'fa-plug',
  AI:         'fa-magic',
  GENERAL:    'fa-bolt',
};

export default function NodePalette({ catalog, onClose }) {
  const [query, setQuery] = useState('');
  const [collapsed, setCollapsed] = useState({});
  const [pos, setPos] = useState({ top: 50, right: 12 });
  const dragInfo = React.useRef(null);
  const paletteRef = React.useRef(null);

  const filtered = useMemo(() => {
    const q = query.toLowerCase().trim();
    if (!q) return catalog;
    const result = {};
    for (const [cat, actions] of Object.entries(catalog)) {
      const matching = actions.filter(a =>
        a.name.toLowerCase().includes(q) || (a.description || '').toLowerCase().includes(q)
      );
      if (matching.length) result[cat] = matching;
    }
    return result;
  }, [catalog, query]);

  const onDragStart = (e, actionName) => {
    e.dataTransfer.setData('application/hecos-action', actionName);
    e.dataTransfer.effectAllowed = 'copy';
  };

  const toggleCat = (cat) => setCollapsed(c => ({ ...c, [cat]: !c[cat] }));

  const sorted = Object.entries(filtered).sort(([a], [b]) => a.localeCompare(b));

  const onPointerDown = (e) => {
    if (e.target.closest('.close-btn')) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    
    let startLeft = pos.left;
    if (startLeft === undefined && paletteRef.current) {
      const rect = paletteRef.current.getBoundingClientRect();
      const parentRect = paletteRef.current.parentElement.getBoundingClientRect();
      startLeft = rect.left - parentRect.left;
    }

    dragInfo.current = {
      startX: e.clientX,
      startY: e.clientY,
      startTop: pos.top,
      startLeft: startLeft !== undefined ? startLeft : 0
    };
  };

  const onPointerMove = (e) => {
    if (!dragInfo.current) return;
    const dx = e.clientX - dragInfo.current.startX;
    const dy = e.clientY - dragInfo.current.startY;
    setPos({
      top: dragInfo.current.startTop + dy,
      left: dragInfo.current.startLeft + dx,
      right: 'auto' // Switch to left-based positioning
    });
  };

  const onPointerUp = (e) => {
    if (dragInfo.current) {
      e.currentTarget.releasePointerCapture(e.pointerId);
      dragInfo.current = null;
    }
  };

  return (
    <div key="palette" ref={paletteRef} className="hc-palette" style={{ position: 'absolute', top: pos.top, right: pos.right, left: pos.left }}>
      <div 
        className="hc-palette-header" 
        onPointerDown={onPointerDown} 
        onPointerMove={onPointerMove} 
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <span style={{ pointerEvents: 'none' }}><i className="fas fa-toolbox" style={{ marginRight: 6 }} />Node Palette</span>
        <button className="close-btn" onClick={onClose} title="Close">
          <i className="fas fa-times" />
        </button>
      </div>

      <div className="hc-palette-search">
        <input
          type="text"
          placeholder="Search actions…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          autoFocus
        />
      </div>

      <div className="hc-palette-body">
        {sorted.length === 0 && (
          <div style={{ padding: '12px', fontSize: '0.7rem', color: 'rgba(255,255,255,0.3)', textAlign: 'center' }}>
            No actions found
          </div>
        )}
        {sorted.map(([cat, actions]) => {
          const icon = CATEGORY_ICONS[cat] || 'fa-bolt';
          const isCollapsed = collapsed[cat];
          return (
            <div key={cat}>
              <div className="hc-pal-category" onClick={() => toggleCat(cat)}>
                <span><i className={`fas ${icon}`} style={{ marginRight: 5 }} />{cat}</span>
                <i className={`fas fa-chevron-${isCollapsed ? 'right' : 'down'}`}
                   style={{ fontSize: '0.55rem', opacity: 0.5 }} />
              </div>
              {!isCollapsed && (
                <div className="hc-pal-items">
                  {actions.map(action => (
                    <div
                      key={action.name}
                      className="hc-pal-item"
                      draggable
                      onDragStart={e => onDragStart(e, action.name)}
                      title={action.description || action.name}
                    >
                      <span className="pal-icon">{action.icon || '⚡'}</span>
                      <span className="pal-name">
                        {action.name.replace(/^[^_]+__/, '')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
