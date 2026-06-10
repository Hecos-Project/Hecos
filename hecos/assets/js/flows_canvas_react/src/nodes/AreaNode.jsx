import React from 'react';
import { NodeResizer } from '@xyflow/react';

export default function AreaNode({ id, data, selected }) {
  const { title = 'New Area', description = '', color = '#1a1a2e', width, height, backgroundImage = '' } = data;

  // Ensure default dimensions if not provided, though the wrapper usually handles style dimensions
  const minWidth = 200;
  const minHeight = 200;

  // Convert hex color to rgba for background transparency
  const hexToRgba = (hex, alpha) => {
    let r = 0, g = 0, b = 0;
    if (hex && hex.length === 4) {
      r = parseInt(hex[1] + hex[1], 16);
      g = parseInt(hex[2] + hex[2], 16);
      b = parseInt(hex[3] + hex[3], 16);
    } else if (hex && hex.length === 7) {
      r = parseInt(hex.substring(1, 3), 16);
      g = parseInt(hex.substring(3, 5), 16);
      b = parseInt(hex.substring(5, 7), 16);
    }
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const bgColor = color ? hexToRgba(color, 0.2) : 'rgba(26, 26, 46, 0.2)';
  const borderColor = color || '#1a1a2e';

  const nodeStyle = {
    width: '100%',
    height: '100%',
    backgroundColor: bgColor,
    border: `2px dashed ${borderColor}`,
    borderRadius: '8px',
    padding: '16px',
    boxSizing: 'border-box',
    position: 'relative',
    pointerEvents: 'none', // Lets clicks pass through to nodes inside, but NodeResizer still works because it's a sibling
  };

  if (backgroundImage) {
    // Tint the image with the selected color for readability
    const tint = color ? hexToRgba(color, 0.6) : 'rgba(0,0,0,0.6)';
    nodeStyle.backgroundImage = `linear-gradient(${tint}, ${tint}), url("${backgroundImage}")`;
    nodeStyle.backgroundSize = 'cover';
    nodeStyle.backgroundPosition = 'center';
  }

  return (
    <>
      <NodeResizer
        color="#00d4ff"
        isVisible={selected}
        minWidth={minWidth}
        minHeight={minHeight}
      />
      <div
        className="react-flow__node-area"
        style={nodeStyle}
      >
        <div style={{ pointerEvents: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {title && (
            <div style={{
              fontSize: '18px',
              fontWeight: 'bold',
              color: 'var(--text, #fff)',
              textShadow: '1px 1px 2px rgba(0,0,0,0.8)'
            }}>
              {title}
            </div>
          )}
          {description && (
            <div style={{
              fontSize: '13px',
              color: 'var(--text-muted, #aaa)',
              lineHeight: '1.4',
              textShadow: '1px 1px 2px rgba(0,0,0,0.8)'
            }}>
              {description}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
