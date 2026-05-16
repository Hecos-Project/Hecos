/**
 * hecos_aesthetic_picker.js
 * A generalized, reusable UI component for selecting HEX colors and background images.
 * Integrates directly with the `hecos_file_picker` ecosystem.
 */

class HecosAestheticPicker {
    /**
     * Instantiates the picker inside a target container.
     * @param {string|HTMLElement} container - The DOM element or ID to render inside.
     * @param {Object} options - Configuration and callbacks.
     */
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.getElementById(container) : container;
        if (!this.container) {
            console.error("HecosAestheticPicker: provided container not found.");
            return;
        }

        this.options = Object.assign({
            initialColor: '#202124',
            initialImage: '',
            initialStyle: 'default',
            showColor: true,
            showImage: true,
            showStyle: false,
            colorLabel: t('webui_aes_color') || 'Colore Fondale',
            imageLabel: t('webui_aes_background') || 'Immagine Sfondo',
            styleLabel: t('webui_aes_theme') || 'Tema Widget',
            onColorChange: (hex) => {},
            onColorLive: (hex) => {}, // For drag events
            onImageChange: (path) => {},
            onClearImage: () => {},
            onStyleChange: (style) => {},
            onReset: () => {}
        }, options);

        this.currentColor = this.options.initialColor;
        this.currentImage = this.options.initialImage;
        this.currentStyle = this.options.initialStyle;

        this.render();
    }

    render() {
        this.container.innerHTML = '';
        this.container.classList.add('hecos-aesthetic-wrapper');
        
        const wrapper = document.createElement('div');
        wrapper.style.display = 'flex';
        wrapper.style.flexDirection = 'column';
        wrapper.style.gap = '14px';
        wrapper.style.padding = '12px';
        wrapper.style.background = 'transparent';
        wrapper.style.border = 'none';
        wrapper.style.borderRadius = '8px';

        // ─── Style selector ───
        if (this.options.showStyle) {
            const styleRow = document.createElement('div');
            styleRow.style.display = 'flex';
            styleRow.style.flexDirection = 'column';
            styleRow.style.gap = '6px';

            const labelArea = document.createElement('div');
            labelArea.innerHTML = `
                <div style="font-size: 13px; font-weight: 600; color: var(--text); display:flex; align-items:center; gap:6px;">
                    <i class="fas fa-paint-brush" style="color:var(--accent);"></i> ${this.options.styleLabel}
                </div>
            `;

            const styleSelect = document.createElement('select');
            styleSelect.className = 'form-control';
            styleSelect.style.fontSize = '12px';
            styleSelect.style.padding = '4px 8px';
            
            const themes = [
                { val: 'default', lab: 'Standard' },
                { val: 'cyber',   lab: 'Cyber'    },
                { val: 'alert',   lab: 'Alert'    },
                { val: 'glass',   lab: 'Glass'    },
                { val: 'ghost',   lab: 'Ghost'    }
            ];

            themes.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.val;
                opt.innerText = t.lab;
                if (this.currentStyle === t.val) opt.selected = true;
                styleSelect.appendChild(opt);
            });

            styleSelect.addEventListener('change', (e) => {
                this.currentStyle = e.target.value;
                this.options.onStyleChange(this.currentStyle);
            });

            styleRow.appendChild(labelArea);
            styleRow.appendChild(styleSelect);
            wrapper.appendChild(styleRow);

            const divider = document.createElement('div');
            divider.style.height = '1px';
            divider.style.background = 'var(--border)';
            wrapper.appendChild(divider);
        }

        // ─── Color Picker ───
        if (this.options.showColor) {
            const colorRow = document.createElement('div');
            colorRow.style.display = 'flex';
            colorRow.style.alignItems = 'center';
            colorRow.style.justifyContent = 'space-between';
            colorRow.style.gap = '12px';

            const labelArea = document.createElement('div');
            labelArea.innerHTML = `
                <div style="font-size: 13px; font-weight: 600; color: var(--text); display:flex; align-items:center; gap:6px;">
                    <i class="fas fa-palette" style="color:var(--accent);"></i> ${this.options.colorLabel}
                </div>
            `;

            const inputWrapper = document.createElement('div');
            inputWrapper.style.display = 'flex';
            inputWrapper.style.alignItems = 'center';
            inputWrapper.style.gap = '8px';
            
            const hexText = document.createElement('input');
            hexText.type = 'text';
            hexText.className = 'form-control';
            hexText.style.width = '80px';
            hexText.style.fontSize = '12px';
            hexText.style.fontFamily = 'monospace';
            hexText.style.textAlign = 'center';
            hexText.value = this.currentColor;

            // Normalize initial color (input type="color" requires exactly #RRGGBB)
            let safeColor = this.currentColor || '#000000';
            if (!/^#[0-9A-F]{6}$/i.test(safeColor)) safeColor = '#000000';
            this.currentColor = safeColor;

            const colorInput = document.createElement('input');
            colorInput.type = 'color';
            colorInput.value = this.currentColor;
            colorInput.style.cursor = 'pointer';
            colorInput.style.border = '1px solid var(--border)';
            colorInput.style.width = '34px';
            colorInput.style.height = '34px';
            colorInput.style.padding = '2px';
            colorInput.style.borderRadius = '6px';
            colorInput.style.background = 'var(--bg3)';
            colorInput.style.boxSizing = 'border-box';
            colorInput.style.appearance = 'none';
            colorInput.style.webkitAppearance = 'none';

            // Events
            colorInput.addEventListener('input', (e) => {
                this.currentColor = e.target.value;
                hexText.value = this.currentColor;
                this.options.onColorLive(this.currentColor);
            });
            colorInput.addEventListener('change', (e) => {
                this.currentColor = e.target.value;
                hexText.value = this.currentColor;
                this.options.onColorChange(this.currentColor);
            });
            
            hexText.addEventListener('change', (e) => {
                let val = e.target.value;
                if (!val.startsWith('#')) val = '#' + val;
                if (!/^#[0-9A-F]{6}$/i.test(val)) return; // ignore invalid manual typing
                this.currentColor = val;
                colorInput.value = this.currentColor;
                this.options.onColorChange(this.currentColor);
            });

            inputWrapper.appendChild(hexText);
            inputWrapper.appendChild(colorInput);
            colorRow.appendChild(labelArea);
            colorRow.appendChild(inputWrapper);
            wrapper.appendChild(colorRow);
        }

        // ─── Image Picker ───
        if (this.options.showImage) {
            if (this.options.showColor || this.options.showStyle) {
               const divider = document.createElement('div');
               divider.style.height = '1px';
               divider.style.background = 'var(--border)';
               wrapper.appendChild(divider);
            }

            const imgRow = document.createElement('div');
            imgRow.style.display = 'flex';
            imgRow.style.flexDirection = 'column';
            imgRow.style.gap = '8px';

            const labelArea = document.createElement('div');
            labelArea.innerHTML = `
                <div style="font-size: 13px; font-weight: 600; color: var(--text); display:flex; align-items:center; gap:6px;">
                    <i class="fas fa-image" style="color:var(--accent);"></i> ${this.options.imageLabel}
                </div>
            `;
            
            const btnGroup = document.createElement('div');
            btnGroup.style.display = 'flex';
            btnGroup.style.alignItems = 'center';
            btnGroup.style.gap = '8px';

            const nativePickerBtn = document.createElement('button');
            nativePickerBtn.type = 'button';
            nativePickerBtn.className = 'btn btn-sm btn-secondary';
            nativePickerBtn.title = 'Seleziona immagine dal sistema operativo';
            nativePickerBtn.innerHTML = '<i class="fas fa-folder-open"></i> Scegli file';
            
            const clearBtn = document.createElement('button');
            clearBtn.type = 'button';
            clearBtn.className = 'btn btn-sm btn-danger';
            clearBtn.innerHTML = '<i class="fas fa-trash"></i> Rimuovi';
            clearBtn.style.display = this.currentImage ? 'inline-block' : 'none';

            const pathPreview = document.createElement('div');
            pathPreview.style.fontSize = '11px';
            pathPreview.style.color = 'var(--muted)';
            pathPreview.style.wordBreak = 'break-all';
            pathPreview.innerText = this.currentImage ? this.currentImage.split('/').pop() : 'Nessuna immagine';

            nativePickerBtn.addEventListener('click', async () => {
                nativePickerBtn.disabled = true;
                const originalHtml = nativePickerBtn.innerHTML;
                nativePickerBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Attendere...';
                try {
                    const resp = await fetch('/api/system/explorer/pick-native', { method: 'POST' });
                    const data = await resp.json();
                    if (data.ok && data.path) {
                        this.currentImage = data.path;
                        pathPreview.innerText = data.path.split(/[\\/]/).pop();
                        clearBtn.style.display = 'inline-block';
                        this.options.onImageChange(this.currentImage);
                    }
                } catch (e) {
                    console.error("HecosAestheticPicker: OS Pick error", e);
                } finally {
                    nativePickerBtn.disabled = false;
                    nativePickerBtn.innerHTML = originalHtml;
                }
            });

            clearBtn.addEventListener('click', () => {
                this.currentImage = '';
                pathPreview.innerText = 'Nessuna immagine';
                clearBtn.style.display = 'none';
                this.options.onClearImage();
            });

            btnGroup.appendChild(nativePickerBtn);
            btnGroup.appendChild(clearBtn);
            
            imgRow.appendChild(labelArea);
            imgRow.appendChild(btnGroup);
            imgRow.appendChild(pathPreview);
            
            wrapper.appendChild(imgRow);

            // ─── Reset Button ───
            const resetArea = document.createElement('div');
            resetArea.style.marginTop = '4px';
            resetArea.style.textAlign = 'center';
            
            const resetBtn = document.createElement('button');
            resetBtn.type = 'button';
            resetBtn.className = 'btn btn-sm btn-reset';
            resetBtn.style.width = '100%';
            resetBtn.style.background = 'rgba(255, 255, 255, 0.05)';
            resetBtn.style.border = '1px solid rgba(255, 255, 255, 0.1)';
            resetBtn.style.color = 'var(--muted)';
            resetBtn.innerHTML = '<i class="fas fa-undo"></i> Reset to Default';
            
            resetBtn.addEventListener('mouseenter', () => {
                resetBtn.style.background = 'rgba(220, 53, 69, 0.1)';
                resetBtn.style.borderColor = '#dc3545';
                resetBtn.style.color = '#dc3545';
            });
            resetBtn.addEventListener('mouseleave', () => {
                resetBtn.style.background = 'rgba(255, 255, 255, 0.05)';
                resetBtn.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                resetBtn.style.color = 'var(--muted)';
            });

            resetBtn.addEventListener('click', () => {
                if (confirm('Ripristinare l\'aspetto predefinito del widget?')) {
                    this.options.onReset();
                }
            });

            resetArea.appendChild(resetBtn);
            wrapper.appendChild(resetArea);
        }

        this.container.appendChild(wrapper);
    }
}

// ─── Global Styling for Color Picker ───
if (!document.getElementById('hecos-aes-global-css')) {
    console.log("HECOS_AES_PICKER_V2_ACTIVE");
    const style = document.createElement('style');
    style.id = 'hecos-aes-global-css';
    style.innerHTML = `
        input[type="color"]::-webkit-color-swatch-wrapper { padding: 0; }
        input[type="color"]::-webkit-color-swatch { border: none; border-radius: 4px; }
        .hecos-aesthetic-wrapper .btn-secondary { background: var(--bg3); border: 1px solid var(--border); color: var(--text); }
        .hecos-aesthetic-wrapper .btn-secondary:hover { background: var(--accent); color: #000; }
        .hecos-aesthetic-wrapper .btn-danger { background: rgba(220, 53, 69, 0.23); border: 1px solid rgba(220, 53, 69, 0.4); color: #ff5c6c; }
        .hecos-aesthetic-wrapper .btn-danger:hover { background: #dc3545; color: #fff; }
        .hecos-aesthetic-wrapper .form-control { background: var(--bg2) !important; color: var(--text) !important; border-color: var(--border) !important; }
    `;
    document.head.appendChild(style);
}

window.HecosAestheticPicker = HecosAestheticPicker;
