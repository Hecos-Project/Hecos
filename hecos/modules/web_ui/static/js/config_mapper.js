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
  console.log("Starting UI population...");
  const c = window.cfg;
  if (!c) { console.error("cfg not found"); return; }

  const safeCall = (name, fn) => {
      try { fn(); } catch (err) { console.error(`[populateUI] ${name} failed:`, err); }
  };

  // 1. Backend / LLM / AI / Bridge / Filters
  safeCall('Backend', () => populateBackendUI());

  // 2. Audio Module
  if (typeof populateAudioUI === 'function') safeCall('Audio', () => populateAudioUI());

  // 3. System Module
  if (typeof populateSystemUI === 'function') safeCall('System', () => populateSystemUI());

  // 4. Media & Image Gen
  if (typeof populateMediaUI === 'function') safeCall('Media', () => populateMediaUI());

  // 5. Drive
  if (typeof populateDriveUI === 'function') safeCall('Drive', () => populateDriveUI());

  // 6. Remote Triggers
  if (typeof populateRemoteTriggersUI === 'function') safeCall('RemoteTriggers', () => populateRemoteTriggersUI());

  // 7. Reminder
  if (typeof populateReminderUI === 'function') safeCall('Reminder', () => populateReminderUI());

  // 7b. Removed

  // 8. Privacy / WebUI / Agent
  if (typeof populatePrivacyUI === 'function') safeCall('Privacy', () => populatePrivacyUI());
  if (typeof populateWebUIConfig === 'function') safeCall('WebUIConfig', () => populateWebUIConfig());
  if (typeof populateAgentUI === 'function') safeCall('Agent', () => populateAgentUI());

  // 10. Standalone plugin enabled toggles
  safeCall('StandaloneToggles', () => {
      document.querySelectorAll('[data-plugin]').forEach(cb => {
          const tag = cb.dataset.plugin;
          if (c.plugins?.[tag]) cb.checked = c.plugins[tag].enabled !== false;
      });
  });

  // 11. Plugin Manager list
  safeCall('PluginsList', () => {
      if (typeof renderPlugins === 'function') renderPlugins(c.plugins || {});
  });

  // 12. Executor / Automation / Browser / Flows extras
  if (typeof populateExecutorUI === 'function')   safeCall('Executor', () => populateExecutorUI());
  if (typeof populateAutomationUI === 'function') safeCall('Automation', () => populateAutomationUI());
  if (typeof populateBrowserUI === 'function')    safeCall('Browser', () => populateBrowserUI());
  if (typeof populateFlowsUI === 'function')      safeCall('Flows', () => populateFlowsUI());

  // 13. Restart indicator badges
  if (typeof initRestartIndicators === 'function') safeCall('RestartIndicators', () => initRestartIndicators());

  console.log("UI Populated successfully.");
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
        if (sysPart.plugins?.DASHBOARD) {
            out.plugins['DASHBOARD'] = out.plugins['DASHBOARD'] || {};
            // Merge ONLY the console-specific keys — never touch track_cpu/ram/vram (WebUI widget)
            const dsbSys = sysPart.plugins.DASHBOARD;
            if ('console_telemetry_enabled' in dsbSys) out.plugins['DASHBOARD'].console_telemetry_enabled = dsbSys.console_telemetry_enabled;
            if ('console_telemetry_cpu'     in dsbSys) out.plugins['DASHBOARD'].console_telemetry_cpu     = dsbSys.console_telemetry_cpu;
            if ('console_telemetry_ram'     in dsbSys) out.plugins['DASHBOARD'].console_telemetry_ram     = dsbSys.console_telemetry_ram;
            if ('console_telemetry_vram'    in dsbSys) out.plugins['DASHBOARD'].console_telemetry_vram    = dsbSys.console_telemetry_vram;
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
    if (window.buildFlowsPayload) window.buildFlowsPayload(out);

    // 6. Reminder
    if (typeof buildReminderPayload === 'function') {
        const remPart = buildReminderPayload();
        if (remPart?.plugins?.REMINDER) {
            out.plugins['REMINDER'] = out.plugins['REMINDER'] || {};
            const r = remPart.plugins.REMINDER;
            Object.assign(out.plugins['REMINDER'], r);
        }
    }

    // 6b. Removed

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
