import React, { useEffect, useRef } from 'react';

export default function ContextMenu({ menu, onClose, onAction }) {
  const ref = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  if (!menu) return null;

  return (
    <div
      ref={ref}
      style={{
        position: 'absolute',
        top: menu.top,
        left: menu.left,
        zIndex: 1000,
        backgroundColor: 'rgba(8,15,28,0.98)',
        border: '1px solid rgba(0,212,255,0.18)',
        borderRadius: '8px',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        backdropFilter: 'blur(12px)',
        minWidth: '150px',
        padding: '5px 0',
        fontFamily: 'Inter, sans-serif'
      }}
      // Stop context menu propagation on the menu itself
      onContextMenu={(e) => { e.preventDefault(); e.stopPropagation(); }}
    >
      {menu.type === 'node' && (
        <React.Fragment>
          <div className="hc-cm-item" onClick={() => onAction('EDIT', menu.node)}>
            <i className="fas fa-edit" style={{ width: '20px', color: '#00d4ff' }} /> Edit Node
          </div>
          <div className="hc-cm-item" onClick={() => onAction('TOGGLE_DISABLE', menu.node)}>
            {menu.node?.data?.disabled ? (
              <><i className="fas fa-play" style={{ width: '20px', color: '#22c55e' }} /> Enable Node</>
            ) : (
              <><i className="fas fa-ban" style={{ width: '20px', color: '#ef4444' }} /> Disable Node</>
            )}
          </div>
          <div className="hc-cm-item" onClick={() => onAction('DUPLICATE', menu.node)}>
            <i className="fas fa-copy" style={{ width: '20px', color: '#b45309' }} /> Duplicate
          </div>
          <div className="hc-separator" style={{ height: '1px', background: 'rgba(255,255,255,0.1)', margin: '4px 0' }} />
          <div className="hc-cm-item" onClick={() => onAction('DELETE', menu.node)}>
            <i className="fas fa-trash" style={{ width: '20px', color: '#ef4444' }} /> Delete
          </div>
        </React.Fragment>
      )}

      {menu.type === 'pane' && (
        <React.Fragment>
          <div className="hc-cm-item" onClick={() => onAction('SHOW_PALETTE')}>
            <i className="fas fa-toolbox" style={{ width: '20px', color: '#00d4ff' }} /> Show Palette
          </div>
          <div className="hc-cm-item" onClick={() => onAction('NEW_NODE', menu)}>
            <i className="fas fa-plus-circle" style={{ width: '20px', color: '#22c55e' }} /> Quick Add
          </div>
        </React.Fragment>
      )}

      {menu.type === 'edge' && (
        <React.Fragment>
          <div className="hc-cm-item" onClick={() => onAction('DELETE_EDGE', menu.edge)}>
            <i className="fas fa-unlink" style={{ width: '20px', color: '#ef4444' }} /> Delete Connection
          </div>
        </React.Fragment>
      )}
    </div>
  );
}
