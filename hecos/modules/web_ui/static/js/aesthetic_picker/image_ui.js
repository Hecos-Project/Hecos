class HecosAestheticImagePicker {
    static render(instance, wrapper) {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.flexDirection = 'column';
        row.style.gap = '8px';

        const topArea = document.createElement('div');
        topArea.style.display = 'flex';
        topArea.style.alignItems = 'center';
        topArea.style.justifyContent = 'space-between';

        const label = document.createElement('div');
        label.innerHTML = `<div style="font-size: 13px; font-weight: 600; color: var(--text); display:flex; align-items:center; gap:6px;">
                            <i class="fas fa-image" style="color:var(--accent);"></i> ${instance.options.imageLabel}
                           </div>`;

        const resetBtn = document.createElement('button');
        resetBtn.type = 'button';
        resetBtn.className = 'btn-reset-mini';
        resetBtn.title = 'Reset Immagine';
        resetBtn.innerHTML = '<i class="fas fa-undo"></i>';
        resetBtn.addEventListener('click', () => instance.options.onReset(instance));

        topArea.appendChild(label);
        topArea.appendChild(resetBtn);

        const btnGroup = document.createElement('div');
        btnGroup.style.display = 'flex';
        btnGroup.style.alignItems = 'center';
        btnGroup.style.gap = '8px';

        const nativePickerBtn = document.createElement('button');
        nativePickerBtn.type = 'button';
        nativePickerBtn.className = 'btn btn-sm btn-secondary';
        nativePickerBtn.innerHTML = '<i class="fas fa-folder-open"></i> Scegli file';
        
        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'btn btn-sm btn-danger';
        clearBtn.innerHTML = '<i class="fas fa-trash"></i> Rimuovi';
        clearBtn.style.display = instance.currentImage ? 'inline-block' : 'none';

        const pathPreview = document.createElement('div');
        pathPreview.style.fontSize = '11px';
        pathPreview.style.color = 'var(--muted)';
        pathPreview.style.wordBreak = 'break-all';
        pathPreview.innerText = instance.currentImage ? instance.currentImage.split(/[\\/]/).pop() : 'Nessuna immagine';

        nativePickerBtn.addEventListener('click', async () => {
            nativePickerBtn.disabled = true;
            const originalHtml = nativePickerBtn.innerHTML;
            nativePickerBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Attendere...';
            try {
                const resp = await fetch('/api/system/explorer/pick-native', { method: 'POST' });
                const data = await resp.json();
                if (data.ok && data.path) {
                    instance.currentImage = data.path;
                    pathPreview.innerText = data.path.split(/[\\/]/).pop();
                    clearBtn.style.display = 'inline-block';
                    instance.options.onImageChange(instance.currentImage);
                }
            } catch (e) {
                console.error("HecosAestheticPicker: OS Pick error", e);
            } finally {
                nativePickerBtn.disabled = false;
                nativePickerBtn.innerHTML = originalHtml;
            }
        });

        clearBtn.addEventListener('click', () => {
            instance.currentImage = '';
            pathPreview.innerText = 'Nessuna immagine';
            clearBtn.style.display = 'none';
            instance.options.onClearImage();
        });

        btnGroup.appendChild(nativePickerBtn);
        btnGroup.appendChild(clearBtn);
        
        row.appendChild(topArea);
        row.appendChild(btnGroup);
        row.appendChild(pathPreview);
        
        wrapper.appendChild(row);
    }
}
window.HecosAestheticImagePicker = HecosAestheticImagePicker;
