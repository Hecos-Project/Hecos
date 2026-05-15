/**
 * Hecos WebUI - Mapper Logic for AI Agent
 */

function populateAgentUI() {
    const c = window.cfg;
    if (!c || !c.agent) return;
    const a = c.agent;
    setCheck('agent-enabled', a.enabled ?? true);
    setVal('agent-max-iter', a.max_iterations ?? 10);
    setCheck('agent-verbose', a.verbose_traces ?? true);
    setCheck('agent-action-console', a.action_console_enabled ?? true);
}

function buildAgentPayload() {
    const el = document.getElementById('agent-enabled');
    const a = window.cfg.agent || {};
    return {
        agent: {
            enabled: getC('agent-enabled', a.enabled ?? true),
            max_iterations: parseInt(getV('agent-max-iter', a.max_iterations)) || 10,
            verbose_traces: getC('agent-verbose', a.verbose_traces ?? true),
            action_console_enabled: getC('agent-action-console', a.action_console_enabled ?? true)
        }
    };
}

window.populateAgentUI = populateAgentUI;
window.buildAgentPayload = buildAgentPayload;
