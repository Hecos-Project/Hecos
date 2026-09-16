/**
 * igen_horde.js - Image Gen Panel: AI Horde Account Check
 * checkHordeAccount - fetches kudos balance and account info.
 */

window.checkHordeAccount = async function() {
    var kEl = document.getElementById('horde-kudos-value');
    var iEl = document.getElementById('horde-account-info');
    var tEl = document.getElementById('horde-account-text');
    var btn = (typeof event !== 'undefined' && event) ? event.currentTarget : null;
    if (kEl) kEl.textContent = '... Kudos';
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Attendere...'; }
    try {
        var res  = await fetch('/hecos/api/plugins/image_gen/horde/status');
        var data = await res.json();
        if (data.ok) {
            if (kEl) kEl.textContent = Math.floor(data.kudos).toLocaleString() + ' Kudos';
            if (iEl && tEl) {
                iEl.style.display = 'block';
                tEl.innerHTML = 'Connesso come: <strong>' + data.username + '</strong> <span style="margin:0 6px;">|</span> Worker attivi: <strong>' + data.worker_count + '</strong>';
                if (data.is_anonymous) {
                    tEl.innerHTML += '<br><span style="color:#e74c3c;"><i class="fas fa-exclamation-circle"></i> Account anonimo. La priorit\u00e0 di generazione \u00e8 bassa.</span>';
                }
            }
        } else {
            if (kEl) kEl.textContent = 'Errore API';
            if (iEl && tEl) {
                iEl.style.display = 'block';
                tEl.innerHTML = '<span style="color:#e74c3c;"><i class="fas fa-times-circle"></i> ' + (data.error || 'Errore di connessione a AI Horde') + '</span>';
            }
        }
    } catch(e) {
        if (kEl) kEl.textContent = 'Offline';
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-user-check"></i> Verifica'; }
    }
};
