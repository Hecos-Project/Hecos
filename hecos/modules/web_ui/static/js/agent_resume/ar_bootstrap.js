/**
 * MODULE: agent_resume/ar_bootstrap.js
 * PURPOSE: Lifecycle orchestrator connecting checkpoint checks with chat load, session switch, and Resume actions.
 */

(function () {
  const ns = (window._HecosAgentResume = window._HecosAgentResume || {});
  let _checking = false;

  function _tr(key, fallbackEn) {
    const val = (window.I18N && window.I18N[key]) || (typeof window.t === 'function' ? window.t(key) : '');
    return (val && val !== key) ? val : fallbackEn;
  }

  async function refreshBanner(explicitSid = '') {
    if (_checking || !ns.api || !ns.banner) return;
    const activePlanCard = document.querySelector('#agent-plan-active-card:not(.is-completed)');
    if (window.isStreaming || activePlanCard) {
      ns.banner.renderBanner(null);
      return;
    }
    _checking = true;
    try {
      const data = await ns.api.fetchCheckpoint(explicitSid);
      if (data && data.has_resumable && data.checkpoint) {
        ns.banner.renderBanner(data.checkpoint, {
          onResume: async (ckpt, btn) => {
            if (btn) btn.disabled = true;
            try {
              ns.banner.renderBanner(null);
              await ns.api.resumeCheckpoint(ckpt.session_id || explicitSid);
            } catch (err) {
              if (window.showToast) window.showToast(`⚠️ ${_tr('ar_toast_resume_failed', 'Resume failed:')} ${err.message || err}`, true);
              await refreshBanner(explicitSid);
            }
          },
          onDismiss: async (ckpt) => {
            await ns.api.dismissCheckpoint(ckpt.session_id || explicitSid);
            ns.banner.renderBanner(null);
          },
        });
      } else {
        ns.banner.renderBanner(null);
      }
    } catch (e) {
    } finally {
      _checking = false;
    }
  }

  window.AgentResume = {
    refreshBanner,
    resumeActive: (sid) => ns.api?.resumeCheckpoint(sid),
    dismissActive: (sid) => ns.api?.dismissCheckpoint(sid),
  };

  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => refreshBanner(), 700);
  });
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && !window.isStreaming) {
      refreshBanner();
    }
  });
})();
