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

  return (
    <div className="hc-palette" style={{ position: 'absolute', top: 50, right: 12 }}>
      <div className="hc-palette-header">
        <span><i className="fas fa-toolbox" style={{ marginRight: 6 }} />Node Palette</span>
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
