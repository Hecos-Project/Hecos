/**
 * config_mapper.js — Entry Point / Orchestrator
 *
 * All domain logic is delegated to the sub-modules loaded before this file:
 *   config_mapper_utils.js       → DOM helpers, populateSelect, getV/C, initRestartIndicators
 *   config_mapper_llm.js         → Backend / LLM / AI / Bridge / Filters
 *   config_mapper_plugins.js     → renderPlugins, syncPluginStateToMemory, buildPluginsPayload
 *   config_mapper_drive.js       → DRIVE plugin populate+build
 *   config_mapper_components.js  → RemoteTriggers, WebUI, Privacy, Agent, Reminder
 *   config_mapper_extras.js      → Executor, Automation, Browser, HecosTextFilters, saveDsb
 *
 * Load order in index.html must match the dependency chain above.
 */

function populateUI() {
  try {
    const c = window.cfg;

    // 1. Backend / LLM / AI / Bridge / Filters
    populateBackendUI();

    // 2. Audio Module
    if (typeof populateAudioUI === 'function')  populateAudioUI();

    // 3. System Module
    if (typeof populateSystemUI === 'function') populateSystemUI();

    // 4. Media & Image Gen
    if (typeof populateMediaUI === 'function')  populateMediaUI();

    // 5. Drive
    populateDriveUI();

    // 6. Remote Triggers
    populateRemoteTriggersUI();

    // 7. Reminder
    if (typeof populateReminderUI === 'function') populateReminderUI();

    // 8. Privacy / WebUI / Agent
    populatePrivacyUI();
    populateWebUIConfig();
    populateAgentUI();

    // 9. Dashboard specialized toggles
    const dsb = c.plugins?.DASHBOARD || {};
    setCheck('dashboard-webui-enabled',  dsb.webui_dashboard_enabled  ?? true);
    setCheck('telemetry-webui-enabled',  dsb.webui_telemetry_enabled  ?? true);
    setCheck('track-cpu-enabled',        dsb.track_cpu                ?? true);
    setCheck('track-ram-enabled',        dsb.track_ram                ?? true);
    setCheck('track-vram-enabled',       dsb.track_vram               ?? true);
    setCheck('dashboard-console-enabled',dsb.console_dashboard_enabled ?? true);
    setCheck('telemetry-console-enabled',dsb.console_telemetry_enabled ?? true);

    // 10. Standalone plugin enabled toggles
    document.querySelectorAll('[data-plugin]').forEach(cb => {
      const tag = cb.dataset.plugin;
      if (c.plugins?.[tag]) cb.checked = c.plugins[tag].enabled !== false;
    });

    // 11. Plugin Manager list
    renderPlugins(c.plugins || {});

    // 12. Executor / Automation / Browser extras
    if (window.populateExecutorUI)   window.populateExecutorUI();
    if (window.populateAutomationUI) window.populateAutomationUI();
    if (window.populateBrowserUI)    window.populateBrowserUI();

    // 13. Restart indicator badges
    initRestartIndicators();

    console.log("UI Populated successfully.");
  } catch (err) {
    console.error("UI Population failed:", err);
  }
}

function buildPayload() {
  const out = JSON.parse(JSON.stringify(window.cfg));
  out.plugins = out.plugins || {};

  try {
    // 1. Backend / LLM / AI / Bridge / Filters / Privacy
    buildBackendPayload(out);

    // 2. System logic (audio, logging, cognition etc.)
    if (typeof buildSystemPayload === 'function') {
        const sysPart = buildSystemPayload();
        out.logging   = sysPart.logging;
        out.system    = sysPart.system;
        out.language  = sysPart.language;
        out.cognition = sysPart.cognition;
        if (sysPart.plugins?.SYS_NET) {
            out.plugins['SYS_NET'] = out.plugins['SYS_NET'] || {};
            out.plugins['SYS_NET'].proxy_url = sysPart.plugins.SYS_NET.proxy_url;
        }
        if (sysPart.plugins?.WEB_UI) {
            out.plugins['WEB_UI'] = out.plugins['WEB_UI'] || {};
            out.plugins['WEB_UI'].https_enabled = sysPart.plugins.WEB_UI.https_enabled;
        }
    }

    // 3. Drive
    const drivePart = buildDrivePayload();
    if (drivePart?.plugins?.DRIVE) {
        out.plugins['DRIVE'] = out.plugins['DRIVE'] || {};
        Object.assign(out.plugins['DRIVE'], drivePart.plugins.DRIVE);
    }

    // 4. Plugin toggles, extensions, lazy, dashboard, browser, automation
    buildPluginsPayload(out);

    // 5. Remote Triggers
    const rtPart = buildRemoteTriggersPayload();
    if (rtPart?.plugins?.REMOTE_TRIGGERS) {
        out.plugins['REMOTE_TRIGGERS'] = out.plugins['REMOTE_TRIGGERS'] || {};
        out.plugins['REMOTE_TRIGGERS'].settings = rtPart.plugins.REMOTE_TRIGGERS.settings;
    }

    // 6. Reminder
    if (typeof buildReminderPayload === 'function') {
        const remPart = buildReminderPayload();
        if (remPart?.plugins?.REMINDER) {
            out.plugins['REMINDER'] = out.plugins['REMINDER'] || {};
            const r = remPart.plugins.REMINDER;
            Object.assign(out.plugins['REMINDER'], r);
        }
    }

    // 7. WebUI
    const webuiPart = buildWebUIPayload();
    if (webuiPart?.plugins?.WEB_UI) {
        out.plugins['WEB_UI'] = out.plugins['WEB_UI'] || {};
        Object.assign(out.plugins['WEB_UI'], webuiPart.plugins.WEB_UI);
    }

    // 8. Agent
    const agentPart = buildAgentPayload();
    if (agentPart?.agent) out.agent = agentPart.agent;

    console.log("[PERSISTENCE-TRACE] buildPayload - FINAL AI BLOCK:", JSON.stringify(out.ai));
  } catch (err) { console.error("buildPayload err:", err); }

  return out;
}

// Global exports (needed by config_core.js and other callers)
window.populateUI  = populateUI;
window.buildPayload = buildPayload;
