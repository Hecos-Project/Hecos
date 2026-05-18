class HecosAestheticColorPicker {
    static render(instance, wrapper) {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.flexDirection = 'column';
        row.style.gap = '10px';

        // Top Header line: Label + Reset
        const headerArea = document.createElement('div');
        headerArea.style.display = 'flex';
        headerArea.style.alignItems = 'center';
        headerArea.style.justifyContent = 'space-between';
        
        headerArea.innerHTML = `
            <div style="font-size: 13px; font-weight: 600; color: var(--text); display:flex; align-items:center; gap:6px;">
                <i class="fas fa-palette" style="color:var(--accent);"></i> ${instance.options.colorLabel}
            </div>
        `;

        const resetBtn = document.createElement('button');
        resetBtn.type = 'button';
        resetBtn.className = 'btn-reset-mini';
        resetBtn.title = 'Reset Colore';
        resetBtn.innerHTML = '<i class="fas fa-undo"></i>';
        resetBtn.addEventListener('click', () => instance.options.onReset(instance));
        
        // Manual Color Input Area
        const inputWrapper = document.createElement('div');
        inputWrapper.style.display = 'flex';
        inputWrapper.style.alignItems = 'center';
        inputWrapper.style.justifyContent = 'space-between'; // stretch select and inputs
        inputWrapper.style.gap = '8px';

        // -- Palette Dropdown --
        const paletteSelect = document.createElement('select');
        if (!instance.options.showPalette) paletteSelect.style.display = 'none';
        paletteSelect.className = 'form-control';
        paletteSelect.style.fontSize = '12px';
        paletteSelect.style.padding = '4px 8px';
        paletteSelect.style.flex = '1';
        
        const opts = [
            { val: 'none', label: 'Custom...' },
            { val: 'dark', label: 'Dark Palette' },
            { val: 'light', label: 'Light Palette' },
            { val: 'vibrant', label: 'Vibrant Palette' }
        ];
        opts.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o.val;
            opt.innerText = o.label;
            paletteSelect.appendChild(opt);
        });

        // -- Swatch Container --
        const swatchContainer = document.createElement('div');
        swatchContainer.className = 'aes-swatch-container';
        swatchContainer.style.display = 'none'; // Hidden by default

        // Handle palette selection
        paletteSelect.addEventListener('change', (e) => {
            const paletteKey = e.target.value;
            swatchContainer.innerHTML = '';
            if (paletteKey === 'none') {
                swatchContainer.style.display = 'none';
            } else {
                swatchContainer.style.display = 'flex';
                (window.HECOS_PALETTES[paletteKey] || []).forEach(color => {
                    const swatch = document.createElement('div');
                    swatch.title = color.label;
                    swatch.className = 'aes-swatch';
                    swatch.style.background = color.hex;
                    swatch.addEventListener('click', () => {
                        this.updateColorExternal(instance, color.hex);
                    });
                    swatchContainer.appendChild(swatch);
                });
            }
        });

        // -- Native native inputs --
        const controlsGroup = document.createElement('div');
        controlsGroup.style.display = 'flex';
        controlsGroup.style.gap = '6px';
        controlsGroup.style.alignItems = 'center';

        const hexText = document.createElement('input');
        if (instance.options.showHex) {
            hexText.type = 'text';
            hexText.className = 'form-control';
            hexText.style.width = '75px';
            hexText.style.fontSize = '11px';
            hexText.style.fontFamily = 'monospace';
            hexText.style.textAlign = 'center';
            hexText.value = instance.currentColor;
            
            hexText.addEventListener('change', (e) => {
                let val = e.target.value;
                if (!val.startsWith('#')) val = '#' + val;
                if (!/^#[0-9A-F]{6}$/i.test(val)) return;
                this.updateColorExternal(instance, val);
                paletteSelect.value = 'none';
                swatchContainer.style.display = 'none';
            });
            controlsGroup.appendChild(hexText);
        }
        instance.els.hexText = hexText;

        let safeColor = instance.currentColor || '#000000';
        if (!/^#[0-9A-F]{6}$/i.test(safeColor)) safeColor = '#000000';

        const colorInput = document.createElement('input');
        colorInput.type = 'color';
        colorInput.value = safeColor;
        colorInput.className = 'aes-color-input';
        
        colorInput.addEventListener('input', (e) => {
            instance.currentColor = e.target.value;
            if (instance.options.showHex) instance.els.hexText.value = instance.currentColor;
            instance.options.onColorLive(instance.currentColor);
        });
        colorInput.addEventListener('change', (e) => {
            instance.currentColor = e.target.value;
            if (instance.options.showHex) instance.els.hexText.value = instance.currentColor;
            instance.options.onColorChange(instance.currentColor);
            paletteSelect.value = 'none';
            swatchContainer.style.display = 'none';
        });
        instance.els.colorInput = colorInput;
        controlsGroup.appendChild(colorInput);
        
        headerArea.appendChild(resetBtn);
        inputWrapper.appendChild(paletteSelect);
        inputWrapper.appendChild(controlsGroup);

        row.appendChild(headerArea);
        row.appendChild(swatchContainer);
        row.appendChild(inputWrapper);
        wrapper.appendChild(row);
    }

    static updateColorExternal(instance, hex) {
        instance.currentColor = hex;
        instance.els.colorInput.value = hex;
        if (instance.options.showHex) instance.els.hexText.value = hex;
        instance.options.onColorChange(hex);
        instance.options.onColorLive(hex); 
    }
}
window.HecosAestheticColorPicker = HecosAestheticColorPicker;
