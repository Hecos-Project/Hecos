window.hecosPrompt = function(msg, onSave) {
    var modalId = 'audio-custom-prompt-modal';
    var modal = document.getElementById(modalId);
    if (!modal) {
        modal = document.createElement('div');
        modal.id = modalId;
        modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:9999;';
        modal.innerHTML = '<div style="background:var(--bg2); border:1px solid var(--border); padding:24px; border-radius:12px; max-width:400px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,0.5);">' +
            '<h3 style="margin-top:0; color:var(--text);"><i class="fas fa-keyboard" style="margin-right:8px; color:var(--accent);"></i> Input Required</h3>' +
            '<p id="' + modalId + '-text" style="margin:20px 0; color:var(--text); font-size:1.05em;"></p>' +
            '<input type="text" id="' + modalId + '-input" class="config-input" style="width:100%; margin-bottom:20px; border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 12px; border-radius:6px;">' +
            '<div style="display:flex; justify-content:flex-end; gap:10px;">' +
            '<button class="btn" id="' + modalId + '-cancel" style="border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 16px; border-radius:6px; cursor:pointer;">Cancel</button>' +
            '<button class="btn" style="background:var(--accent); color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer;" id="' + modalId + '-save">Save</button>' +
            '</div></div>';
        document.body.appendChild(modal);
    }
    document.getElementById(modalId + '-text').textContent = msg;
    var input = document.getElementById(modalId + '-input');
    input.value = '';

    var cleanup = function() { modal.style.display = 'none'; };

    document.getElementById(modalId + '-cancel').onclick = cleanup;
    document.getElementById(modalId + '-save').onclick = function() {
        cleanup();
        var val = input.value.trim();
        if (val) onSave(val);
    };

    modal.style.display = 'flex';
    setTimeout(function() { input.focus(); }, 100);
};

window.hecosConfirm = function(msg, onYes) {
    if (window.hpmShowConfirm) {
        window.hpmShowConfirm(msg, 'Confirm', onYes);
    } else {
        var modalId = 'audio-custom-confirm-modal';
        var modal = document.getElementById(modalId);
        if (!modal) {
            modal = document.createElement('div');
            modal.id = modalId;
            modal.style.cssText = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); display:flex; align-items:center; justify-content:center; z-index:9999;';
            modal.innerHTML = '<div style="background:var(--bg2); border:1px solid var(--border); padding:24px; border-radius:12px; max-width:400px; width:90%; box-shadow:0 10px 30px rgba(0,0,0,0.5);">' +
                '<h3 style="margin-top:0; color:var(--text);"><i class="fas fa-question-circle" style="margin-right:8px; color:var(--accent);"></i> Confirmation</h3>' +
                '<p id="' + modalId + '-text" style="margin:20px 0; color:var(--text); font-size:1.05em;"></p>' +
                '<div style="display:flex; justify-content:flex-end; gap:10px;">' +
                '<button class="btn" id="' + modalId + '-cancel" style="border:1px solid var(--border); background:var(--bg3); color:var(--text); padding:8px 16px; border-radius:6px; cursor:pointer;">Cancel</button>' +
                '<button class="btn" style="background:var(--accent); color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer;" id="' + modalId + '-yes">Confirm</button>' +
                '</div></div>';
            document.body.appendChild(modal);
        }
        document.getElementById(modalId + '-text').textContent = msg;

        var cleanup = function() { modal.style.display = 'none'; };

        document.getElementById(modalId + '-cancel').onclick = cleanup;
        document.getElementById(modalId + '-yes').onclick = function() {
            cleanup();
            onYes();
        };

        modal.style.display = 'flex';
    }
};

// ── XTTS Presets Logic ───────────────────────────────────────────────────────

