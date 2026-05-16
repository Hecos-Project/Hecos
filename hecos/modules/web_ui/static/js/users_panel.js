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
                    <th style="padding:8px; text-align:right;">-</th>
                </tr></thead><tbody>`;
            res.users.forEach(u => {
                const isSelf  = u.username === "admin";
                const actions = isSelf
                    ? `<i>self</i>`
                    : `<button class="btn btn-danger" style="padding:2px 4px; font-size:8px;" onclick="deleteUser('${u.username}')">X</button>`;
                html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
                    <td style="padding:8px; font-weight:600;">${u.username}</td>
                    <td style="padding:8px; color:var(--muted);">${u.role}</td>
                    <td style="padding:8px; text-align:right;">${actions}</td>
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
