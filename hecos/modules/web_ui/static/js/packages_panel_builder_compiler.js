window.builderRunBuild = async function(autoInstall = false) {
    const dir = document.getElementById('builder-source-dir').value;
    if (!dir) {
        _builderModal("Please select a directory first.", true);
        return;
    }

    currentManifest.id = document.getElementById('builder-id').value;
    currentManifest.name = document.getElementById('builder-name').value;
    currentManifest.version = document.getElementById('builder-version').value;
    currentManifest.author = document.getElementById('builder-author').value;
    currentManifest.type = document.getElementById('builder-type').value;
    currentManifest.license = document.getElementById('builder-license').value;
    currentManifest.date = document.getElementById('builder-date').value;
    currentManifest.description = document.getElementById('builder-desc').value;

    const btn = document.getElementById('builder-btn-build');
    const oldText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> BUILDING...';
    btn.disabled = true;
    
    window.builderLog(`Starting build process for ${currentManifest.name}...`, 'warn');
    window.builderLog(`Source Directory: ${dir}`, 'info');

    try {
        const outDir = document.getElementById('builder-dest-root') ? document.getElementById('builder-dest-root').value : '';
        const cliDir = window.builderLoadSetup().cli;
        const response = await fetch('/api/hpm/builder/build', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ src_dir: dir, manifest: currentManifest, out_dir: outDir, builder_cli_dir: cliDir })
        });
        const data = await response.json();
        
        const printLogs = (logs) => {
            if (!logs) return;
            logs.split('\n').forEach(l => {
                if (l.trim() && !l.includes("FINAL_OUT_DIR=")) {
                    if (l.includes("[ERROR]")) window.builderLog(l, "error");
                    else if (l.includes("[WARN]")) window.builderLog(l, "warning");
                    else window.builderLog(l, "info");
                }
            });
        };

        if (data) printLogs(data.logs);
        
        if (!data || !data.ok) {
            _builderModal("BUILD FAILED: " + (data ? data.error : "Unknown error"), true);
            window.builderLog(`Build Failed: ${data ? data.error : 'Unknown error'}`, 'error');
        } else {
            // Success Animation
            window.builderLog(`Package successfully built and saved!`, 'success');
            if (data.out_dir) {
                const link = `<a href="javascript:void(0)" onclick="window.builderOpenFolder('${data.out_dir.replace(/\\/g, '\\\\')}')" style="color:#60a5fa; text-decoration:underline;"><i class="fas fa-folder-open"></i> ${data.out_dir}</a>`;
                window.builderLog(`Destination: ${link}`, 'info');
            } else if (data.out_path) {
                window.builderLog(`Saved to: ${data.out_path}`, 'info');
            }
            
        }
        
        if (data && data.ok && autoInstall) {
            window.builderLog('Auto-install requested. Triggering Dev Sync...', 'info');
            if (typeof window.builderDevSync === 'function') {
                await window.builderDevSync();
            }
        }
    } catch (e) {
        console.error(e);
        window.builderLog('An unexpected error occurred: ' + e.message, 'error');
        _builderModal("Error connecting to Hecos Backend: " + e.message, true);
    } finally {
        btn.innerHTML = oldText;
        btn.disabled = false;
    }
};





window._builderStartBatchMode = function(packagesList) {
    const msg = `You selected a folder containing <b>${packagesList.length} packages</b>.<br><br>` + 
                `Do you want to launch a <b>Batch Build</b> for all these packages at once?`;
                
    // Show a confirm-style UI inside the info modal
    const titleEl = document.getElementById('hpm-info-modal-title');
    const textEl = document.getElementById('hpm-info-modal-text');
    const modal = document.getElementById('hpm-info-modal');
    
    titleEl.innerHTML = '<i class="fas fa-layer-group" style="color:#10b981; margin-right:8px;"></i>Batch Build Mode';
    textEl.innerHTML = msg + `<br><br><div style="display:flex; gap:8px; justify-content:center;">
        <button class="btn btn-primary" onclick="window._executeBatchBuild('${packagesList.join(",")}')">YES, BATCH BUILD ALL</button>
    </div>`;
    modal.style.display = 'flex';
};

window._executeBatchBuild = async function(packagesCsv) {
    document.getElementById('hpm-info-modal').style.display = 'none';
    const packagesList = packagesCsv.split(',');
    
    const outDir = document.getElementById('builder-dest-root') ? document.getElementById('builder-dest-root').value : '';
    const srcRoot = document.getElementById('builder-sources-root') ? document.getElementById('builder-sources-root').value : '';
    
    _builderModal(`Starting Batch Build for ${packagesList.length} packages... please wait.`, false);
    window.builderLog(`Initiating Batch Build for ${packagesList.length} targets...`, 'warn');
    
    try {
        const response = await fetch('/api/hpm/builder/batch-build', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ packages: packagesList, out_dir: outDir, base_dir: srcRoot })
        });
        const data = await response.json();
        
        if (!data.ok) {
            _builderModal("ERRORE BATCH BUILD: " + (data.error || "Unknown"), true);
        } else {
            _builderModal(`<b>Batch Build Completed!</b><br><br>Success: ${data.success_count}<br>Failed: ${data.fail_count}<br>Check the logs for details.`, false);
            window.builderLog(`Batch Build Completed. Success: ${data.success_count}, Failed: ${data.fail_count}`, data.fail_count > 0 ? 'warn' : 'success');
        }
    } catch (e) {
        console.error(e);
        window.builderLog('An unexpected error occurred: ' + e.message, 'error');
        _builderModal("Error connecting to Hecos Backend: " + e.message, true);
    }
};


window.builderOpenFolder = async function(path) {
    try {
        await fetch('/api/hpm/builder/open-folder', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ path: path })
        });
    } catch(e) {}
};

window.builderGenerateKeys = async function() {
    window.builderLog('Starting RSA/Ed25519 Keys Generation...', 'warn');
    const setup = window.builderLoadSetup();
    const cliDir = setup.cli;
    try {
        const resp = await fetch('/api/hpm/builder/keys', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                builder_cli_dir: cliDir,
                builder_priv_key: setup.priv,
                builder_pub_key: setup.pub
            })
        });
        const data = await resp.json();
        if (data.logs) {
            data.logs.split('\n').forEach(l => {
                if (l.trim()) window.builderLog(l.trim(), l.includes('Error') || l.includes('Failed') ? 'error' : 'info');
            });
        }
        if (data.ok) {
            window.builderLog('Keys successfully generated and saved in CLI root.', 'success');
            _builderModal("Keys Generated Successfully!", false);
        } else {
            window.builderLog('Keys Generation Failed: ' + data.error, 'error');
            _builderModal("Keys Generation Failed: " + data.error, true);
        }
    } catch(e) {
        window.builderLog('Error: ' + e.message, 'error');
    }
};

window.builderGenerateCatalog = async function() {
    window.builderLog('Starting Store Catalog Generation...', 'warn');
    const cliDir = window.builderLoadSetup().cli;
    try {
        const resp = await fetch('/api/hpm/builder/catalog', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ builder_cli_dir: cliDir })
        });
        const data = await resp.json();
        if (data.logs) {
            data.logs.split('\n').forEach(l => {
                if (l.trim()) window.builderLog(l.trim(), l.includes('Error') || l.includes('Failed') ? 'error' : 'info');
            });
        }
        if (data.ok) {
            window.builderLog('Store Catalog successfully generated.', 'success');
            _builderModal("Catalog Generated Successfully!", false);
        } else {
            window.builderLog('Catalog Generation Failed: ' + data.error, 'error');
            _builderModal("Catalog Generation Failed: " + data.error, true);
        }
    } catch(e) {
        window.builderLog('Error: ' + e.message, 'error');
    }
};

// ─── Helper: get the currently selected package .hpkg path ───────────────────
function _getPackagesDir() {
    return window.builderLoadSetup().dest || 'C:\\Hecos-Packages\\packages';
}

// ─── Dev Sync ─────────────────────────────────────────────────────────────────
window.builderDevSync = async function() {
    const srcDir = document.getElementById('builder-source-dir') ? document.getElementById('builder-source-dir').value : '';
    if (!srcDir) {
        _builderModal("Please select a package first.", true);
        return;
    }
    const setup = window.builderLoadSetup();
    window.builderLog(`Dev Sync: syncing ${currentManifest.name || srcDir} to live installation...`, 'warn');
    try {
        const resp = await fetch('/api/hpm/builder/dev-sync', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                src_dir: srcDir,
                hecos_root: setup.hecos || 'C:\\Hecos\\hecos'
            })
        });
        const data = await resp.json();
        if (data.logs) {
            data.logs.split('\n').forEach(l => {
                if (l.trim()) window.builderLog(l.trim(), l.includes('Error') || l.includes('error') ? 'error' : 'info');
            });
        }
        if (data.ok) {
            window.builderLog(`Dev Sync completed for ${currentManifest.name || 'package'}.`, 'success');
        } else {
            window.builderLog('Dev Sync Failed: ' + data.error, 'error');
            _builderModal("Dev Sync Failed:\n" + data.error, true);
        }
    } catch(e) {
        window.builderLog('Error: ' + e.message, 'error');
    }
};

// ─── Inspect ──────────────────────────────────────────────────────────────────
window.builderInspect = async function() {
    if (!currentManifest.id) {
        _builderModal("Please select a package first.", true);
        return;
    }
    const setup = window.builderLoadSetup();
    window.builderLog(`Inspecting package: ${currentManifest.id}...`, 'warn');
    try {
        const resp = await fetch('/api/hpm/builder/inspect', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ pkg_id: currentManifest.id, packages_dir: setup.dest })
        });
        const data = await resp.json();
        if (!data.ok) {
            window.builderLog('Inspect Failed: ' + data.error, 'error');
            _builderModal("Inspect Failed:\n" + data.error + "\n\nMake sure you have built the package first.", true);
            return;
        }
        const m = data.manifest || {};
        const cap = m.capabilities || {};
        const sigBadge = data.has_signature 
            ? `<span style="background:rgba(16,185,129,0.15); color:#10b981; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(16,185,129,0.3);"><i class="fas fa-lock"></i> Signed</span>`
            : `<span style="background:rgba(239,68,68,0.15); color:#ef4444; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(239,68,68,0.3);"><i class="fas fa-exclamation-triangle"></i> Unsigned</span>`;
        
        let html = `
          <div style="text-align:left; font-size:13px; line-height:1.5;">
            <div style="margin-bottom:10px;">
              <span style="display:inline-block; padding:2px 6px; background:var(--bg3, #2a2a35); border-radius:4px; font-weight:bold; font-size:11px; margin-right:6px;">${(m.type || 'plugin').toUpperCase()}</span>
              <span style="font-size:16px; font-weight:bold; color:var(--text);">${m.name || 'Unknown'} <span style="opacity:0.5;font-weight:normal;font-size:12px;">v${m.version || '0.0.0'}</span></span>
            </div>
            
            <table style="width:100%; border-collapse:collapse; margin-bottom:15px;">
              <tr style="border-bottom:1px solid var(--border-color);">
                <td style="padding:6px 0; color:var(--muted); width:40%;">ID</td>
                <td style="padding:6px 0; font-weight:500;">${m.id || 'N/A'}</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-color);">
                <td style="padding:6px 0; color:var(--muted);">Author</td>
                <td style="padding:6px 0; font-weight:500;">${m.author || 'Unknown'}</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-color);">
                <td style="padding:6px 0; color:var(--muted);">License</td>
                <td style="padding:6px 0; font-weight:500;">${m.license || 'N/A'}</td>
              </tr>
              <tr style="border-bottom:1px solid var(--border-color);">
                <td style="padding:6px 0; color:var(--muted);">Archive Info</td>
                <td style="padding:6px 0;">${sigBadge} <span style="margin-left:8px; color:var(--muted);"><i class="fas fa-folder-open"></i> ${data.file_count} files &nbsp;|&nbsp; <i class="fas fa-hdd"></i> ${data.size_kb} KB</span></td>
              </tr>
            </table>

            <div style="margin-bottom:15px;">
              <div style="font-weight:bold; margin-bottom:6px; color:var(--text);">Capabilities:</div>
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:6px;">
                <div><span style="color:var(--muted);">Widget:</span> ${cap.has_widget ? '<span style="color:#10b981;">Yes</span>' : 'No'}</div>
                <div><span style="color:var(--muted);">Config Panel:</span> ${cap.has_config_panel ? '<span style="color:#10b981;">Yes</span>' : 'No'}</div>
                <div><span style="color:var(--muted);">API Routes:</span> ${cap.has_api_routes ? '<span style="color:#10b981;">Yes</span>' : 'No'}</div>
                <div><span style="color:var(--muted);">System Calls:</span> ${cap.has_system_calls ? '<span style="color:#10b981;">Yes</span>' : 'No'}</div>
              </div>
            </div>
        `;

        if (cap.llm_tools && cap.llm_tools.length > 0) {
          html += `
            <div style="margin-bottom:10px;">
              <div style="font-weight:bold; margin-bottom:4px;">LLM Tools:</div>
              <div style="display:flex; flex-wrap:wrap; gap:5px;">
                ${cap.llm_tools.map(t => `<span style="background:rgba(59,130,246,0.15); color:#3b82f6; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(59,130,246,0.3);">${t}</span>`).join('')}
              </div>
            </div>
          `;
        }

        if (cap.slash_commands && cap.slash_commands.length > 0) {
          html += `
            <div style="margin-bottom:10px;">
              <div style="font-weight:bold; margin-bottom:4px;">Slash Commands:</div>
              <div style="display:flex; flex-wrap:wrap; gap:5px;">
                ${cap.slash_commands.map(cmd => `<span style="background:rgba(236,72,153,0.15); color:#ec4899; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(236,72,153,0.3);">${cmd}</span>`).join('')}
              </div>
            </div>
          `;
        }
        
        html += `
            <div style="margin-top:15px; padding:10px; background:var(--bg2); border-radius:6px; border:1px solid var(--border-color); font-family:monospace; font-size:11px; color:var(--muted); word-break:break-all;">
              <i class="fas fa-file-archive"></i> ${data.hpkg_path.replace(/\\/g, '\\\\')}
            </div>
          </div>
        `;

        window.builderLog(`Inspect OK: ${data.file_count} files, ${data.size_kb} KB, ${data.has_signature ? 'signed' : 'unsigned'}`, 'success');
        _builderModal(html, false);
    } catch(e) {
        window.builderLog('Error: ' + e.message, 'error');
    }
};

// ─── Unpack ───────────────────────────────────────────────────────────────────
window.builderUnpack = async function() {
    if (!currentManifest.id) {
        _builderModal("Please select a package first.", true);
        return;
    }
    const setup = window.builderLoadSetup();
    const unpackDest = setup.unpackDest || setup.src || 'C:\\Hecos-Packages\\sources';
    window.builderLog(`Unpacking ${currentManifest.id}...`, 'warn');
    window.builderLog(`Packages dir: ${setup.dest} | Destination root: ${unpackDest}`, 'info');
    try {
        const resp = await fetch('/api/hpm/builder/unpack', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                builder_cli_dir: setup.cli,
                pkg_id: currentManifest.id,
                packages_dir: setup.dest,
                unpack_dest: unpackDest,
                src_dir_root: setup.src
            })
        });
        const data = await resp.json();
        if (data.logs) {
            data.logs.split('\n').forEach(l => {
                if (l.trim()) window.builderLog(l.trim(), l.includes('Error') || l.includes('error') ? 'error' : 'info');
            });
        }
        if (data.ok) {
            const link = `<a href="javascript:void(0)" onclick="window.builderOpenFolder('${unpackDest.replace(/\\/g, '\\\\')}')" style="color:#60a5fa; text-decoration:underline;"><i class="fas fa-folder-open"></i> ${unpackDest}</a>`;
            window.builderLog(`Unpack completed. Source folder: ` + link, 'success');
            _builderModal(`Package unpacked into:\n${unpackDest}`, false);
        } else {
            window.builderLog('Unpack Failed: ' + data.error, 'error');
            _builderModal("Unpack Failed:\n" + data.error, true);
        }
    } catch(e) {
        window.builderLog('Error: ' + e.message, 'error');
    }
};

// ─── Auto-Capabilities (all packages) ─────────────────────────────────────────
window.builderAutoCapabilities = async function() {
    const setup = window.builderLoadSetup();
    window.builderLog('Auto-Capabilities: regenerating for ALL packages...', 'warn');
    try {
        const resp = await fetch('/api/hpm/builder/capabilities', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ builder_cli_dir: setup.cli, src_root: setup.src })
        });
        const data = await resp.json();
        if (data.logs) {
            data.logs.split('\n').forEach(l => {
                if (l.trim()) window.builderLog(l.trim(), l.includes('Error') || l.includes('error') ? 'error' : 'info');
            });
        }
        if (data.ok) window.builderLog('Auto-Capabilities completed for all packages.', 'success');
        else { window.builderLog('Auto-Capabilities failed: ' + data.error, 'error'); _builderModal("Auto-Capabilities Failed:\n" + data.error, true); }
    } catch(e) { window.builderLog('Error: ' + e.message, 'error'); }
};

// ─── Single Package Capabilities ─────────────────────────────────────────────
window.builderRegenCapabilities = async function() {
    const srcDir = document.getElementById('builder-source-dir') ? document.getElementById('builder-source-dir').value : '';
    if (!srcDir || !currentManifest.id) {
        _builderModal("Please select a package first.", true);
        return;
    }
    const setup = window.builderLoadSetup();
    window.builderLog(`Regenerating capabilities for ${currentManifest.name || currentManifest.id}...`, 'warn');
    try {
        const resp = await fetch('/api/hpm/builder/capabilities', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ builder_cli_dir: setup.cli, src_dir: srcDir, src_root: setup.src })
        });
        const data = await resp.json();
        if (data.logs) {
            data.logs.split('\n').forEach(l => {
                if (l.trim()) window.builderLog(l.trim(), l.includes('Error') || l.includes('error') ? 'error' : 'info');
            });
        }
        if (data.ok) {
            window.builderLog(`Capabilities regenerated for ${currentManifest.name}.`, 'success');
            // Re-load the manifest so we have the latest capabilities in currentManifest
            if (window.builderLoadManifest) window.builderLoadManifest(srcDir);
        } else { 
            window.builderLog('Capabilities failed: ' + data.error, 'error'); 
            _builderModal("Capabilities Failed:\n" + data.error, true); 
        }
    } catch(e) { window.builderLog('Error: ' + e.message, 'error'); }
};

// ─── View Capabilities (from Manifest) ───────────────────────────────────────
window.builderViewCapabilities = function() {
    if (!currentManifest.id) {
        _builderModal("Please select a package first.", true);
        return;
    }

    const c = {
        type: currentManifest.type || 'plugin',
        name: currentManifest.name || 'Unknown',
        version: currentManifest.version || '0.0.0',
        description: currentManifest.description || '',
        author: currentManifest.author || 'Unknown',
        has_widget: (currentManifest.capabilities || {}).has_widget || false,
        has_config_panel: (currentManifest.capabilities || {}).has_config_panel || false,
        has_api_routes: (currentManifest.capabilities || {}).has_api_routes || false,
        has_system_calls: (currentManifest.capabilities || {}).has_system_calls || false,
        llm_tools: (currentManifest.capabilities || {}).llm_tools || [],
        slash_commands: (currentManifest.capabilities || {}).slash_commands || [],
        dependencies: currentManifest.dependencies || [],
        pip_requirements: currentManifest.pip_requirements || [],
        syscall_notes: (currentManifest.capabilities || {}).syscall_notes || '',
        notes: (currentManifest.capabilities || {}).notes || ''
    };

    let html = `
      <div style="text-align:left; font-size:13px; line-height:1.5;">
        <div style="margin-bottom:10px;">
          <span style="display:inline-block; padding:2px 6px; background:var(--bg3, #2a2a35); border-radius:4px; font-weight:bold; font-size:11px; margin-right:6px;">${c.type.toUpperCase()}</span>
          <span style="font-size:16px; font-weight:bold; color:var(--text);">${c.name} <span style="opacity:0.5;font-weight:normal;font-size:12px;">v${c.version}</span></span>
        </div>
        <p style="color:var(--muted); margin-bottom:15px; font-size:14px;">${c.description}</p>
        
        <table style="width:100%; border-collapse:collapse; margin-bottom:15px;">
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted); width:40%;">Author</td>
            <td style="padding:6px 0; font-weight:500;">${c.author || 'Unknown'}</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted);">Has Widget</td>
            <td style="padding:6px 0;">${c.has_widget ? '<span style="color:#10b981;">Yes</span>' : 'No'}</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted);">Config Panel</td>
            <td style="padding:6px 0;">${c.has_config_panel ? '<span style="color:#10b981;">Yes</span>' : 'No'}</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted);">API Routes</td>
            <td style="padding:6px 0;">${c.has_api_routes ? '<span style="color:#10b981;">Yes</span>' : 'No'}</td>
          </tr>
          <tr style="border-bottom:1px solid var(--border-color);">
            <td style="padding:6px 0; color:var(--muted);">System Calls</td>
            <td style="padding:6px 0;">${c.has_system_calls ? '<span style="color:#10b981;">Yes</span>' : 'No'}</td>
          </tr>
        </table>
    `;

    if (c.llm_tools && c.llm_tools.length > 0) {
      html += `
        <div style="margin-bottom:10px;">
          <div style="font-weight:bold; margin-bottom:4px;">LLM Tools:</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">
            ${c.llm_tools.map(t => `<span style="background:rgba(59,130,246,0.15); color:#3b82f6; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(59,130,246,0.3);">${t}</span>`).join('')}
          </div>
        </div>
      `;
    }

    if (c.slash_commands && c.slash_commands.length > 0) {
      html += `
        <div style="margin-bottom:10px;">
          <div style="font-weight:bold; margin-bottom:4px;">Slash Commands:</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">
            ${c.slash_commands.map(cmd => `<span style="background:rgba(236,72,153,0.15); color:#ec4899; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(236,72,153,0.3);">${cmd}</span>`).join('')}
          </div>
        </div>
      `;
    }

    if (c.dependencies && c.dependencies.length > 0) {
      html += `
        <div style="margin-bottom:10px;">
          <div style="font-weight:bold; margin-bottom:4px; color:#60a5fa;">Dependencies (Hecos):</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">
            ${c.dependencies.map(d => `<span style="background:rgba(59,130,246,0.15); color:#60a5fa; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(59,130,246,0.3);">${window._hesc ? window._hesc(d) : d}</span>`).join('')}
          </div>
        </div>
      `;
    }

    if (c.pip_requirements && c.pip_requirements.length > 0) {
      html += `
        <div style="margin-bottom:10px;">
          <div style="font-weight:bold; margin-bottom:4px; color:#fbbf24;">Dependencies (PIP):</div>
          <div style="display:flex; flex-wrap:wrap; gap:5px;">
            ${c.pip_requirements.map(p => {
        let clean = p.split('==')[0].split('>=')[0];
        return `<span style="background:rgba(245,158,11,0.15); color:#fbbf24; padding:2px 6px; border-radius:4px; font-size:11px; border:1px solid rgba(245,158,11,0.3);">${window._hesc ? window._hesc(clean) : clean}</span>`;
      }).join('')}
          </div>
        </div>
      `;
    }

    if (c.syscall_notes || c.notes) {
      html += `<div style="margin-top:15px; padding:10px; background:var(--bg2); border-radius:6px; border:1px solid var(--border-color);">`;
      if (c.syscall_notes) html += `<div style="margin-bottom:6px;"><strong>Syscalls:</strong> <span style="color:var(--muted);">${c.syscall_notes}</span></div>`;
      if (c.notes) html += `<div><strong>Notes:</strong> <span style="color:var(--muted);">${c.notes}</span></div>`;
      html += `</div>`;
    }

    html += `</div>`;

    _builderModal(html, false);
};
