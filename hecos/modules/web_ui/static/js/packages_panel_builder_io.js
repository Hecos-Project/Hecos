window.builderPickNativeImage = async function() {
    const dir = document.getElementById('builder-source-dir').value;
    if (!dir) {
        _builderModal("Please load a package directory first.", true);
        return;
    }
    try {
        const resp = await fetch('/api/system/explorer/pick-native', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                title: "Select Preview Image", 
                filetypes: [["PNG Images", "*.png"]] 
            })
        });
        const data = await resp.json();
        if (data && data.path) {
            const addResp = await fetch('/api/hpm/builder/add-image', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ src_dir: dir, image_path: data.path })
            });
            const addData = await addResp.json();
            if (!addData.ok) {
                _builderModal("Failed to add image: " + addData.error, true);
            } else {
                _builderUpdateImages(dir, addData.images);
            }
        }
    } catch (e) {
        console.error("Native image picker error", e);
    }
};

window.builderUploadImage = async function(event) {
    const dir = document.getElementById('builder-source-dir').value;
    if (!dir) {
        _builderModal("Please select a package directory first.", true);
        return;
    }
    
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('src_dir', dir);
    formData.append('file', file);
    
    try {
        const resp = await fetch('/api/hpm/builder/add-image-upload', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        if (!data.ok) {
            _builderModal("Failed to upload image: " + data.error, true);
        } else {
            _builderUpdateImages(dir, data.images);
        }
    } catch (e) {
        console.error("Image upload error", e);
    }
    event.target.value = ''; // Reset input
};

window.builderHandleFolderInput = function(e) {
    if (e.target.files && e.target.files.length > 0) {
        let packageNames = new Set();
        
        for (let i = 0; i < e.target.files.length; i++) {
            let f = e.target.files[i];
            if (f.webkitRelativePath && f.webkitRelativePath.endsWith('hpkg_manifest.toml')) {
                let parts = f.webkitRelativePath.split('/');
                if (parts.length >= 2) {
                    packageNames.add(parts[parts.length - 2]);
                }
            }
        }
        
        let packagesFound = Array.from(packageNames);
        
        if (packagesFound.length === 0) {
            let f = e.target.files[0];
            let folderName = f.webkitRelativePath ? f.webkitRelativePath.split('/')[0] : "";
            if (folderName) {
                _builderSelectFolderByName(folderName);
            } else {
                _builderModal("No packages found in this folder.", true);
            }
        } else if (packagesFound.length === 1) {
            _builderSelectFolderByName(packagesFound[0]);
        } else {
            _builderStartBatchMode(packagesFound);
        }
    }
    e.target.value = ''; 
};

window.builderHandleFolderDrop = function(e, element) {
    e.preventDefault();
    e.stopPropagation();
    element.style.borderColor = '';
    
    // Some browsers provide absolute path via f.path (like Electron)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        let f = e.dataTransfer.files[0];
        if (f.path) {
            let parts = f.path.split(/[\\/]/);
            _builderSelectFolderByName(parts[parts.length-1]);
        } else if (f.name) {
            // Drop in web browser might just give the folder name
            _builderSelectFolderByName(f.name);
        }
    }
};

window._builderSelectFolderByName = function(folderName) {
    if (!window.builderSourcesData) return;
    
    let found = window.builderSourcesData.find(src => src.rel_path.includes(folderName) || src.name.includes(folderName));
    
    if (found) {
        const baseDir = document.getElementById('builder-sources-root') ? document.getElementById('builder-sources-root').value : '';
        let d = baseDir;
        if (!d.endsWith("\\") && !d.endsWith("/")) d += "\\";
        document.getElementById('builder-source-dir').value = d + found.rel_path;
        
        window.builderLoadManifest();
        // Scroll removed because we have a fixed right pane
    } else {
        _builderModal("Folder '" + folderName + "' not found! Make sure it is located in the configured Sources root.", true);
    }
};

let currentPickerTarget = null;
let currentPickerPath = '';

window.builderPickSourcesRoot = function() {
    window.builderShowCustomPicker('builder-sources-root');
};

window.builderPickDestRoot = function() {
    window.builderShowCustomPicker('builder-dest-root');
};

window.builderShowCustomPicker = async function(targetId) {
    currentPickerTarget = targetId;
    const currentVal = document.getElementById(targetId).value;
    document.getElementById('hpm-folder-picker-modal').style.display = 'flex';
    
    if (currentVal && currentVal.length > 0) {
        await window.builderPickerLoad(currentVal);
    } else {
        await window.builderPickerLoadDrives();
    }
};

window.builderPickerLoadDrives = async function() {
    try {
        const resp = await fetch('/api/system/explorer/drives');
        const data = await resp.json();
        if (data && data.ok) {
            currentPickerPath = '';
            document.getElementById('hpm-picker-path').value = 'My Computer';
            const list = document.getElementById('hpm-picker-list');
            list.innerHTML = '';
            data.drives.forEach(drive => {
                const div = document.createElement('div');
                div.style = "padding:8px; cursor:pointer; border-radius:6px; display:flex; align-items:center; gap:8px;";
                div.onmouseover = () => div.style.background = 'var(--bg3)';
                div.onmouseout = () => div.style.background = 'transparent';
                div.onclick = () => window.builderPickerLoad(drive);
                div.innerHTML = `<i class="fas fa-hdd" style="color:var(--muted);"></i> <span style="color:var(--text);">${drive}</span>`;
                list.appendChild(div);
            });
        }
    } catch (e) { console.error(e);
        window.builderLog('An unexpected error occurred: ' + e.message, 'error'); }
};

window.builderPickerLoad = async function(path) {
    try {
        const resp = await fetch('/api/system/explorer/ls', {
            method: 'POST',
            body: JSON.stringify({path: path})
        });
        const data = await resp.json();
        if (data && data.ok) {
            currentPickerPath = path;
            document.getElementById('hpm-picker-path').value = path;
            const list = document.getElementById('hpm-picker-list');
            list.innerHTML = '';
            
            let dirs = data.entries ? data.entries.filter(e => e.type === 'dir') : [];
            dirs.sort((a,b) => a.name.localeCompare(b.name));
            
            if (dirs.length === 0) {
                list.innerHTML = '<div style="padding:16px; color:var(--muted); text-align:center;">No subfolders</div>';
            }
            
            dirs.forEach(d => {
                const div = document.createElement('div');
                div.style = "padding:8px; cursor:pointer; border-radius:6px; display:flex; align-items:center; gap:8px;";
                div.onmouseover = () => div.style.background = 'var(--bg3)';
                div.onmouseout = () => div.style.background = 'transparent';
                div.onclick = () => window.builderPickerLoad(d.path);
                div.innerHTML = `<i class="fas fa-folder" style="color:var(--accent);"></i> <span style="color:var(--text);">${d.name}</span>`;
                list.appendChild(div);
            });
        } else {
            await window.builderPickerLoadDrives();
        }
    } catch (e) { console.error(e);
        window.builderLog('An unexpected error occurred: ' + e.message, 'error'); }
};

window.builderPickerUp = async function() {
    if (!currentPickerPath) return; 
    let parts = currentPickerPath.replace(/\\/g, '/').split('/').filter(p => p.length > 0);
    if (parts.length <= 1) {
        await window.builderPickerLoadDrives();
    } else {
        parts.pop();
        let upPath = parts.join('\\');
        if (upPath.length === 2 && upPath.endsWith(':')) upPath += '\\';
        await window.builderPickerLoad(upPath);
    }
};

window.builderPickerConfirm = function() {
    if (currentPickerPath && currentPickerTarget) {
        document.getElementById(currentPickerTarget).value = currentPickerPath;
        if (currentPickerTarget === 'builder-sources-root') {
            window.builderRefreshSources();
        }
    }
    document.getElementById('hpm-folder-picker-modal').style.display = 'none';
};
