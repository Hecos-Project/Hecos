class HecosAestheticPicker {
    constructor(containerEl, options) {
        this.container = typeof containerEl === 'string' ? document.getElementById(containerEl) : containerEl;
        this.options = Object.assign({
            initialColor: '',
            initialImage: '',
            initialStyle: 'default',
            showColor: true,
            showImage: true,
            showStyle: false,
            showHex: false,
            showPalette: true,
            colorLabel: 'Colore Sfondo',
            imageLabel: 'Immagine Sfondo',
            styleLabel: 'Tema Pannello',
            onColorChange: (val) => {},
            onColorLive: (val) => {},
            onImageChange: (path) => {},
            onClearImage: () => {},
            onStyleChange: (val) => {},
            onReset: (instance) => {}
        }, options);

        this.currentColor = this.options.initialColor;
        this.currentImage = this.options.initialImage;
        this.currentStyle = this.options.initialStyle;
        
        // HTML Element References
        this.els = {};

        this.render();
    }

    render() {
        this.container.innerHTML = '';
        
        const wrapper = document.createElement('div');
        wrapper.className = 'hecos-aesthetic-wrapper card';
        wrapper.style.padding = '12px 16px';
        wrapper.style.display = 'flex';
        wrapper.style.flexDirection = 'column';
        wrapper.style.gap = '14px';
        wrapper.style.marginBottom = '0';
        wrapper.style.background = 'var(--bg2)';

        if (this.options.showStyle && window.HecosAestheticStylePicker) {
            window.HecosAestheticStylePicker.render(this, wrapper);
        }

        if (this.options.showColor && this.options.showStyle) {
           this._renderDivider(wrapper);
        }

        if (this.options.showColor && window.HecosAestheticColorPicker) {
            window.HecosAestheticColorPicker.render(this, wrapper);
        }

        if (this.options.showImage) {
            if (this.options.showColor || this.options.showStyle) {
               this._renderDivider(wrapper);
            }
            if (window.HecosAestheticImagePicker) {
                window.HecosAestheticImagePicker.render(this, wrapper);
            }
        }

        this.container.appendChild(wrapper);
    }

    _renderDivider(parent) {
        const divider = document.createElement('div');
        divider.style.height = '1px';
        divider.style.background = 'var(--border)';
        divider.style.margin = '4px 0';
        parent.appendChild(divider);
    }
}

if (!document.getElementById('hecos-aes-global-css')) {
    const style = document.createElement('style');
    style.id = 'hecos-aes-global-css';
    style.innerHTML = `
        input[type="color"].aes-color-input::-webkit-color-swatch-wrapper { padding: 0; }
        input[type="color"].aes-color-input::-webkit-color-swatch { border: none; border-radius: 4px; }
        input[type="color"].aes-color-input {
            cursor: pointer;
            border: 1px solid var(--border);
            width: 34px;
            height: 34px;
            padding: 2px;
            border-radius: 6px;
            background: var(--bg3);
            box-sizing: border-box;
            appearance: none;
            -webkit-appearance: none;
        }

        .hecos-aesthetic-wrapper .btn-secondary { background: var(--bg3); border: 1px solid var(--border); color: var(--text); }
        .hecos-aesthetic-wrapper .btn-secondary:hover { background: var(--accent); color: #000; }
        .hecos-aesthetic-wrapper .btn-danger { background: rgba(220, 53, 69, 0.23); border: 1px solid rgba(220, 53, 69, 0.4); color: #ff5c6c; }
        .hecos-aesthetic-wrapper .btn-danger:hover { background: #dc3545; color: #fff; }
        .hecos-aesthetic-wrapper .form-control { background: var(--bg2) !important; color: var(--text) !important; border-color: var(--border) !important; }
        
        .btn-reset-mini { 
            background: rgba(255, 255, 255, 0.05); 
            border: 1px solid rgba(255, 255, 255, 0.1); 
            color: var(--muted); 
            border-radius: 6px;
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 10px;
        }
        .btn-reset-mini:hover {
            background: rgba(108, 140, 255, 0.1);
            border-color: var(--accent);
            color: var(--accent);
            transform: rotate(-30deg);
        }

        .aes-swatch-container {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            padding: 8px;
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
            border: 1px solid var(--border);
        }
        .aes-swatch {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            cursor: pointer;
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .aes-swatch:hover {
            transform: scale(1.15);
            box-shadow: 0 0 6px var(--accent);
            border-color: white;
        }
    `;
    document.head.appendChild(style);
}

window.HecosAestheticPicker = HecosAestheticPicker;
