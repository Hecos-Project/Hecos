import React, { useState, useRef } from 'react';
import { getPalettes } from '../utils/palettes';

// ── Color Picker with palette support ─────────────────────────────────────────
function AreaColorPicker({ value, onChange }) {
  const [paletteKey, setPaletteKey] = useState('none');
  const palettes = getPalettes();

  const paletteColors = paletteKey !== 'none' ? (palettes[paletteKey] || []) : [];

  return (
    <div className="hc-field">
      <label>Background Color</label>

      {/* Row: native color + palette selector */}
      <div style={{ display: 'flex', gap: '8px', marginTop: '6px', alignItems: 'center' }}>
        <input
          type="color"
          value={value || '#1a1a2e'}
          onChange={e => onChange(e.target.value)}
          title="Pick any custom color"
          style={{
            width: '38px', height: '38px',
            padding: '2px', border: '2px solid rgba(255,255,255,0.15)',
            borderRadius: '6px', background: 'none', cursor: 'pointer',
            flexShrink: 0,
          }}
        />
        <select
          style={{ flex: 1 }}
          value={paletteKey}
          onChange={e => setPaletteKey(e.target.value)}
        >
          <option value="none">— Palette —</option>
          <option value="dark">🌑 Dark</option>
          <option value="light">🌤 Light</option>
          <option value="vibrant">⚡ Vibrant</option>
        </select>
        {/* Live preview swatch */}
        <div
          title={`Current: ${value}`}
          style={{
            width: '38px', height: '38px', borderRadius: '6px', flexShrink: 0,
            backgroundColor: value || '#1a1a2e',
            border: '2px solid rgba(255,255,255,0.2)',
            boxShadow: '0 0 6px rgba(0,0,0,0.4)',
          }}
        />
      </div>

      {/* Palette swatches */}
      {paletteColors.length > 0 && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: '8px',
          marginTop: '10px', padding: '10px',
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)',
        }}>
          {paletteColors.map(c => {
            const isSelected = value?.toLowerCase() === c.hex.toLowerCase();
            return (
              <div
                key={c.hex}
                title={`${c.label} (${c.hex})`}
                onClick={() => onChange(c.hex)}
                style={{
                  width: '32px', height: '32px', borderRadius: '6px',
                  backgroundColor: c.hex, cursor: 'pointer',
                  border: isSelected ? '3px solid #fff' : '2px solid rgba(255,255,255,0.2)',
                  boxShadow: isSelected
                    ? `0 0 10px ${c.hex}, 0 0 4px #fff`
                    : '0 2px 4px rgba(0,0,0,0.4)',
                  transform: isSelected ? 'scale(1.15)' : 'scale(1)',
                  transition: 'all 0.15s ease',
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Background Image Picker ────────────────────────────────────────────────────
function AreaImagePicker({ value, onChange }) {
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Convert the local file to a base64 data URL so it works inside the canvas
    const reader = new FileReader();
    reader.onload = (evt) => {
      onChange(evt.target.result);
    };
    reader.readAsDataURL(file);
    // Reset input so same file can be re-selected
    e.target.value = '';
  };

  const clearImage = () => onChange('');

  return (
    <div className="hc-field">
      <label>Background Image</label>

      {/* Preview */}
      {value && (
        <div style={{ position: 'relative', marginTop: '8px', marginBottom: '8px' }}>
          <img
            src={value}
            alt="Background preview"
            style={{
              width: '100%', height: '90px', objectFit: 'cover',
              borderRadius: '6px', border: '1px solid rgba(255,255,255,0.15)',
              display: 'block',
            }}
          />
          <button
            onClick={clearImage}
            title="Remove image"
            style={{
              position: 'absolute', top: '6px', right: '6px',
              background: 'rgba(0,0,0,0.7)', border: 'none',
              color: '#fff', borderRadius: '50%',
              width: '22px', height: '22px',
              cursor: 'pointer', fontSize: '12px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <i className="fas fa-times" />
          </button>
        </div>
      )}

      {/* Buttons row */}
      <div style={{ display: 'flex', gap: '8px', marginTop: value ? '0' : '6px' }}>
        {/* Native OS file picker */}
        <button
          type="button"
          className="hc-btn secondary"
          onClick={() => fileInputRef.current?.click()}
          style={{ flex: 1 }}
        >
          <i className="fas fa-folder-open" style={{ marginRight: '6px' }} />
          Browse…
        </button>
        {value && (
          <button
            type="button"
            className="hc-btn secondary"
            onClick={clearImage}
            style={{ color: '#ff6b6b' }}
            title="Remove image"
          >
            <i className="fas fa-trash-alt" />
          </button>
        )}
      </div>

      {/* URL fallback input */}
      <input
        type="text"
        value={value && value.startsWith('data:') ? '' : (value || '')}
        onChange={e => onChange(e.target.value)}
        placeholder="…or paste a URL (https://... / /assets/...)"
        style={{ marginTop: '6px' }}
        title="Paste an image URL"
      />

      {/* Hidden native file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────
export default function AreaEditPanel({ node, allNodeIds, onSave, onClose }) {
  const data = node.data || {};
  const [areaId,          setAreaId]          = useState(data.areaId || node.id || '');
  const [title,           setTitle]           = useState(data.title || '');
  const [description,     setDescription]     = useState(data.description || '');
  const [color,           setColor]           = useState(data.color || '#1a1a2e');
  const [backgroundImage, setBackgroundImage] = useState(data.backgroundImage || '');

  const handleSave = () => {
    const finalAreaId = areaId.trim() || node.id;
    if (finalAreaId !== node.id && allNodeIds.includes(finalAreaId)) {
      if (window.toast) window.toast('error', `ID '${finalAreaId}' is already in use.`);
      else alert(`ID '${finalAreaId}' is already in use.`);
      return;
    }
    onSave(node.id, {
      ...data,
      areaId: finalAreaId,
      title:           title.trim(),
      description:     description.trim(),
      color:           color,
      backgroundImage: backgroundImage,
    });
  };

  return (
    <div className="hc-edit-panel">
      <div className="hc-edit-panel-header">
        <h3>
          <i className="fas fa-layer-group" style={{ marginRight: 6 }} />
          Edit Area
        </h3>
        <button className="close-btn" onClick={onClose}>
          <i className="fas fa-times" />
        </button>
      </div>

      <div className="hc-edit-panel-body">

        <div className="hc-field">
          <label>Area ID</label>
          <input
            type="text"
            value={areaId}
            onChange={e => setAreaId(e.target.value)}
            placeholder="unique_area_id"
          />
        </div>

        <div className="hc-field">
          <label>Title</label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Act 1"
          />
        </div>

        <div className="hc-field">
          <label>Description</label>
          <textarea
            rows={3}
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="e.g. In this act..."
          />
        </div>

        <AreaColorPicker value={color} onChange={setColor} />

        <AreaImagePicker value={backgroundImage} onChange={setBackgroundImage} />

      </div>

      <div className="hc-edit-panel-footer">
        <button className="hc-btn secondary" onClick={onClose}>Cancel</button>
        <button className="hc-btn primary" onClick={handleSave}>
          <i className="fas fa-check" style={{ marginRight: 5 }} />Save Area
        </button>
      </div>
    </div>
  );
}
