/**
 * igen_probe.js - Image Gen Panel: Provider Probe / Diagnostics
 * runIgenProbe - tests all providers and renders a latency/status table.
 */

window.runIgenProbe = async function() {
    var btn = document.getElementById('igen-probe-btn');
    var box = document.getElementById('igen-probe-results');
    if (!btn || !box) return;

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin" style="color:var(--accent);"></i> Probing...';
    box.style.display = 'block';
    box.innerHTML = '<div style="color:var(--muted); text-align:center; padding:8px;">\u23f3 Testing all servers, please wait...</div>';

    try {
        var res  = await fetch('/hecos/api/plugins/image_gen/probe');
        var data = await res.json();

        if (!data.ok) {
            box.innerHTML = '<div style="color:#e74c3c;">\u274c Probe error: ' + data.error + '</div>';
            return;
        }

        var results = data.results || [];
        var okCount = results.filter(function(r) { return r.ok; }).length;

        var html = '<div style="margin-bottom:8px; font-weight:700; color:var(--text);">' +
            'Results: <span style="color:#2ecc71;">' + okCount + ' OK</span> / ' + results.length + ' tested' +
            '</div>';

        html += '<table style="width:100%; border-collapse:collapse; font-size:11px;">';
        html += '<thead><tr style="border-bottom:1px solid var(--border); color:var(--muted);">';
        html += '<th style="text-align:left; padding:4px 6px;">Provider / Server</th>';
        html += '<th style="text-align:center; padding:4px 6px;">Status</th>';
        html += '<th style="text-align:right; padding:4px 6px;">Latency</th>';
        html += '<th style="text-align:left; padding:4px 6px;">Details</th>';
        html += '</tr></thead><tbody>';

        results.forEach(function(r) {
            var icon    = r.ok ? '\u2705' : '\u274c';
            var latency = r.latency_ms != null ? r.latency_ms + 'ms' : '\u2014';
            var detail  = r.error ? '<span style="color:#e74c3c;">' + r.error + '</span>' : '';
            var rowBg   = r.ok ? 'rgba(46,204,113,0.04)' : 'transparent';
            var onclick = '';
            var cursor  = '';
            var title   = '';
            if (r.ok && r.server_id) {
                onclick = 'onclick="document.getElementById(\'igen-hf-provider\').value=\'' + r.server_id + '\'; _igenDebounceSave(); _igenAlert(\'Server selected: ' + r.name + '\', \'success\');"';
                cursor  = 'cursor:pointer;';
                title   = 'title="Click to select this server"';
            }

            html += '<tr style="border-bottom:1px solid var(--border); background:' + rowBg + '; ' + cursor + '" ' + onclick + ' ' + title + '>';
            html += '<td style="padding:5px 6px; font-weight:600;">' + r.name + '</td>';
            html += '<td style="text-align:center; padding:5px 6px;">' + icon + '</td>';
            html += '<td style="text-align:right; padding:5px 6px; color:var(--muted);">' + latency + '</td>';
            html += '<td style="padding:5px 6px;">' + detail + '</td>';
            html += '</tr>';
        });

        html += '</tbody></table>';
        if (okCount > 0) {
            html += '<p style="margin-top:8px; font-size:11px; color:var(--muted);">\ud83d\udca1 Click a \u2705 row to auto-select that server.</p>';
        }
        box.innerHTML = html;

    } catch (e) {
        box.innerHTML = '<div style="color:#e74c3c;">\u274c Network error: ' + e.message + '</div>';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-stethoscope" style="color:var(--accent);"></i> Test Providers';
    }
};
