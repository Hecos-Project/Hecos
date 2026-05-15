/**
 * Hecos WebUI - Core Configuration Entry Point
 * Orchestrates the modularized configuration system.
 */

// Global State
window.cfg = window.cfg || {};
window.sysOptions = window.sysOptions || {};
window.isInitialLoading = false;

// Event Listeners for Auto-Saving
document.addEventListener('change', (e) => {
  if (e.target.closest('.no-autosave') || e.target.closest('#tab-logs')) return;
  const tag = e.target.tagName;
  const type = e.target.type;
  if (tag === 'SELECT' || tag === 'TEXTAREA' || type === 'checkbox' || (tag === 'INPUT' && type !== 'file')) {
    
    // Sync plugin toggles across UI
    if (e.target.dataset.plugin) {
        const pluginTag = e.target.dataset.plugin;
        document.querySelectorAll(`[data-plugin="${pluginTag}"]`).forEach(cb => {
            if (cb !== e.target) cb.checked = e.target.checked;
        });
        if (typeof syncPluginStateToMemory === 'function') {
            syncPluginStateToMemory(pluginTag, e.target.checked);
        }
    }

    // Sync Persona Selectors
    if (e.target.id === 'ia-personality-main' && typeof loadPersonaAvatar === 'function') {
        loadPersonaAvatar(e.target.value);
    }
    
    // Auto-stop voice if toggle is turned off
    if (e.target.id === 'sys-voice-status' && !e.target.checked) {
       if (typeof stopVoice === 'function') stopVoice();
    }
    
    if (typeof saveConfig === 'function') saveConfig(true);
  }
});

// Deep-linking (hash change)
window.addEventListener('hashchange', () => {
    const tab = window.location.hash.substring(1);
    if (tab && typeof showTab === 'function') showTab(tab);
});

// DOM Ready initialization
document.addEventListener('DOMContentLoaded', () => {
    console.log("[HECOS-CORE] DOM Loaded. Waiting for initAll...");
    
    // Backend Type card switching
    const backendTypeEl = document.getElementById('backend-type');
    if (backendTypeEl) {
        backendTypeEl.addEventListener('change', function() {
          const v = this.value;
          ['card-cloud', 'card-ollama', 'card-kobold'].forEach(id => {
              const el = document.getElementById(id);
              if (el) el.style.display = (id.includes(v)) ? '' : 'none';
          });
        });
    }

    // Start background status refresh
    if (typeof refreshStatus === 'function') {
        refreshStatus();
        setInterval(refreshStatus, 15000);
    }
});

/**
 * Strips legacy icons and injects new ones into titles.
 * (Optimized version for modular system)
 */
window.injectIconsInPanel = function(specificId = null) {
    const hub = window.CONFIG_HUB;
    if (!hub) return;
    const modulesToProcess = specificId ? hub.modules.filter(m => m.id === specificId) : hub.modules;

    setTimeout(() => {
        modulesToProcess.forEach(m => {
            const panel = document.getElementById('tab-' + (specificId || m.id));
            if (!panel) return;
            panel.querySelectorAll('.card-title, .panel-title, .section-title').forEach(title => {
                if (title.getAttribute('data-icon-injected')) return;
                const icon = window.getIconForModule(m.id, m.label, m.icon);
                let cleanText = title.innerHTML.trim();
                cleanText = cleanText.replace(/^[ \u00a9\u00ae\u2000-\u3300\ud83c\ud83d\ud83e\ud83f][\ufe00-\ufe0f]?\s*/u, '');
                cleanText = cleanText.replace(/^(✅|❌|⚠️|🧠|☁️|🛣️|🤖|🌉|🔊|⚙️|🧩|🛡️|🔒|⏳|💾|↺|📊|🎨|🔍|🛠️|📁|📝|🖼️|🌐|📷|🏠|❓|ℹ️)\s*/u, '');
                if (!cleanText || cleanText.length < 2) cleanText = window.t ? window.t(m.label) : m.label;
                title.innerHTML = `${icon} ${cleanText}`;
                title.setAttribute('data-icon-injected', 'true');
            });
        });
    }, 200);
};
