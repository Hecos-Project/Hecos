/**
 * Voice Forge - Console Mixer & Slider State Orchestrator
 * Connects slider inputs, real-time value updates, audio preview playback, and profile baking.
 */

window.VFMixer = {
  radar: null,
  spectro: null,
  formants: null,
  currentAudioUrl: null,
  previewDebounceTimer: null,
  initialized: false,

  recipe: {
    id: "custom_timbre_1",
    name: "Custom Timbre",
    description: "Custom sculpted timbre",
    category: "custom",
    language: "it",
    reference_text: "Ma la volpe col suo balzo ha raggiunto il quieto fante all'ombra del tiglio fiorito.",
    source_type: "synthetic_fish",
    source_file: null,
    source_seed: 42,
    source_speaker: "af_heart",
    pitch_semitones: 0.0,
    pitch_dynamics: 1.0,
    vocal_tract_ratio: 1.0,
    breathiness: 0.0,
    roughness: 0.0,
    tremolo: 0.0,
    body_gain_db: 0.0,
    warmth_gain_db: 0.0,
    presence_gain_db: 0.0,
    air_gain_db: 0.0,
    tempo_ratio: 1.0,
    blend_source_file: null,
    blend_ratio: 0.0,
    tags: []
  },

  async init() {
    this.radar = new window.VFRadarChart("vf-canvas-radar");
    this.spectro = new window.VFSpectrogram("vf-canvas-spectro");
    this.formants = new window.VFFormantVisualizer("vf-formants-container");

    this.bindInputs();
    await this.loadLanguage(this.recipe.language || "it");
    this.updateReadouts();
    this.updatePredictedRadar();
    if (this.formants) this.formants.render([500, 1500, 2500, 3500], 1.0);
    this.initialized = true;
  },

  bindInputs() {
    const sliderMap = [
      { id: "vf-sl-pitch", key: "pitch_semitones", float: true },
      { id: "vf-sl-dyn", key: "pitch_dynamics", float: true },
      { id: "vf-sl-tract", key: "vocal_tract_ratio", float: true },
      { id: "vf-sl-breath", key: "breathiness", float: true },
      { id: "vf-sl-rough", key: "roughness", float: true },
      { id: "vf-sl-trem", key: "tremolo", float: true },
      { id: "vf-sl-body", key: "body_gain_db", float: true },
      { id: "vf-sl-warmth", key: "warmth_gain_db", float: true },
      { id: "vf-sl-presence", key: "presence_gain_db", float: true },
      { id: "vf-sl-air", key: "air_gain_db", float: true },
      { id: "vf-sl-blend", key: "blend_ratio", float: true }
    ];

    sliderMap.forEach(item => {
      const el = document.getElementById(item.id);
      if (el) {
        el.oninput = (e) => {
          this.recipe[item.key] = item.float ? parseFloat(e.target.value) : parseInt(e.target.value, 10);
          this.updateReadouts();
          this.updatePredictedRadar();
        };
      }
    });

    // Language change
    const langSel = document.getElementById("vf-sel-lang");
    if (langSel) {
      langSel.onchange = (e) => {
        this.recipe.language = e.target.value;
        this.loadLanguage(e.target.value);
      };
    }

    // Source type change
    const srcSel = document.getElementById("vf-sel-source-type");
    if (srcSel) {
      srcSel.onchange = (e) => {
        this.recipe.source_type = e.target.value;
        this.updateSourceUi();
      };
    }

    // Reference text change
    const refTxt = document.getElementById("vf-txt-reference");
    if (refTxt) {
      refTxt.oninput = (e) => {
        this.recipe.reference_text = e.target.value;
      };
    }

    // Custom File upload
    const fileInp = document.getElementById("vf-file-upload");
    if (fileInp) {
      fileInp.onchange = async (e) => {
        if (e.target.files && e.target.files[0]) {
          await this.uploadCustomSource(e.target.files[0]);
        }
      };
    }
  },

  async onLanguageSelect(lang) {
    this.recipe.language = lang;
    const langSel = document.getElementById("vf-sel-lang");
    if (langSel && langSel.value !== lang) langSel.value = lang;
    await this.loadLanguage(lang);
  },

  async loadLanguage(lang) {
    // 1. Instant update if window.VF_CORPUS_DATA is present
    if (window.VF_CORPUS_DATA && window.VF_CORPUS_DATA[lang]) {
      const cData = window.VF_CORPUS_DATA[lang];
      const corpusSel = document.getElementById("vf-sel-corpus");
      if (corpusSel && cData.samples && cData.samples.length > 0) {
        corpusSel.innerHTML = cData.samples.map(s => 
          `<option value="${encodeURIComponent(s.text)}">${s.label}</option>`
        ).join("");
        if (cData.samples[0]) {
          this.recipe.reference_text = cData.samples[0].text;
          const refTxt = document.getElementById("vf-txt-reference");
          if (refTxt) refTxt.value = cData.samples[0].text;
        }
      }
    }

    // 2. Query backend to ensure sync
    try {
      if (window.VFApi && window.VFApi.getCorpus) {
        const res = await window.VFApi.getCorpus(lang);
        if (res && res.ok && res.samples && res.samples.length > 0) {
          const corpusSel = document.getElementById("vf-sel-corpus");
          if (corpusSel) {
            corpusSel.innerHTML = res.samples.map(s => `
              <option value="${encodeURIComponent(s.text)}">${s.label}</option>
            `).join("");
            this.recipe.reference_text = res.samples[0].text;
            const refTxt = document.getElementById("vf-txt-reference");
            if (refTxt) refTxt.value = res.samples[0].text;
          }
        }
      }
    } catch (e) {
      console.warn("[VoiceForge] Corpus fetch notice:", e);
    }
  },

  onCorpusSelect(encodedText) {
    try {
      const text = decodeURIComponent(encodedText);
      this.recipe.reference_text = text;
      const refTxt = document.getElementById("vf-txt-reference");
      if (refTxt) refTxt.value = text;
    } catch (e) {
      console.error("[VoiceForge] Error selecting corpus:", e);
    }
  },

  updateSourceUi() {
    const seedBox = document.getElementById("vf-box-seed");
    const fileBox = document.getElementById("vf-box-file");
    if (seedBox) seedBox.style.display = this.recipe.source_type === "synthetic_fish" ? "flex" : "none";
    if (fileBox) fileBox.style.display = this.recipe.source_type === "file" ? "flex" : "none";
  },

  updateReadouts() {
    const setVal = (id, txt) => {
      const el = document.getElementById(id);
      if (el) el.textContent = txt;
    };

    setVal("vf-val-pitch", (this.recipe.pitch_semitones >= 0 ? "+" : "") + this.recipe.pitch_semitones.toFixed(1) + " st");
    setVal("vf-val-dyn", this.recipe.pitch_dynamics.toFixed(2) + "x");
    setVal("vf-val-tract", this.recipe.vocal_tract_ratio.toFixed(2) + "x");
    setVal("vf-val-breath", Math.round(this.recipe.breathiness * 100) + "%");
    setVal("vf-val-rough", Math.round(this.recipe.roughness * 100) + "%");
    setVal("vf-val-trem", Math.round(this.recipe.tremolo * 100) + "%");

    setVal("vf-val-body", (this.recipe.body_gain_db >= 0 ? "+" : "") + this.recipe.body_gain_db.toFixed(1) + " dB");
    setVal("vf-val-warmth", (this.recipe.warmth_gain_db >= 0 ? "+" : "") + this.recipe.warmth_gain_db.toFixed(1) + " dB");
    setVal("vf-val-presence", (this.recipe.presence_gain_db >= 0 ? "+" : "") + this.recipe.presence_gain_db.toFixed(1) + " dB");
    setVal("vf-val-air", (this.recipe.air_gain_db >= 0 ? "+" : "") + this.recipe.air_gain_db.toFixed(1) + " dB");
    setVal("vf-val-blend", Math.round(this.recipe.blend_ratio * 100) + "%");
  },

  updatePredictedRadar() {
    if (!this.radar) return;
    const pitchScore = Math.max(5, Math.min(100, 50 + (this.recipe.pitch_semitones * 4.2)));
    const dynScore = Math.max(5, Math.min(100, this.recipe.pitch_dynamics * 50));
    const tractScore = Math.max(5, Math.min(100, 50 + (1.0 - this.recipe.vocal_tract_ratio) * 150));
    const brightScore = Math.max(5, Math.min(100, 50 + (this.recipe.presence_gain_db + this.recipe.air_gain_db) * 2.5));
    const breathScore = Math.max(5, Math.min(100, this.recipe.breathiness * 95));
    const roughScore = Math.max(5, Math.min(100, this.recipe.roughness * 95));

    this.radar.setScores({
      pitch: pitchScore,
      dynamics: dynScore,
      vocal_tract: tractScore,
      brightness: brightScore,
      breath: breathScore,
      roughness: roughScore
    }, false);
  },

  async loadPreset(presetId) {
    try {
      // 1. Instant client-side fallback from bundled static recipes
      if (window.VF_STATIC_RECIPES && window.VF_STATIC_RECIPES[presetId]) {
        this.recipe = Object.assign({}, this.recipe, window.VF_STATIC_RECIPES[presetId]);
        this.syncSlidersToRecipe();
        const titleEl = document.getElementById("vf-current-preset-name");
        if (titleEl) titleEl.textContent = this.recipe.name;
      }

      // 2. Query backend API
      if (window.VFApi && window.VFApi.getRecipe) {
        const res = await window.VFApi.getRecipe(presetId);
        if (res && res.ok && res.recipe) {
          this.recipe = Object.assign({}, this.recipe, res.recipe);
          this.syncSlidersToRecipe();
          const titleEl = document.getElementById("vf-current-preset-name");
          if (titleEl) titleEl.textContent = this.recipe.name;
        }
      }
      if (window.showToast) window.showToast(`Preset applicato: ${this.recipe.name}`, "info");
    } catch (e) {
      console.error("[VoiceForge] Error loading preset:", e);
    }
  },

  syncSlidersToRecipe() {
    const setSlider = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val;
    };

    setSlider("vf-sl-pitch", this.recipe.pitch_semitones);
    setSlider("vf-sl-dyn", this.recipe.pitch_dynamics);
    setSlider("vf-sl-tract", this.recipe.vocal_tract_ratio);
    setSlider("vf-sl-breath", this.recipe.breathiness);
    setSlider("vf-sl-rough", this.recipe.roughness);
    setSlider("vf-sl-trem", this.recipe.tremolo);
    setSlider("vf-sl-body", this.recipe.body_gain_db);
    setSlider("vf-sl-warmth", this.recipe.warmth_gain_db);
    setSlider("vf-sl-presence", this.recipe.presence_gain_db);
    setSlider("vf-sl-air", this.recipe.air_gain_db);
    setSlider("vf-sl-blend", this.recipe.blend_ratio);

    const langSel = document.getElementById("vf-sel-lang");
    if (langSel) langSel.value = this.recipe.language || "it";
    this.loadLanguage(this.recipe.language || "it");

    const refTxt = document.getElementById("vf-txt-reference");
    if (refTxt && this.recipe.reference_text) refTxt.value = this.recipe.reference_text;

    const srcSel = document.getElementById("vf-sel-source-type");
    if (srcSel) srcSel.value = this.recipe.source_type || "synthetic_fish";

    this.updateSourceUi();
    this.updateReadouts();
    this.updatePredictedRadar();
  },

  async uploadCustomSource(file) {
    try {
      const btn = document.getElementById("vf-btn-upload-label");
      if (btn) btn.textContent = "Caricamento...";
      const res = await window.VFApi.uploadSourceAudio(file);
      if (res && res.ok) {
        this.recipe.source_file = res.file_path;
        this.recipe.source_type = "file";
        const srcSel = document.getElementById("vf-sel-source-type");
        if (srcSel) srcSel.value = "file";
        this.updateSourceUi();
        if (window.showToast) window.showToast(`Audio caricato con successo (${res.duration_seconds}s)`, "success");
      }
    } catch (e) {
      console.error("[VoiceForge] Upload failed:", e);
      if (window.showToast) window.showToast("Errore caricamento: " + e.message, "error");
    } finally {
      const btn = document.getElementById("vf-btn-upload-label");
      if (btn) btn.textContent = "Upload Audio";
    }
  },

  async triggerPreview() {
    const playBtn = document.getElementById("vf-btn-preview");
    const audioEl = document.getElementById("vf-audio-player");
    if (playBtn) {
      playBtn.classList.add("vf-pulsing");
      playBtn.disabled = true;
      playBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generazione preview...`;
    }

    try {
      const res = await window.VFApi.previewVoice(this.recipe);
      if (res && res.ok) {
        this.currentAudioUrl = res.audio_url;
        if (audioEl) {
          audioEl.src = res.audio_url + "?t=" + Date.now();
          audioEl.play().catch(e => console.log("Audio autoplay prevented", e));
        }

        if (this.radar && res.voice_dna) {
          this.radar.setScores(res.voice_dna, true);
        }
        if (this.spectro && res.spectrogram) {
          this.spectro.render(res.spectrogram);
        }
        if (this.formants && res.formants) {
          this.formants.render(res.formants, this.recipe.vocal_tract_ratio);
        }

        const setHud = (id, val) => {
          const el = document.getElementById(id);
          if (el) el.textContent = val;
        };
        if (res.f0_stats) setHud("vf-hud-f0", `${res.f0_stats.median_hz} Hz`);
        if (res.spectral_centroid_hz) setHud("vf-hud-centroid", `${res.spectral_centroid_hz} Hz`);
        if (res.hnr_db !== undefined) setHud("vf-hud-hnr", `${res.hnr_db} dB`);
        if (res.formants && res.formants.length >= 2) setHud("vf-hud-f1f2", `${Math.round(res.formants[0])} / ${Math.round(res.formants[1])} Hz`);
      } else {
        if (window.showToast) window.showToast(res.error || "Preview non riuscita", "error");
      }
    } catch (e) {
      console.error("[VoiceForge] Preview error:", e);
      if (window.showToast) window.showToast("Errore preview: " + e.message, "error");
    } finally {
      if (playBtn) {
        playBtn.classList.remove("vf-pulsing");
        playBtn.disabled = false;
        playBtn.innerHTML = `<i class="fas fa-play"></i> Listen Preview`;
      }
    }
  },

  async triggerBake() {
    const bakeBtn = document.getElementById("vf-btn-bake");
    if (bakeBtn) {
      bakeBtn.disabled = true;
      bakeBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Baking in corso...`;
    }

    try {
      const res = await window.VFApi.bakeVoice(this.recipe, true);
      if (res && res.ok) {
        if (window.showToast) {
          window.showToast(`Profilo "${res.meta.name}" registrato in Fish Speech!`, "success");
        }
        await window.VFPresets.refresh();
      } else {
        if (window.showToast) window.showToast(res.error || "Bake fallito", "error");
      }
    } catch (e) {
      console.error("[VoiceForge] Bake error:", e);
      if (window.showToast) window.showToast("Errore durante il bake: " + e.message, "error");
    } finally {
      if (bakeBtn) {
        bakeBtn.disabled = false;
        bakeBtn.innerHTML = `<i class="fas fa-fire"></i> Bake to Fish Speech`;
      }
    }
  }
};

window.vfOnLanguageChange = function(lang) {
  if (window.VFMixer && window.VFMixer.onLanguageSelect) {
    window.VFMixer.onLanguageSelect(lang);
  }
};
