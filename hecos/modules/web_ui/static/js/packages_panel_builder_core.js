
window.builderLog = function(msg, type='info') {
    const term = document.getElementById('builder-terminal');
    console.log(`[Builder] ${msg}`);
    if (!term) return;
    
    const now = new Date();
    const time = now.getHours().toString().padStart(2,'0') + ':' + 
                 now.getMinutes().toString().padStart(2,'0') + ':' + 
                 now.getSeconds().toString().padStart(2,'0');
    
    let color = '#a3a3a3';
    let icon = '';
    if (type === 'error') { color = '#ef4444'; icon = 'fa-times-circle'; }
    if (type === 'success') { color = '#10b981'; icon = 'fa-check'; }
    if (type === 'warn') { color = '#f59e0b'; icon = 'fa-exclamation-triangle'; }
    
    const div = document.createElement('div');
    div.style.color = color;
    div.innerHTML = `<span style="color:#4b5563;">[${time}]</span> ${icon ? `<i class="fas ${icon}"></i> ` : ''}${msg}`;
    term.appendChild(div);
    term.scrollTop = term.scrollHeight;
};

// Package Builder Logic

let currentManifest = {};

// Use native Hecos Modal instead of browser alert
function _builderModal(msg, isError = true) {
    const titleEl = document.getElementById('hpm-info-modal-title');
    const textEl = document.getElementById('hpm-info-modal-text');
    const modal = document.getElementById('hpm-info-modal');
    
    if (titleEl && textEl && modal) {
        if (isError) {
            titleEl.innerHTML = '<i class="fas fa-exclamation-triangle" style="color:#ff4a4a; margin-right:8px;"></i>Builder Error';
        } else {
            titleEl.innerHTML = '<i class="fas fa-info-circle" style="color:#3b82f6; margin-right:8px;"></i>Builder Info';
        }
        textEl.innerHTML = msg;
        modal.style.display = 'flex';
    } else {
        console.error("Modal not found. Fallback:", msg);
        alert(msg);
    }
}

window.builderSourcesData = [];
window.builderActiveCategoryFilters = new Set();


window.builderLoadSetup = function() {
    const src = localStorage.getItem('hpm-builder-src') || 'C:\\\\Hecos-Packages\\\\sources';
    const dest = localStorage.getItem('hpm-builder-dest') || 'C:\\\\Hecos-Packages\\\\packages';
    const cli = localStorage.getItem('hpm-builder-cli') || 'C:\\\\Hecos-Packages\\\\Hecos_HPM_Builder';
    const priv = localStorage.getItem('hpm-builder-priv') || 'C:\\\\Hecos\\\\data\\\\trusted_keys\\\\hpm_private.pem';
    const pub = localStorage.getItem('hpm-builder-pub') || 'C:\\\\Hecos\\\\data\\\\trusted_keys';
    const unpackDest = localStorage.getItem('hpm-builder-unpack') || src;
    const hecos = localStorage.getItem('hpm-builder-hecos') || 'C:\\\\Hecos\\\\hecos';
    
    const srcEl = document.getElementById('builder-sources-root');
    const destEl = document.getElementById('builder-dest-root');
    const cliEl = document.getElementById('builder-cli-root');
    
    if (srcEl) srcEl.value = src;
    if (destEl) destEl.value = dest;
    if (cliEl) cliEl.value = cli;
    
    return {src, dest, cli, priv, pub, unpackDest, hecos};
};

window.builderSaveSetup = function() {
    const srcInput = document.getElementById('setup-sources-root') || document.getElementById('setup-src-root');
    const src = srcInput ? srcInput.value : '';
    const dest = document.getElementById('setup-dest-root') ? document.getElementById('setup-dest-root').value : '';
    const cli = document.getElementById('setup-cli-root') ? document.getElementById('setup-cli-root').value : '';
    const priv = document.getElementById('setup-private-key') ? document.getElementById('setup-private-key').value : '';
    const pub = document.getElementById('setup-public-keys') ? document.getElementById('setup-public-keys').value : '';
    
    if (src) localStorage.setItem('hpm-builder-src', src);
    if (dest) localStorage.setItem('hpm-builder-dest', dest);
    if (cli) localStorage.setItem('hpm-builder-cli', cli);
    if (priv) localStorage.setItem('hpm-builder-priv', priv);
    if (pub) localStorage.setItem('hpm-builder-pub', pub);
    const unpackDest = document.getElementById('setup-unpack-dest') ? document.getElementById('setup-unpack-dest').value : '';
    const hecos = document.getElementById('setup-hecos-root') ? document.getElementById('setup-hecos-root').value : '';
    if (unpackDest) localStorage.setItem('hpm-builder-unpack', unpackDest);
    if (hecos) localStorage.setItem('hpm-builder-hecos', hecos);
    
    window.builderLoadSetup();
    
    document.getElementById('hpm-builder-setup-modal').style.display='none';
    window.builderLog('Builder settings saved successfully.', 'success');
    window.builderRefreshSources();
};

window.builderOpenSetup = function() {
    const setup = window.builderLoadSetup();
    const srcInput = document.getElementById('setup-sources-root') || document.getElementById('setup-src-root');
    if(srcInput) srcInput.value = setup.src;
    if(document.getElementById('setup-dest-root')) document.getElementById('setup-dest-root').value = setup.dest;
    if(document.getElementById('setup-cli-root')) document.getElementById('setup-cli-root').value = setup.cli;
    if(document.getElementById('setup-private-key')) document.getElementById('setup-private-key').value = setup.priv;
    if(document.getElementById('setup-public-keys')) document.getElementById('setup-public-keys').value = setup.pub;
    if(document.getElementById('setup-unpack-dest')) document.getElementById('setup-unpack-dest').value = setup.unpackDest;
    if(document.getElementById('setup-hecos-root')) document.getElementById('setup-hecos-root').value = setup.hecos;
    
    document.getElementById('hpm-builder-setup-modal').style.display='flex';
};

// Auto load on init
setTimeout(window.builderLoadSetup, 500);

