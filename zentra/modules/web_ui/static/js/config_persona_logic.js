/**
 * Zentra Core WebUI - Persona Avatar Management
 */

async function loadPersonaAvatar(personaName) {
    const preview = document.getElementById('ia-avatar-preview');
    if (!preview || !personaName) return;

    const name = personaName.replace('.yaml', '');
    try {
        const r = await fetch(`/api/persona/avatar?persona=${encodeURIComponent(name)}`);
        const d = await r.json();
        if (d.ok && d.avatar_path) {
            preview.src = d.avatar_path + '?t=' + Date.now();
        }
    } catch (e) {
        console.warn("[Avatar] Failed to load avatar for", name, e);
    }
}

async function uploadAvatar() {
    const input = document.getElementById('ia-avatar-input');
    const preview = document.getElementById('ia-avatar-preview');
    const loader = document.getElementById('ia-avatar-loading');
    const select = document.getElementById('ia-personality-main');
    
    if (!input.files || !input.files[0]) return;
    if (!select.value) {
        alert("Seleziona prima una personalità!");
        return;
    }

    const file = input.files[0];
    const persona = select.value.replace('.yaml', '');

    // Show preview immediately using FileReader
    const reader = new FileReader();
    reader.onload = (e) => { preview.src = e.target.result; };
    reader.readAsDataURL(file);

    // Prepare upload
    const formData = new FormData();
    formData.append('file', file);
    formData.append('persona', persona);

    if (loader) loader.style.display = 'flex';
    
    try {
        const res = await fetch('/api/persona/avatar/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        if (data.ok) {
            console.log("Avatar uploaded successfully:", data.avatar_path);
            // Refresh the preview with the server-side URL to confirm it's saved
            preview.src = data.avatar_path + '?t=' + Date.now();
        } else {
            alert("Errore caricamento: " + data.error);
        }
    } catch (e) {
        console.error("Upload error:", e);
        alert("Errore di rete durante il caricamento.");
    } finally {
        if (loader) loader.style.display = 'none';
        input.value = ''; // Reset input
    }
}

// On page load and on persona selection change, load the correct avatar
document.addEventListener('DOMContentLoaded', () => {
    const select = document.getElementById('ia-personality-main');
    if (!select) return;
    
    // Load avatar for the currently selected persona on page load
    // Use a short delay to ensure the select value is populated first by config_mapper
    setTimeout(() => {
        if (select.value) {
            loadPersonaAvatar(select.value);
        }
    }, 500);

    // Update avatar preview when user changes the persona dropdown
    select.addEventListener('change', () => {
        if (select.value) {
            loadPersonaAvatar(select.value);
        }
    });
});

window.uploadAvatar = uploadAvatar;
window.loadPersonaAvatar = loadPersonaAvatar;
