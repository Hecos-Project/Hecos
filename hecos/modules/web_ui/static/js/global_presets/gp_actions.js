/* ⚡ SOUL FORGE: gp_actions.js — Session Draft Sync, Promotion & Quick Test Lab */

window.sfSaveDraftToSession = async function() {
    const sessionId = window.sfGetActiveSessionId ? window.sfGetActiveSessionId() : null;
    if (!sessionId) return;

    const newData = window.sfCollectUIState();
    try {
        const res = await fetch('/api/chat/session/config', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ session_id: sessionId, config: newData })
        });
        if (res.ok) {
            const msgEl = document.getElementById('sf-status-msg');
            if (msgEl) {
                msgEl.textContent = "✓ Live draft active for this chat";
                clearTimeout(window._sfStatusClearTimer);
                window._sfStatusClearTimer = setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 2500);
            }
        }
    } catch(e) {
        console.warn("Failed to save session draft", e);
    }
};

window.sfSaveAsNewSoul = function() {
    window.hecosPrompt("Enter name for the new Global Preset:", async function(name) {
        if (!name) return;
        
        const id = name.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const data = window.sfCollectUIState();
        data.meta = { id: id, name: name, icon: "⚡" };
        
        try {
            const res = await fetch('/api/souls', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(data)
            });
            if (res.ok) {
                await window.sfLoadData();
                await window.sfSelectSessionSoul(id);
                if (window.showToast) window.showToast(`Global Preset "${name}" created!`, "success");
            }
        } catch(e) {}
    });
};

window.soSaveAsNewSoul = window.sfSaveAsNewSoul;

window.sfSaveInlineToActive = async function() {
    const soulId = window.sfState.activeSoulId;
    if (!soulId) return;
    
    const soulObj = window.sfState.souls.find(s => s.meta.id === soulId);
    if (!soulObj) return;
    
    const newData = window.sfCollectUIState();
    newData.meta = soulObj.meta;
    
    try {
        const res = await fetch('/api/souls', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(newData)
        });
        if (res.ok) {
            Object.assign(soulObj, newData);
            window.sfState.baselineState = JSON.parse(JSON.stringify(window.sfCollectUIState()));

            // If this preset is also the system-wide default, keep system.yaml/audio.yaml synced
            if (window.sfState.globalDefaultSoulId === soulId) {
                await fetch('/api/souls/activate', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({ soul_id: soulId, session_id: 'global' })
                });
                if (window.sfUpdateTooltip) window.sfUpdateTooltip(newData, soulId);
            }

            window.sfRefreshUIVisibilityAndSummaries();
            const msgEl = document.getElementById('sf-status-msg');
            if (msgEl) {
                msgEl.textContent = `✓ Preset "${soulObj.meta.name}" updated.`;
                setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 3000);
            }
            if (window.showToast) window.showToast(`Preset "${soulObj.meta.name}" updated!`, "success");
        }
    } catch(e) {}
};

window.sfOverwriteSoul = function() {
    if (!window.sfState.activeSoulId) {
        if (window.showToast) window.showToast("Please select a Global Preset to update first, or click 'New Preset' or 'Use as Default'.", "error");
        return;
    }
    const soulObj = window.sfState.souls.find(s => s.meta.id === window.sfState.activeSoulId);
    const pName = soulObj?.meta?.name || window.sfState.activeSoulId;
    window.hecosConfirm(`Do you want to overwrite Global Preset "${pName}" with current settings?`, function() {
        window.sfSaveInlineToActive();
    });
};

window.soOverwriteSoul = window.sfOverwriteSoul;

window.sfSetAsGlobalDefault = function() {
    const soulId = window.sfState.activeSoulId;
    if (soulId) {
        const soulObj = window.sfState.souls.find(s => s.meta.id === soulId);
        const pName = soulObj?.meta?.name || soulId;
        const msg = window.sfState.isDirty
            ? `Save changes to preset "${pName}" and set it as Global Default for all new chats?`
            : `Set preset "${pName}" as Global Default for all new chats?`;
        window.hecosConfirm(msg, async function() {
            if (window.sfState.isDirty) {
                await window.sfSaveInlineToActive();
            }
            await window.sfActivateSoul(soulId);
            if (window.showToast) window.showToast(`⭐ "${pName}" set as Global Default!`, "success");
        });
    } else {
        window.hecosConfirm(
            "Save current configuration (Backend, Model, Soul, Inference, Payload, Voice) directly as System Global Default without using a preset?",
            async function() {
                const data = window.sfCollectUIState();
                data.meta = { id: "", name: "Base Defaults", icon: "⚙️" };
                await window.sfActivateSoul("", data);
                if (window.showToast) window.showToast("⭐ Base Configuration saved as Global Default!", "success");
            }
        );
    }
};

window.sfRevertSessionDraft = function() {
    const sessionId = window.sfGetActiveSessionId ? window.sfGetActiveSessionId() : null;
    window.hecosConfirm("Discard changes for this chat and revert to default settings?", async function() {
        if (sessionId) {
            await fetch('/api/souls/activate', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({ soul_id: "", session_id: sessionId })
            });
        }
        await window.sfLoadActiveSessionState();
        const msgEl = document.getElementById('sf-status-msg');
        if (msgEl) {
            msgEl.textContent = "↺ Chat modifications discarded.";
            setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 3000);
        }
        if (window.HecosWelcome && window.HecosWelcome.show) window.HecosWelcome.show();
    });
};

window.sfRevertSoul = window.sfRevertSessionDraft;
window.soRevertSoul = window.sfRevertSessionDraft;

window.sfRenameSoul = function() {
    const soulId = window.sfState.activeSoulId;
    if (!soulId) {
        if (window.showToast) window.showToast("No Global Preset selected to rename.", "error");
        return;
    }
    const soulObj = window.sfState.souls.find(s => s.meta.id === soulId);
    if (!soulObj) return;

    window.hecosPrompt("Enter new name for the Global Preset:", async function(newName) {
        if (!newName || newName === soulObj.meta.name) return;
        
        const newData = window.sfCollectUIState();
        newData.meta = { ...soulObj.meta, name: newName };
        
        try {
            const res = await fetch('/api/souls', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(newData)
            });
            if (res.ok) {
                await window.sfLoadData();
                const msgEl = document.getElementById('sf-status-msg');
                if (msgEl) {
                    msgEl.textContent = "Global Preset renamed.";
                    setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 3000);
                }
            }
        } catch(e) {}
    });
};

window.sfDeleteSoul = function() {
    const soulId = window.sfState.activeSoulId;
    if (!soulId) {
        if (window.showToast) window.showToast("No Global Preset selected to delete.", "error");
        return;
    }
    const soulObj = window.sfState.souls.find(s => s.meta.id === soulId);
    const pName = soulObj?.meta?.name || soulId;
    window.hecosConfirm(`Are you sure you want to permanently delete Global Preset "${pName}"?`, async function() {
        try {
            const res = await fetch(`/api/souls/${soulId}`, { method: 'DELETE' });
            if (res.ok) {
                if (window.sfState.globalDefaultSoulId === soulId) {
                    await fetch('/api/souls/activate', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify({ soul_id: "", session_id: 'global' })
                    });
                }
                const sessionId = window.sfGetActiveSessionId ? window.sfGetActiveSessionId() : null;
                if (sessionId) {
                    await fetch('/api/souls/activate', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify({ soul_id: "", session_id: sessionId })
                    });
                }
                await window.sfLoadData();
                const msgEl = document.getElementById('sf-status-msg');
                if (msgEl) {
                    msgEl.textContent = "Global Preset deleted.";
                    setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 3000);
                }
            } else {
                if (window.showToast) window.showToast("Error during deletion.", "error");
            }
        } catch(e) {
            if (window.showToast) window.showToast("Error during deletion.", "error");
        }
    });
};

window.sfExportSoul = async function() {
    const soulId = window.sfState.activeSoulId;
    if (!soulId) {
        if (window.showToast) window.showToast("No Global Preset selected to export.", "error");
        return;
    }
    try {
        const res = await fetch(`/api/souls/${soulId}`);
        const data = await res.json();
        if (data.ok && data.soul) {
            const blob = new Blob([JSON.stringify(data.soul, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${soulId}.global_preset.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    } catch(e) { console.error(e); }
};

window.sfImportSoul = function(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const soulData = JSON.parse(e.target.result);
            const res = await fetch('/api/souls', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(soulData)
            });
            if (res.ok) {
                const d = await res.json();
                await window.sfLoadData();
                if (d.soul_id) await window.sfSelectSessionSoul(d.soul_id);
                const msgEl = document.getElementById('sf-status-msg');
                if (msgEl) {
                    msgEl.textContent = "Preset imported successfully.";
                    setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 3000);
                }
            }
        } catch(err) {
            if (window.showToast) window.showToast("Invalid JSON file.", "error");
        }
        event.target.value = '';
    };
    reader.readAsText(file);
};

// ── Voice Preview (▶ Preview Voice) ──────────────────────────────────────────

window._sfVoiceAudio = null;
window._sfVoiceEvtSource = null;

window.sfStopVoicePreview = function() {
    if (window._sfVoiceEvtSource) {
        window._sfVoiceEvtSource.close();
        window._sfVoiceEvtSource = null;
    }
    if (window._sfVoiceAudio) {
        window._sfVoiceAudio.pause();
        window._sfVoiceAudio = null;
    }
    fetch('/api/audio/stop', { method: 'POST' }).catch(() => {});
    const btn = document.getElementById('sf-voice-preview-btn');
    if (btn) {
        btn.innerHTML = '<i class="fas fa-play"></i> Preview Voice';
        btn.disabled = false;
    }
};

window.sfPreviewVoice = async function(customText) {
    const btn = document.getElementById('sf-voice-preview-btn');
    if (window._sfVoiceEvtSource || (window._sfVoiceAudio && !window._sfVoiceAudio.paused)) {
        window.sfStopVoicePreview();
        return;
    }

    const textToSpeak = (customText && typeof customText === 'string' && customText.trim())
        ? customText.trim()
        : "Hello, I am Hecos. This is a preview of the selected voice and audio parameters.";

    if (btn) {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Synthesizing... (Stop)';
    }

    const sessionId = window.sfGetActiveSessionId ? window.sfGetActiveSessionId() : null;
    const draft = window.sfCollectUIState();

    try {
        const res = await fetch('/api/audio/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: textToSpeak,
                mode: 'web',
                bypass_cache: true,
                session_id: sessionId,
                engine: draft.voice?.tts_engine,
                draft: draft
            })
        });
        const data = await res.json();
        if (!data.ok || !data.job_id) {
            window.sfStopVoicePreview();
            if (window.showToast) window.showToast("Failed to start voice test", "error");
            return;
        }

        const es = new EventSource(`/api/audio/test/progress/${data.job_id}`);
        window._sfVoiceEvtSource = es;

        es.onmessage = (event) => {
            const prog = JSON.parse(event.data);
            if (prog.status === 'not_found' || prog.status === 'error') {
                window.sfStopVoicePreview();
                if (window.showToast) window.showToast(`❌ ${prog.error || 'TTS Error'}`, "error");
                return;
            }
            if (prog.total > 0 && btn) {
                const pct = Math.round((prog.current / prog.total) * 100);
                btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${pct}% (Stop)`;
            }
            if (prog.status === 'done') {
                es.close();
                window._sfVoiceEvtSource = null;
                const audioUrl = prog.audio_id
                    ? `/api/audio?id=${encodeURIComponent(prog.audio_id)}`
                    : `/api/audio?t=${Date.now()}`;
                const audio = new Audio(audioUrl);
                window._sfVoiceAudio = audio;
                if (btn) btn.innerHTML = '<i class="fas fa-stop"></i> Stop Audio';
                audio.onended = () => {
                    window._sfVoiceAudio = null;
                    if (btn) btn.innerHTML = '<i class="fas fa-play"></i> Preview Voice';
                };
                audio.onerror = () => {
                    window._sfVoiceAudio = null;
                    if (btn) btn.innerHTML = '<i class="fas fa-play"></i> Preview Voice';
                };
                audio.play().catch(() => {
                    window._sfVoiceAudio = null;
                    if (btn) btn.innerHTML = '<i class="fas fa-play"></i> Preview Voice';
                });
            }
        };

        es.onerror = () => {
            window.sfStopVoicePreview();
        };
    } catch (e) {
        console.error("sfPreviewVoice error", e);
        window.sfStopVoicePreview();
    }
};

// ── Quick Test Lab (▶ Ephemeral LLM Response Test) ───────────────────────────

window.sfRunLabTest = async function() {
    const promptEl = document.getElementById('sf-lab-prompt');
    const runBtn = document.getElementById('sf-lab-run-btn');
    const outBox = document.getElementById('sf-lab-output');
    const metricsEl = document.getElementById('sf-lab-metrics');
    const thinkBox = document.getElementById('sf-lab-thinking-box');
    const thinkText = document.getElementById('sf-lab-thinking-text');
    const respEl = document.getElementById('sf-lab-response');
    const speakBtn = document.getElementById('sf-lab-speak-btn');
    const ttsCheck = document.getElementById('sf-lab-tts');

    const prompt = (promptEl?.value || "Briefly introduce yourself in two sentences.").trim();
    if (!prompt) return;

    if (runBtn) {
        runBtn.disabled = true;
        runBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Test...';
    }
    if (outBox) outBox.style.display = 'flex';
    if (metricsEl) metricsEl.innerHTML = '<span class="sf-lab-chip"><i class="fas fa-spinner fa-spin"></i> Generating test response...</span>';
    if (thinkBox) thinkBox.style.display = 'none';
    if (respEl) respEl.textContent = '';
    if (speakBtn) speakBtn.style.display = 'none';

    const sessionId = window.sfGetActiveSessionId ? window.sfGetActiveSessionId() : null;
    const draft = window.sfCollectUIState();

    try {
        const res = await fetch('/api/souls/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                session_id: sessionId,
                draft: draft
            })
        });
        const data = await res.json();
        if (!data.ok) {
            if (metricsEl) metricsEl.innerHTML = `<span class="sf-lab-chip" style="color:#f87171;">❌ Error: ${data.error || 'Test failed'}</span>`;
            return;
        }

        window.sfState.lastLabResponse = data.response || "";
        const m = data.metrics || {};

        if (metricsEl) {
            const toolsBadge = m.send_tools
                ? `🛠️ ${m.tools_count || 0} tools`
                : `🛠️ Tools OFF`;
            const soulBadge = m.send_personality ? `🎭 Soul ON` : `🎭 Soul OFF`;
            const memBadge = m.send_memory ? `🧠 Mem ON` : `🧠 Mem OFF`;
            metricsEl.innerHTML = [
                `<span class="sf-lab-chip">⏱️ ${m.elapsed_sec ?? '?'}s</span>`,
                `<span class="sf-lab-chip">⚡ ${m.tok_per_sec ?? '?'} tok/s</span>`,
                `<span class="sf-lab-chip">🤖 ${m.model || '?'}</span>`,
                `<span class="sf-lab-chip">🌡️ Temp ${m.temperature ?? '?'}</span>`,
                `<span class="sf-lab-chip">📦 ~${m.prompt_tokens ?? 0} prompt tok</span>`,
                `<span class="sf-lab-chip">${toolsBadge}</span>`,
                `<span class="sf-lab-chip">${soulBadge} · ${memBadge}</span>`
            ].join('');
        }

        if (data.thinking && thinkBox && thinkText) {
            thinkText.textContent = data.thinking;
            thinkBox.style.display = 'block';
        }
        if (respEl) {
            respEl.textContent = data.response || '(No text response)';
        }
        if (speakBtn && data.response) {
            speakBtn.style.display = 'inline-block';
        }
        if (ttsCheck && ttsCheck.checked && data.response) {
            window.sfPreviewVoice(data.response);
        }
    } catch (e) {
        if (metricsEl) metricsEl.innerHTML = `<span class="sf-lab-chip" style="color:#f87171;">❌ Network error: ${e.message}</span>`;
    } finally {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.innerHTML = '<i class="fas fa-play"></i> Test';
        }
    }
};

window.sfSpeakLabResponse = function() {
    if (window.sfState.lastLabResponse) {
        window.sfPreviewVoice(window.sfState.lastLabResponse);
    }
};
