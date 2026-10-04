async function refreshAudioHistoryCount() {
    const lbl = document.getElementById('v-history-count');
    if (lbl) lbl.textContent = 'Loading...';
    try {
        const r = await fetch('/api/audio/history/info');
        const d = await r.json();
        if (d.ok) {
            const max = parseInt(document.getElementById('v-tts-history-max')?.value || 100);
            if (lbl) lbl.textContent = `📂 ${d.count} files present (${d.size_mb} MB) — limit: ${max}`;
        } else {
            if (lbl) lbl.textContent = '❌ Error loading.';
        }
    } catch (e) {
        if (lbl) lbl.textContent = '❌ Request failed.';
    }
}

async function clearAudioHistory() {
    if (!confirm('Delete all audio files from history?')) return;
    const lbl = document.getElementById('v-history-count');
    try {
        const r = await fetch('/api/audio/history/clear', { method: 'POST' });
        const d = await r.json();
        if (d.ok) {
            if (lbl) lbl.textContent = `✅ History cleared (${d.deleted} files deleted).`;
        } else {
            if (lbl) lbl.textContent = '❌ ' + (d.error || 'Unknown error.');
        }
    } catch (e) {
        if (lbl) lbl.textContent = '❌ Request failed.';
    }
}

// ── On-Demand TTS Engine Installer ───────────────────────────────────────────
window.refreshAudioHistoryCount = refreshAudioHistoryCount;
window.clearAudioHistory     = clearAudioHistory;
