import pathlib

targets = [
    r'C:\Hecos\hecos\hpm\voice_forge\web\static\js\vf_production.js',
    r'C:\Hecos-Elite\sources\apps\voice_forge_src\web\static\js\vf_production.js',
]

# ── 1. VFTextHistory module to inject before window.VFProduction ──────────────
HISTORY_MODULE = '''\
/**
 * VFTextHistory – per-session text input history (last 10 entries).
 * Shared across all take textareas and the reference text field.
 * Arrow-Up/Down in a focused textarea navigates the history.
 */
window.VFTextHistory = (() => {
  const KEY     = "vf_text_history";
  const MAX     = 10;

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; }
  }
  function save(arr) {
    try { localStorage.setItem(KEY, JSON.stringify(arr)); } catch {}
  }

  return {
    /** Save a text entry. Trims, deduplicates (removes earlier identical), caps at MAX. */
    push(text) {
      const t = (text || "").trim();
      if (!t) return;
      let arr = load().filter(e => e !== t);
      arr.unshift(t);
      if (arr.length > MAX) arr = arr.slice(0, MAX);
      save(arr);
    },

    get() { return load(); },

    /**
     * Attach history navigation to a textarea or input element.
     * - Arrow Up   (at first line / caret at pos 0): go back in history
     * - Arrow Down (at last line  / caret at end):   go forward / restore draft
     * While browsing, the original unsaved text is preserved as a draft (index -1).
     */
    attach(el) {
      if (!el || el.dataset.vfHistoryBound === "1") return;
      el.dataset.vfHistoryBound = "1";

      let idx   = -1;   // -1 = not browsing (live text)
      let draft = "";   // snapshot of text before entering history

      const isTextarea = el.tagName === "TEXTAREA";

      function atFirstLine() {
        if (!isTextarea) return true;
        const before = el.value.slice(0, el.selectionStart);
        return !before.includes("\\n");
      }
      function atLastLine() {
        if (!isTextarea) return true;
        const after = el.value.slice(el.selectionEnd);
        return !after.includes("\\n");
      }

      el.addEventListener("keydown", e => {
        const history = window.VFTextHistory.get();
        if (!history.length) return;

        if (e.key === "ArrowUp" && atFirstLine()) {
          if (idx === -1) draft = el.value;      // snapshot before entering history
          if (idx < history.length - 1) {
            idx++;
            el.value = history[idx];
            // Dispatch input so take.text stays in sync
            el.dispatchEvent(new Event("input", { bubbles: true }));
            // Move caret to start
            requestAnimationFrame(() => { el.setSelectionRange(0, 0); });
            e.preventDefault();
          }

        } else if (e.key === "ArrowDown" && atLastLine()) {
          if (idx === -1) return;                // already at live text, nothing to do
          idx--;
          if (idx === -1) {
            el.value = draft;                   // restore the original draft
          } else {
            el.value = history[idx];
          }
          el.dispatchEvent(new Event("input", { bubbles: true }));
          // Move caret to end
          requestAnimationFrame(() => { el.setSelectionRange(el.value.length, el.value.length); });
          e.preventDefault();

        } else if (e.key !== "ArrowUp" && e.key !== "ArrowDown") {
          // Any other key resets browsing state
          idx   = -1;
          draft = "";
        }
      });
    }
  };
})();

'''

# ── 2. Anchor strings ─────────────────────────────────────────────────────────
ANCHOR_BEFORE_VFPRODUCTION = 'if (!window.VFProduction || !window.VFProduction._isVFProduction) {'

# In _executeTake, save text to history right before marking status=rendering
OLD_EXECUTE = '    take.status = "rendering";\n    take.error = "";'
NEW_EXECUTE  = ('    // Save text to history before rendering\n'
                '    if (window.VFTextHistory) window.VFTextHistory.push(take.text);\n'
                '    take.status = "rendering";\n'
                '    take.error = "";')

# In renderTakes textarea block, attach history after the input listener
OLD_TA_BLOCK = ('      ta.addEventListener("input", () => {\n'
                '        take.text = ta.value;\n'
                '        if (take.status === "done" || take.status === "error") {\n'
                '          take.status = "queued";\n'
                '          take.filename = "";\n'
                '          take.metadataFilename = "";\n'
                '          take.metadataUrl = "";\n'
                '          take.metadataDownloadUrl = "";\n'
                '          take.resolvedSeed = null;\n'
                '          take.resolvedSeeds = [];\n'
                '          take.routingMode = "";\n'
                '        }\n'
                '        this.refreshTakeMeta(take, idx);\n'
                '        this.updateToolbarState();\n'
                '      });\n'
                '      card.appendChild(ta);')

NEW_TA_BLOCK  = (OLD_TA_BLOCK.rstrip(';').rstrip()
                 + '\n      // Attach history navigation (Arrow Up / Down)\n'
                   '      if (window.VFTextHistory) window.VFTextHistory.attach(ta);\n'
                   '      card.appendChild(ta);')

# In init(), hook the reference text input after bindReferenceTextClear()
OLD_INIT_REF = '    this.bindReferenceTextClear();'
NEW_INIT_REF = ('    this.bindReferenceTextClear();\n'
                '    // Attach history to the reference text input (preview/calibration)\n'
                '    const _refInp = document.getElementById("vf-txt-reference");\n'
                '    if (_refInp && window.VFTextHistory) window.VFTextHistory.attach(_refInp);')

# ─────────────────────────────────────────────────────────────────────────────

for t in targets:
    p = pathlib.Path(t)
    text = p.read_text(encoding='utf-8')
    orig = text

    # 1. Inject VFTextHistory module before VFProduction definition
    if 'window.VFTextHistory' not in text:
        text = text.replace(
            ANCHOR_BEFORE_VFPRODUCTION,
            HISTORY_MODULE + ANCHOR_BEFORE_VFPRODUCTION
        )

    # 2. Save to history in _executeTake
    text = text.replace(OLD_EXECUTE, NEW_EXECUTE)

    # 3. Attach history to take textareas
    text = text.replace(OLD_TA_BLOCK, NEW_TA_BLOCK)

    # 4. Hook reference text input in init()
    text = text.replace(OLD_INIT_REF, NEW_INIT_REF)

    if text == orig:
        print(f'NO CHANGE: {t}')
        for label, old in [('VFTextHistory module', 'window.VFTextHistory'),
                            ('_executeTake save', OLD_EXECUTE[:40]),
                            ('TA block', OLD_TA_BLOCK[:40]),
                            ('init ref hook', OLD_INIT_REF[:40])]:
            print(f'  {label} found in orig: {old in orig}')
    else:
        p.write_text(text, encoding='utf-8')
        bom = p.read_bytes()[:3] == b'\xef\xbb\xbf'
        checks = {
            'module': 'window.VFTextHistory' in text,
            'push_in_execute': 'VFTextHistory.push(take.text)' in text,
            'attach_in_ta': 'VFTextHistory.attach(ta)' in text,
            'attach_refInp': 'VFTextHistory.attach(_refInp)' in text,
        }
        print(f'FIXED: {t}')
        print(f'  BOM:{bom}  ' + '  '.join(f'{k}:{v}' for k,v in checks.items()))
