class HecosAestheticStylePicker {
    static render(instance, wrapper) {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.flexDirection = 'column';
        row.style.gap = '6px';

        const label = document.createElement('div');
        label.innerHTML = `<div style="font-size: 13px; font-weight: 600; color: var(--text); display:flex; align-items:center; gap:6px;">
                            <i class="fas fa-paint-brush" style="color:var(--accent);"></i> ${instance.options.styleLabel}
                           </div>`;

        const select = document.createElement('select');
        select.className = 'form-control';
        select.style.fontSize = '12px';
        select.style.padding = '4px 8px';
        
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
            if (instance.currentStyle === t.val) opt.selected = true;
            select.appendChild(opt);
        });

        select.addEventListener('change', (e) => {
            instance.currentStyle = e.target.value;
            instance.options.onStyleChange(instance.currentStyle);
        });

        row.appendChild(label);
        row.appendChild(select);
        wrapper.appendChild(row);
    }
}
window.HecosAestheticStylePicker = HecosAestheticStylePicker;
