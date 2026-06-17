/**
 * Hecos Template Manager — JavaScript API layer
 * ================================================
 * One function per concern. No global state pollution.
 * All state is encapsulated in the TemplateManager namespace.
 *
 * Public API (exposed via return):
 *   init, loadTemplates, openTemplate, newTemplate, saveTemplate,
 *   deleteTemplate, loadHistory, restoreVersion, previewRender,
 *   loadFlowVariables, onChannelChange, onTextBodyInput, insertVar
 *
 * _internal_activeId is synced to the external TemplateManager._activeId
 * property defined by _templates_logic.html to drive UI side-effects.
 */

window.TemplateManager = (() => {

  /* ── Internal State ──────────────────────────────────────────────────────── */
  let _allTemplates     = [];        // flat list from last fetch
  let _internal_activeId = null;     // currently selected template id
  let _grapeEditor      = null;      // GrapeJS instance (email only)
  let _activeChannel    = 'email';   // channel of the template currently open
  let _dirty            = false;     // unsaved changes flag

  /* Active-ID helpers */
  function _getActiveId() { return _internal_activeId; }
  function _setActiveId(v) {
    _internal_activeId = v;
    // Trigger the external property setter so _templates_logic.html can
    // show/hide the delete button without polling.
    try {
      const desc = Object.getOwnPropertyDescriptor(TemplateManager, '_activeId');
      if (desc && desc.set) desc.set.call(TemplateManager, v);
    } catch (_) {}
  }

  /* ── DOM helpers ──────────────────────────────────────────────────────────── */

  const $ = id => document.getElementById(id);

  function _showSection(id) {
    ['tpl-list-section', 'tpl-editor-section', 'tpl-empty-section'].forEach(s => {
      const el = $(s);
      if (el) el.style.display = (s === id) ? '' : 'none';
    });
  }

  function _toast(msg, type = 'success') {
    if (window.toast) { window.toast(type, msg); return; }
    console.info('[Templates]', msg);
  }

  /* ── API calls ────────────────────────────────────────────────────────────── */

  async function _apiFetch(path, method = 'GET', body = null) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch('/api/templates' + path, opts);
    return res.json();
  }

  /* ── List templates ───────────────────────────────────────────────────────── */

  async function loadTemplates() {
    try {
      const data = await _apiFetch('/');
      _allTemplates = data.templates || [];
      _renderSidebar();
      if (_allTemplates.length === 0) {
        _showSection('tpl-empty-section');
      } else {
        _showSection('tpl-list-section');
      }
    } catch (e) {
      _toast('Error loading templates: ' + e, 'error');
    }
  }

  function _renderSidebar() {
    const channels = ['email', 'whatsapp', 'telegram', 'discord'];
    channels.forEach(ch => {
      const list = $('tpl-list-' + ch);
      if (!list) return;
      const items = _allTemplates.filter(t => t.channel === ch);
      list.innerHTML = items.length === 0
        ? `<div class="tpl-sidebar-empty">No templates yet</div>`
        : items.map(t => `
            <div class="tpl-sidebar-item ${t.id === _getActiveId() ? 'active' : ''}"
                 data-id="${t.id}" onclick="TemplateManager.openTemplate('${t.id}')">
              <span class="tpl-sidebar-name">${_esc(t.name)}</span>
              <span class="tpl-sidebar-date">${_shortDate(t.updated_at)}</span>
            </div>`).join('');
    });
  }

  /* ── Open / edit a template ───────────────────────────────────────────────── */

  async function openTemplate(id) {
    if (_dirty && !confirm('You have unsaved changes. Discard them?')) return;
    try {
      const data = await _apiFetch('/' + id);
      if (!data.ok) { _toast('Template not found', 'error'); return; }
      _setActiveId(id);
      _dirty         = false;
      _activeChannel = data.template.channel;
      _populateEditor(data.template);
      _showSection('tpl-editor-section');
      _renderSidebar();
    } catch (e) {
      _toast('Error loading template: ' + e, 'error');
    }
  }

  function _populateEditor(tpl) {
    _val('tpl-edit-name',        tpl.name        || '');
    _val('tpl-edit-description', tpl.description || '');

    const defaultCb = $('tpl-edit-is-default');
    if (defaultCb) defaultCb.checked = !!tpl.is_default;

    _setChannel(tpl.channel);

    if (tpl.channel === 'email') {
      _val('tpl-edit-subject', tpl.subject || '');
      _setEmailBody(tpl.body_html || tpl.body_text || '');
    } else {
      _val('tpl-edit-header',    tpl.header    || '');
      _val('tpl-edit-body-text', tpl.body_text || '');
      _val('tpl-edit-footer',    tpl.footer    || '');
      _renderTextPreview(tpl.header || '', tpl.body_text || '', tpl.footer || '');
    }

    _renderVariables(tpl.variables || []);
    _renderHistory([]);
  }

  /* ── Channel switch ───────────────────────────────────────────────────────── */

  function _setChannel(ch) {
    _activeChannel = ch;
    ['email', 'whatsapp', 'telegram', 'discord'].forEach(c => {
      const el = $('tpl-editor-' + c);
      if (el) el.style.display = (c === ch) ? '' : 'none';
    });
    const chSel = $('tpl-edit-channel');
    if (chSel) chSel.value = ch;

    if (ch === 'email' && !_grapeEditor) _initGrapeJS();
  }

  function onChannelChange(ch) {
    _setChannel(ch);
    _dirty = true;
  }

  /* ── GrapeJS (email editor) ───────────────────────────────────────────────── */

  function _initGrapeJS() {
    if (typeof grapesjs === 'undefined') {
      const loadingEl = $('tpl-grapes-loading');
      if (loadingEl) loadingEl.style.display = '';
      return;
    }
    const loadingEl = $('tpl-grapes-loading');
    if (loadingEl) loadingEl.style.display = 'none';

    _grapeEditor = grapesjs.init({
      container:  '#tpl-grapes-container',
      height:     '420px',
      width:      '100%',
      fromElement: false,
      storageManager: false,
      plugins:    ['gjs-preset-newsletter'],
      pluginsOpts: {
        'gjs-preset-newsletter': {
          modalLabelImport: 'Paste HTML here',
          modalLabelExport: 'Copy the HTML below',
        }
      },
      panels: { defaults: [] },
      blockManager:  { appendTo: '#tpl-grapes-blocks' },
      styleManager:  { appendTo: '#tpl-grapes-styles' },
      traitManager:  { appendTo: '#tpl-grapes-traits' },
    });

    _grapeEditor.on('change:changesCount', () => { _dirty = true; });

    // Apply any pending HTML
    if (window._tplPendingHtml) {
      _grapeEditor.setComponents(window._tplPendingHtml);
      delete window._tplPendingHtml;
    }
  }

  function _setEmailBody(html) {
    if (_grapeEditor) {
      _grapeEditor.setComponents(html || '');
    } else {
      window._tplPendingHtml = html;
    }
  }

  function _getEmailBody() {
    if (_grapeEditor) {
      try { return _grapeEditor.runCommand('gjs-get-inlined-html') || _grapeEditor.getHtml(); }
      catch { return _grapeEditor.getHtml(); }
    }
    return '';
  }

  /* ── Messenger plain-text editor ─────────────────────────────────────────── */

  function _renderTextPreview(header, text, footer) {
    const prev = $('tpl-text-preview');
    if (!prev) return;
    const headerVal = header !== undefined ? header : (_getVal('tpl-edit-header') || '');
    const footerVal = footer  !== undefined ? footer  : (_getVal('tpl-edit-footer')  || '');
    const parts = [headerVal, text, footerVal].filter(Boolean);
    prev.textContent = parts.join('\n\n') || '(empty)';
  }

  function onTextBodyInput(val) {
    _renderTextPreview(undefined, val, undefined);
    _dirty = true;
    _renderVariables(_extractVars(val));
  }

  /* ── Variable extraction & picker ────────────────────────────────────────── */

  function _extractVars(text) {
    const matches = (text || '').match(/\{\{\s*(\w+)\s*\}\}/g) || [];
    const seen = new Set();
    return matches
      .map(m => m.replace(/\{\{\s*|\s*\}\}/g, ''))
      .filter(v => { if (seen.has(v)) return false; seen.add(v); return true; });
  }

  function _renderVariables(vars) {
    const box = $('tpl-variables-list');
    if (!box) return;
    if (!vars || vars.length === 0) {
      box.innerHTML = '<span style="opacity:.5;font-size:.75rem">No variables detected</span>';
      return;
    }
    box.innerHTML = vars.map(v =>
      `<span class="tpl-var-chip" onclick="TemplateManager.insertVar('{{ ${v} }}')" title="Click to copy/insert">{{ ${v} }}</span>`
    ).join('');
  }

  function insertVar(placeholder) {
    const ta = $('tpl-edit-body-text');
    if (ta && (document.activeElement === ta || ta.matches(':focus'))) {
      const s = ta.selectionStart, e = ta.selectionEnd;
      ta.value = ta.value.slice(0, s) + placeholder + ta.value.slice(e);
      ta.selectionStart = ta.selectionEnd = s + placeholder.length;
      ta.focus();
    } else {
      navigator.clipboard.writeText(placeholder)
        .then(() => _toast(`Copied: ${placeholder}`))
        .catch(() => _toast(`Variable: ${placeholder}`));
    }
    _dirty = true;
  }

  /* ── Flow variable picker ────────────────────────────────────────────────── */

  async function loadFlowVariables() {
    try {
      const res = await fetch('/api/flows/running');
      if (!res.ok) { _toast('No running flows found', 'info'); return; }
      const data = await res.json();
      const runIds = Object.values(data || {});
      if (!runIds.length) { _toast('No flow is currently running', 'info'); return; }

      const varRes  = await fetch('/api/flows/' + runIds[0] + '/context');
      const varData = await varRes.json();
      const vars    = Object.keys(varData.context || {});
      if (vars.length) {
        _renderVariables(vars);
        _toast(`Loaded ${vars.length} variable(s) from flow`);
      } else {
        _toast('No variables found in the running flow', 'info');
      }
    } catch (e) {
      _toast('Could not load flow variables: ' + e, 'error');
    }
  }

  /* ── Save template ────────────────────────────────────────────────────────── */

  async function saveTemplate() {
    const name    = _getVal('tpl-edit-name').trim();
    const channel = _getVal('tpl-edit-channel');
    if (!name) { _toast('Name is required', 'error'); return; }

    let bodyHtml = '', bodyText = '', subject = '', footer = '';

    if (channel === 'email') {
      subject  = _getVal('tpl-edit-subject');
      bodyHtml = _getEmailBody();
      bodyText = _stripHtml(bodyHtml);
    } else {
      bodyText = _getVal('tpl-edit-body-text');
      footer   = _getVal('tpl-edit-footer');
    }
    const header = (_activeChannel !== 'email') ? _getVal('tpl-edit-header') : '';
    const isDefaultCb = $('tpl-edit-is-default');
    const isDefault = isDefaultCb ? isDefaultCb.checked : false;

    const vars = _extractVars([subject, bodyHtml, bodyText].join(' '));

    const payload = {
      id:          _getActiveId() || undefined,
      name,
      channel,
      description: _getVal('tpl-edit-description'),
      subject,
      body_html:   bodyHtml,
      body_text:   bodyText,
      header,
      footer,
      is_default:  isDefault,
      variables:   vars,
    };

    try {
      const aid    = _getActiveId();
      const method = aid ? 'PUT'  : 'POST';
      const path   = aid ? '/' + aid : '/';
      const res    = await _apiFetch(path, method, payload);
      if (!res.ok) { _toast('Save error: ' + res.error, 'error'); return; }
      _setActiveId(res.template.id);
      _dirty = false;
      _toast('Template saved!');
      await loadTemplates();
      _showSection('tpl-editor-section');
      _renderSidebar();
    } catch (e) {
      _toast('Save failed: ' + e, 'error');
    }
  }

  /* ── Delete template ──────────────────────────────────────────────────────── */

  async function deleteTemplate(id) {
    if (!id) { _toast('No template selected', 'error'); return; }
    const tpl = _allTemplates.find(t => t.id === id);
    if (!confirm(`Delete template "${tpl?.name || id}"? This cannot be undone.`)) return;
    try {
      const res = await _apiFetch('/' + id, 'DELETE');
      if (!res.ok) { _toast('Delete error: ' + res.error, 'error'); return; }
      if (_getActiveId() === id) {
        _setActiveId(null);
        _dirty = false;
        _showSection('tpl-empty-section');
      }
      _toast('Template deleted');
      await loadTemplates();
    } catch (e) {
      _toast('Delete failed: ' + e, 'error');
    }
  }

  /* ── New template ─────────────────────────────────────────────────────────── */

  function newTemplate(channel) {
    if (_dirty && !confirm('You have unsaved changes. Discard them?')) return;
    _setActiveId(null);
    _dirty = false;
    _populateEditor({
      name: '', channel: channel || 'email', description: '',
      subject: '', body_html: '', body_text: '', header: '', footer: '', is_default: false, variables: []
    });
    _showSection('tpl-editor-section');
    _renderSidebar();
  }

  /* ── Version history ──────────────────────────────────────────────────────── */

  async function loadHistory() {
    const aid = _getActiveId();
    if (!aid) return;
    try {
      const data = await _apiFetch('/' + aid + '/history');
      _renderHistory(data.history || []);
    } catch (e) {
      _toast('Error loading history: ' + e, 'error');
    }
  }

  function _renderHistory(history) {
    const box = $('tpl-history-list');
    if (!box) return;
    if (!history.length) {
      box.innerHTML = '<div class="tpl-history-empty">No versions yet</div>';
      return;
    }
    box.innerHTML = history.map((v, i) => `
      <div class="tpl-history-item">
        <span class="tpl-history-date">${_shortDate(v.snapshot_at)}</span>
        <span class="tpl-history-name">${_esc(v.name)}</span>
        <button class="tpl-history-restore" onclick="TemplateManager.restoreVersion(${i})">
          <i class="fas fa-undo"></i> Restore
        </button>
      </div>`).join('');
  }

  async function restoreVersion(index) {
    const aid = _getActiveId();
    if (!aid) return;
    if (!confirm(`Restore version #${index + 1}? Current state will be saved first.`)) return;
    try {
      const res = await _apiFetch('/' + aid + '/restore/' + index, 'POST');
      if (!res.ok) { _toast('Restore error: ' + res.error, 'error'); return; }
      _dirty = false;
      _populateEditor(res.template);
      _toast('Version restored!');
      await loadHistory();
    } catch (e) {
      _toast('Restore failed: ' + e, 'error');
    }
  }

  /* ── Preview / render ─────────────────────────────────────────────────────── */

  async function previewRender() {
    const aid = _getActiveId();
    if (!aid) { _toast('Save the template first', 'info'); return; }
    const varsRaw = _getVal('tpl-preview-vars');
    let variables = {};
    try { variables = JSON.parse(varsRaw || '{}'); }
    catch { _toast('Invalid JSON for variables', 'error'); return; }
    try {
      const res = await _apiFetch('/' + aid + '/render', 'POST', { variables });
      if (!res.ok) { _toast('Render error: ' + res.error, 'error'); return; }
      const r = res.rendered;
      const iframe = $('tpl-preview-iframe');
      if (_activeChannel === 'email' && iframe) {
        iframe.srcdoc = r.body_html || `<pre>${_esc(r.body_text)}</pre>`;
        iframe.style.display = '';
      }
      // For messenger channels, combine header + body + footer
      const prev = $('tpl-preview-text');
      if (prev) {
        const parts = [r.header, r.body_text, r.footer].filter(Boolean);
        prev.textContent = parts.join('\n\n') || '';
      }
      const subj = $('tpl-preview-subject');
      if (subj) subj.textContent = r.subject || '—';
    } catch (e) {
      _toast('Preview failed: ' + e, 'error');
    }
  }

  /* ── Utility helpers ──────────────────────────────────────────────────────── */

  function _val(id, v)  { const el = $(id); if (el && v !== undefined) el.value = v; }
  function _getVal(id)  { const el = $(id); return el ? el.value : ''; }
  function _esc(s)      { return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

  function _shortDate(iso) {
    if (!iso) return '';
    try { return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); }
    catch { return iso.slice(0, 10); }
  }

  function _stripHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return (tmp.textContent || tmp.innerText || '').trim();
  }

  /* ── Init ─────────────────────────────────────────────────────────────────── */

  function init() {
    loadTemplates();
    // Lazily load history when the History tab is first clicked
    const histTab = $('tpl-tab-history');
    if (histTab && !histTab._tplHistoryBound) {
      histTab._tplHistoryBound = true;
      histTab.addEventListener('click', loadHistory);
    }
  }

  /* ── Public API ───────────────────────────────────────────────────────────── */
  return {
    // State (read by _templates_logic.html for the delete button)
    _internal_activeId: null,
    // Methods
    init,
    loadTemplates,
    openTemplate,
    newTemplate,
    saveTemplate,
    deleteTemplate,
    loadHistory,
    restoreVersion,
    previewRender,
    loadFlowVariables,
    onChannelChange,
    onTextBodyInput,
    insertVar,
  };

})();
