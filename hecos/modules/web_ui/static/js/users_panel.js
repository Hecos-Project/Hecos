/**
 * users_panel.js
 * ─────────────────────────────────────────────────────────────────────────────
 * Hecos Users — Config Panel Logic
 * Handles profile load/save, avatar upload, password change, and user registry
 * management (create, delete, list).
 * ─────────────────────────────────────────────────────────────────────────────
 */

let saveTimeout = null;

function debouncedSave() {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveMyProfile, 800);
}

function _showSync() {
    const b = document.getElementById('sync-badge');
    if (!b) return;
    b.classList.add('visible');
    setTimeout(() => b.classList.remove('visible'), 2000);
}

function togglePass(id) {
    const el = document.getElementById(id);
    el.type = (el.type === 'password') ? 'text' : 'password';
}

// ─────────────────────────────────────────────────────────────────────────────
// Profile Load / Save
// ─────────────────────────────────────────────────────────────────────────────

async function loadMyProfile() {
    try {
        const r   = await fetch("/hecos/api/users/me/profile");
        const res = await r.json();
        if (res.ok && res.profile) {
            const p      = res.profile;
            const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ""; };

            // Identity
            setVal('my_display_name', p.display_name);
            setVal('my_language',     p.preferred_language || 'en');
            // Bio Metrics
            setVal('my_real_name',   p.real_name);
            setVal('my_age',         p.age);
            setVal('my_birthday',    p.birthday);
            setVal('my_height',      p.height);
            setVal('my_weight',      p.weight);
            setVal('my_gender',      p.gender);
            setVal('my_orientation', p.orientation);
            // Social
            setVal('my_family_parents',       p.family_parents);
            setVal('my_family_partner',       p.family_partner);
            setVal('my_family_siblings',      p.family_siblings);
            setVal('my_pets',                 p.pets);
            setVal('my_family_children',      p.family_children);
            setVal('my_family_grandchildren', p.family_grandchildren);
            // Career & Education
            setVal('my_title',         p.title);
            setVal('my_education',     p.education);
            setVal('my_job_main',      p.job_main);
            setVal('my_job_secondary', p.job_secondary);
            // Interests & Notes
            setVal('my_interests',   p.interests);
            setVal('my_bio_notes',   p.bio_notes);
            setVal('my_extra_notes', p.extra_notes);
            // Contact
            setVal('my_email',   p.email);
            setVal('my_phone',   p.phone);
            setVal('my_address', p.address);
            setVal('my_city',    p.city);

            if (p.avatar_path) {
                const img = document.getElementById('my_avatar_preview');
                img.src           = p.avatar_path + "?t=" + Date.now();
                img.style.display = "block";
                document.getElementById('my_avatar_placeholder').style.display = "none";
            }
        }
    } catch (e) { console.error("Load profile failed", e); }
}

async function saveMyProfile(isLangChange = false) {
    const get = id => { const el = document.getElementById(id); return el ? el.value : ""; };
    const data = {
        display_name:           get('my_display_name'),
        preferred_language:     get('my_language'),
        real_name:              get('my_real_name'),
        age:                    get('my_age'),
        birthday:               get('my_birthday'),
        height:                 get('my_height'),
        weight:                 get('my_weight'),
        gender:                 get('my_gender'),
        orientation:            get('my_orientation'),
        family_parents:         get('my_family_parents'),
        family_partner:         get('my_family_partner'),
        family_siblings:        get('my_family_siblings'),
        pets:                   get('my_pets'),
        family_children:        get('my_family_children'),
        family_grandchildren:   get('my_family_grandchildren'),
        title:                  get('my_title'),
        education:              get('my_education'),
        job_main:               get('my_job_main'),
        job_secondary:          get('my_job_secondary'),
        interests:              get('my_interests'),
        bio_notes:              get('my_bio_notes'),
        extra_notes:            get('my_extra_notes'),
        email:                  get('my_email'),
        phone:                  get('my_phone'),
        address:                get('my_address'),
        city:                   get('my_city'),
    };
    try {
        const r   = await fetch("/hecos/api/users/me/profile", {
            method:  "PUT",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify(data),
        });
        const res = await r.json();
        if (res.ok) {
            if (isLangChange) {
                _showSync();
                setTimeout(() => window.location.reload(), 1000);
            } else {
                _showSync();
            }
        }
    } catch (e) { console.error("Save profile failed", e); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Avatar Upload
// ─────────────────────────────────────────────────────────────────────────────

async function uploadMyAvatar() {
    const file = document.getElementById('my_avatar_file').files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    try {
        const r   = await fetch("/hecos/api/users/me/avatar", { method: "POST", body: fd });
        const res = await r.json();
        if (res.ok) {
            const img           = document.getElementById('my_avatar_preview');
            img.src             = res.avatar_path + "?t=" + Date.now();
            img.style.display   = "block";
            document.getElementById('my_avatar_placeholder').style.display = "none";
            _showSync();
        }
    } catch (e) { console.error("Avatar upload failed", e); }
}

// ─────────────────────────────────────────────────────────────────────────────
// Password Change
// ─────────────────────────────────────────────────────────────────────────────

async function changeMyPassword() {
    const oldP = document.getElementById('sec_current_pass').value;
    const newP = document.getElementById('sec_new_pass').value;
    const stat = document.getElementById('sec-status');

    const showStatus = (msg, ok) => {
        stat.textContent        = msg;
        stat.style.background   = ok ? 'rgba(33,186,13,0.1)' : 'rgba(186,33,13,0.1)';
        stat.style.color        = ok ? '#21ba0d' : '#ff4444';
        stat.style.display      = 'block';
    };

    if (!oldP || !newP) {
        showStatus('Auth required', false);
        return;
    }
    try {
        const r   = await fetch("/hecos/api/users/me/password", {
            method:  "PUT",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ password: newP, current_password: oldP }),
        });
        const res = await r.json();
        showStatus(res.ok ? 'Key Updated' : 'Failed', res.ok);
        if (res.ok) {
            document.getElementById('sec_new_pass').value     = '';
            document.getElementById('sec_current_pass').value = '';
        }
        setTimeout(() => stat.style.display = 'none', 4000);
    } catch (e) { showStatus('Error', false); }
}

// ─────────────────────────────────────────────────────────────────────────────
// User Registry (Admin)
// ─────────────────────────────────────────────────────────────────────────────

async function loadUsersData() {
    const container = document.getElementById("users-table-container");
    try {
        const r   = await fetch("/hecos/api/users");
        const res = await r.json();
        if (res.ok) {
            if (!res.users.length) {
                container.innerHTML = `<p style="color:var(--muted);font-size:11px;padding:20px;text-align:center;">Empty Registry.</p>`;
                return;
            }
            let html = `<table style="width:100%; border-collapse:collapse; text-align:left; font-size:10px;">
                <thead style="background:rgba(255,255,255,0.03); color:var(--accent);"><tr>
                    <th style="padding:8px;">User</th>
                    <th style="padding:8px;">Role</th>
                    <th style="padding:8px; text-align:right;">Actions</th>
                </tr></thead><tbody>`;
            res.users.forEach(u => {
                const isSelf  = u.username === "admin";
                const delBtn  = isSelf
                    ? `<i style="font-size:9px;color:var(--muted);">admin</i>`
                    : `<button class="btn btn-danger" style="padding:2px 4px; font-size:8px;" onclick="deleteUser('${u.username}')">X</button>`;
                html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                    <td style="padding:8px; font-weight:600;">${u.username}</td>
                    <td style="padding:8px; color:var(--muted);">${u.role}</td>
                    <td style="padding:8px; text-align:right; display:flex; gap:4px; justify-content:flex-end;">
                        <button class="btn btn-secondary" style="padding:2px 4px; font-size:8px;" onclick="usersExportSingle('${u.username}')" title="Export Profile">
                            <i class="fas fa-file-export"></i>
                        </button>
                        ${delBtn}
                    </td>
                </tr>`;
            });
            html += `</tbody></table>`;
            container.innerHTML = html;
        }
    } catch (e) { container.innerHTML = `<p style="color:var(--red); padding:10px;">Error</p>`; }
}

async function createUser() {
    const u = document.getElementById("new_user_name").value;
    const p = document.getElementById("new_user_pass").value;
    const r = document.getElementById("new_user_role").value;
    if (!u || !p) return;
    try {
        const resp = await fetch("/hecos/api/users", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ username: u, password: p, role: r }),
        });
        const res = await resp.json();
        if (res.ok) {
            document.getElementById("new_user_name").value = "";
            document.getElementById("new_user_pass").value = "";
            loadUsersData();
            _showSync();
        } else { alert(res.error); }
    } catch (e) {}
}

async function deleteUser(username) {
    if (!confirm(`Delete ${username}?`)) return;
    try {
        const r   = await fetch(`/hecos/api/users/${username}`, { method: "DELETE" });
        const res = await r.json();
        if (res.ok) { loadUsersData(); _showSync(); }
    } catch (e) {}
}

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────────────────────────────────────
loadMyProfile();
loadUsersData();

// ─────────────────────────────────────────────────────────────────────────────
// Backup / Restore / Export
// ─────────────────────────────────────────────────────────────────────────────

async function _usersDownloadJson(filename, content) {
    if (window.showSaveFilePicker) {
        try {
            const fh = await window.showSaveFilePicker({
                suggestedName: filename,
                types: [{ description: 'JSON', accept: { 'application/json': ['.json'] } }]
            });
            const w = await fh.createWritable();
            await w.write(content);
            await w.close();
            return;
        } catch(e) {
            if (e.name === 'AbortError') return;
        }
    }
    const blob = new Blob([content], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
}

/** Backup all users (admin only) */
async function usersBackup() {
    try {
        if (window.showToast) showToast('Preparing users backup...', 'info');
        const res  = await fetch('/hecos/api/users/backup');
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Backup failed');

        const payload  = {
            type:        'hecos_users_backup',
            exported_at: new Date().toISOString(),
            users:       data.users
        };
        const filename = `hecos_users_backup_${new Date().toISOString().split('T')[0]}.json`;
        await _usersDownloadJson(filename, JSON.stringify(payload, null, 2));
        if (window.showToast) showToast(`Backup of ${data.count} users completed`, 'success');
    } catch(err) {
        console.error('[USERS] Backup error:', err);
        if (window.showToast) showToast(err.message, 'error');
        else alert('Backup error: ' + err.message);
    }
}

/** Export a single user's profile */
async function usersExportSingle(username) {
    try {
        const res  = await fetch(`/hecos/api/users/${username}/export`);
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || 'Export failed');

        const payload  = {
            type:        'hecos_users_backup',
            exported_at: new Date().toISOString(),
            users:       [data.user]
        };
        const safeUser = (username || 'user').replace(/[^a-z0-9_]/gi, '_');
        const filename = `hecos_user_${safeUser}.json`;
        await _usersDownloadJson(filename, JSON.stringify(payload, null, 2));
        if (window.showToast) showToast(`Profile of ${username} exported`, 'success');
    } catch(err) {
        console.error('[USERS] Export error:', err);
        if (window.showToast) showToast(err.message, 'error');
        else alert('Export error: ' + err.message);
    }
}

/** Export MY own profile (works for any role) */
async function usersExportMe() {
    return usersExportSingle('me');
}

/** Restore users from a backup JSON file */
async function usersRestoreFile(event) {
    const file = event.target.files[0];
    if (!file) return;
    event.target.value = '';

    // Create a beautiful Hecos-style modal on the fly
    const modalHtml = `
    <div id="users-restore-modal" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);backdrop-filter:blur(5px);z-index:99999;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity 0.2s;">
        <div style="background:var(--bg-secondary, #1e1e1e);border:1px solid var(--border-color, #333);border-radius:12px;padding:24px;width:400px;max-width:90%;box-shadow:0 10px 30px rgba(0,0,0,0.5);transform:translateY(-20px);transition:transform 0.2s;font-family:inherit;">
            <h3 style="margin-top:0;margin-bottom:12px;color:var(--text-primary, #fff);font-size:18px;display:flex;align-items:center;gap:8px;">
                <span style="font-size:20px;">🔄</span> Ripristino Utenti
            </h3>
            <p style="color:var(--text-secondary, #aaa);font-size:14px;line-height:1.5;margin-bottom:20px;">
                Come vuoi procedere con il ripristino dei dati utente?
            </p>
            
            <div style="display:flex;flex-direction:column;gap:12px;margin-bottom:24px;">
                <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer;padding:12px;background:var(--bg-tertiary, #2a2a2a);border-radius:8px;border:1px solid var(--border-color, #333);">
                    <input type="radio" name="restore_mode" value="merge" checked style="margin-top:2px;">
                    <div>
                        <div style="color:var(--text-primary, #fff);font-weight:600;font-size:14px;margin-bottom:4px;">Unione (Merge)</div>
                        <div style="color:var(--text-secondary, #aaa);font-size:12px;">Aggiorna solo i profili esistenti. Salta gli utenti sconosciuti o non presenti nel sistema. (Consigliato)</div>
                    </div>
                </label>
                
                <label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer;padding:12px;background:var(--bg-tertiary, #2a2a2a);border-radius:8px;border:1px solid var(--border-color, #333);">
                    <input type="radio" name="restore_mode" value="replace" style="margin-top:2px;">
                    <div>
                        <div style="color:var(--text-primary, #fff);font-weight:600;font-size:14px;margin-bottom:4px;">Sostituzione (Replace)</div>
                        <div style="color:var(--text-secondary, #aaa);font-size:12px;">Aggiorna gli esistenti E crea eventuali utenti mancanti (con password temporanea 'hecos').</div>
                    </div>
                </label>
            </div>
            
            <div style="display:flex;justify-content:flex-end;gap:12px;">
                <button id="urm-cancel" style="padding:8px 16px;background:transparent;color:var(--text-secondary, #aaa);border:1px solid var(--border-color, #333);border-radius:6px;cursor:pointer;font-weight:500;transition:0.2s;">Annulla</button>
                <button id="urm-confirm" style="padding:8px 16px;background:var(--accent-color, #0078d4);color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:500;transition:0.2s;">Procedi</button>
            </div>
        </div>
    </div>`;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = document.getElementById('users-restore-modal');
    const modalBox = modal.querySelector('div');
    
    // Animate in
    requestAnimationFrame(() => {
        modal.style.opacity = '1';
        modalBox.style.transform = 'translateY(0)';
    });

    const cleanup = () => {
        modal.style.opacity = '0';
        modalBox.style.transform = 'translateY(-20px)';
        setTimeout(() => modal.remove(), 200);
    };

    document.getElementById('urm-cancel').onclick = cleanup;
    
    document.getElementById('urm-confirm').onclick = async () => {
        const mode = document.querySelector('input[name="restore_mode"]:checked').value;
        cleanup();

        try {
            const text    = await file.text();
            
            // Handle edge case if user picks a ZIP file by mistake
            if (text.startsWith('PK')) {
                throw new Error("Hai selezionato un pacchetto ZIP (Backup Globale). Per ripristinare il backup globale, usa il pannello 'Backups' nella Dashboard, non questa pagina.");
            }

            let payload;
            try {
                payload = JSON.parse(text);
            } catch (e) {
                throw new Error("Il file non è un file JSON valido per l'importazione degli utenti.");
            }
            
            const users   = payload.users || payload;
            if (!Array.isArray(users)) throw new Error('File JSON non valido: lista utenti mancante.');

            if (window.showToast) showToast(`Ripristino di ${users.length} utenti in corso...`, 'info');

            const res = await fetch('/hecos/api/users/restore', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ users, mode })
            });
            const result = await res.json();
            if (!result.ok) throw new Error(result.error || 'Ripristino fallito');

            const msg2 = `Ripristinati ${result.imported} profili` + (result.skipped ? ` (${result.skipped} saltati)` : '');
            if (window.showToast) showToast(msg2, 'success');
            loadUsersData();
            loadMyProfile();
        } catch(err) {
            console.error('[USERS] Restore error:', err);
            
            // Create error modal
            const errHtml = `
            <div id="users-err-modal" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);backdrop-filter:blur(5px);z-index:99999;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity 0.2s;">
                <div style="background:var(--bg-secondary, #1e1e1e);border:1px solid #ff4444;border-radius:12px;padding:24px;width:400px;max-width:90%;box-shadow:0 10px 30px rgba(0,0,0,0.5);transform:translateY(-20px);transition:transform 0.2s;">
                    <h3 style="margin-top:0;margin-bottom:12px;color:#ff4444;font-size:18px;display:flex;align-items:center;gap:8px;">
                        ⚠️ Errore di Ripristino
                    </h3>
                    <p style="color:var(--text-primary, #fff);font-size:14px;line-height:1.5;margin-bottom:20px;">
                        ${err.message}
                    </p>
                    <div style="display:flex;justify-content:flex-end;">
                        <button id="urm-err-close" style="padding:8px 16px;background:transparent;color:var(--text-secondary, #aaa);border:1px solid var(--border-color, #333);border-radius:6px;cursor:pointer;">Chiudi</button>
                    </div>
                </div>
            </div>`;
            document.body.insertAdjacentHTML('beforeend', errHtml);
            const errModal = document.getElementById('users-err-modal');
            requestAnimationFrame(() => {
                errModal.style.opacity = '1';
                errModal.querySelector('div').style.transform = 'translateY(0)';
            });
            document.getElementById('urm-err-close').onclick = () => {
                errModal.style.opacity = '0';
                setTimeout(() => errModal.remove(), 200);
            };
        }
    };
}
