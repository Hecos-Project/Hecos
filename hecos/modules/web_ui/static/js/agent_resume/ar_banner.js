/**
 * MODULE: agent_resume/ar_banner.js
 * PURPOSE: Render and bind the collapsible Resume Interrupted Task banner above #chat-area.
 */

(function () {
  const ns = (window._HecosAgentResume = window._HecosAgentResume || {});

  function _tr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || (typeof window.t === 'function' ? window.t(key) : '');
    return (val && val !== key) ? val : fallbackEn;
  }

  function _esc(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _formatStatusLabel(ckpt) {
    const st = String(ckpt.status || 'running').toLowerCase();
    const reason = String(ckpt.reason || '').toLowerCase();
    if (reason.includes('timeout')) return _tr('ar_status_timeout', 'Turn Timeout');
    if (st === 'running') return _tr('ar_status_crash', 'Interrupted / Crash');
    if (reason.includes('abort')) return _tr('ar_status_stopped', 'Stopped');
    return _tr('ar_status_interrupted', 'Interrupted');
  }

  function renderBanner(checkpoint, handlers) {
    const slot = document.getElementById('agent-resume-slot');
    if (!slot) return;

    if (!checkpoint) {
      slot.innerHTML = '';
      return;
    }

    const stepNum = Number(checkpoint.iteration || 0);
    const maxStep = Number(checkpoint.max_iterations || 25);
    const nextStep = stepNum + 1;
    const files = Array.isArray(checkpoint.directory_entries) && checkpoint.directory_entries.length
      ? checkpoint.directory_entries
      : (Array.isArray(checkpoint.verified_files) ? checkpoint.verified_files.map((f) => f.name) : []);

    const moreTpl = _tr('ar_more_files', '+{count} more');
    const pillsHtml = files.slice(0, 6).map((f) => `<span class="agent-resume-file-pill">✓ ${_esc(f)}</span>`).join('') +
      (files.length > 6 ? `<span class="agent-resume-file-pill">${_esc(moreTpl.replace('{count}', String(files.length - 6)))}</span>` : '');

    const regionLbl = _esc(_tr('ar_region_label', 'Resume interrupted work'));
    const savedAtLbl = _esc(_tr('ar_saved_at', 'Work saved at'));
    const resumeBtnLbl = _esc(_tr('ar_btn_resume', 'Resume from Step'));
    const dismissTitle = _esc(_tr('ar_btn_dismiss_title', 'Hide and discard this checkpoint'));
    const dismissLbl = _esc(_tr('ar_btn_dismiss', 'Dismiss'));

    slot.innerHTML = `
      <div class="agent-resume-banner" role="region" aria-label="${regionLbl}">
        <div class="agent-resume-info">
          <div class="agent-resume-title">
            <span class="agent-resume-badge"><i class="fas fa-history"></i> ${_esc(_formatStatusLabel(checkpoint))}</span>
            <span>${savedAtLbl} <strong>Step ${stepNum}/${maxStep}</strong>${checkpoint.model_label ? ` · ${_esc(checkpoint.model_label)}` : ''}</span>
          </div>
          ${checkpoint.user_preview ? `<div class="agent-resume-preview" title="${_esc(checkpoint.user_preview)}">${_esc(checkpoint.user_preview)}</div>` : ''}
          ${pillsHtml ? `<div class="agent-resume-files">${pillsHtml}</div>` : ''}
        </div>
        <div class="agent-resume-actions">
          <button type="button" class="agent-resume-btn-go" id="agent-resume-go-btn">
            <i class="fas fa-play"></i> ${resumeBtnLbl} ${nextStep}
          </button>
          <button type="button" class="agent-resume-btn-dismiss" id="agent-resume-dismiss-btn" title="${dismissTitle}">
            <i class="fas fa-times"></i> ${dismissLbl}
          </button>
        </div>
      </div>
    `;

    const goBtn = slot.querySelector('#agent-resume-go-btn');
    const disBtn = slot.querySelector('#agent-resume-dismiss-btn');
    if (goBtn && handlers?.onResume) {
      goBtn.addEventListener('click', () => handlers.onResume(checkpoint, goBtn));
    }
    if (disBtn && handlers?.onDismiss) {
      disBtn.addEventListener('click', () => handlers.onDismiss(checkpoint, disBtn));
    }
  }

  ns.banner = { renderBanner };
})();
