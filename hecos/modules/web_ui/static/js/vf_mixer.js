/**
 * Voice Forge - Console Mixer & Slider State Orchestrator
 * Connects slider inputs, real-time value updates, audio preview playback, and profile baking.
 */

const VF_NEUTRAL_RECIPE = {
  id: "",
  name: "Custom Timbre (Neutral)",
  description: "Custom sculpted timbre",
  category: "custom",
  language: "en",
  reference_text: "The quick brown fox jumps over the lazy dog near the vibrant riverbank.",
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
};

window.VFMixer = {
  radar: null,
  spectro: null,
  formants: null,
  currentAudioUrl: null,
  previewDebounceTimer: null,
  initialized: false,

  activePresetMeta: {
    id: "",
    name: "Custom Timbre (Neutral)",
    sourceCategory: "neutral",
    isBuiltin: false
  },
  savedRecipeSnapshot: JSON.parse(JSON.stringify(VF_NEUTRAL_RECIPE)),
  recipe: JSON.parse(JSON.stringify(VF_NEUTRAL_RECIPE)),

  _cloneRecipe(obj) {
    return JSON.parse(JSON.stringify(obj || VF_NEUTRAL_RECIPE));
  },

  _modalPrompt(msg, defaultVal, onSave) {
    if (typeof window.hecosPrompt === "function") {
      window.hecosPrompt(msg, onSave, defaultVal);
    } else {
      const val = window.prompt(msg, defaultVal || "");
      if (val && val.trim()) onSave(val.trim());
    }
  },

  _modalConfirm(msg, onYes) {
    if (typeof window.hecosConfirm === "function") {
      window.hecosConfirm(msg, onYes);
    } else if (typeof window.hpmShowConfirm === "function") {
      window.hpmShowConfirm(msg, "Confirm", onYes);
    } else if (window.confirm(msg)) {
      onYes();
    }
  },

  _nextCustomName() {
    const customList = (window.VFPresets && window.VFPresets.allPresets && window.VFPresets.allPresets.custom) || [];
    const existingNames = new Set(customList.map(p => (p.name || "").trim().toLowerCase()));
    const existingIds = new Set(customList.map(p => (p.id || "").trim().toLowerCase()));
    let idx = 1;
    while (existingNames.has(`custom_${idx}`) || existingIds.has(`custom_${idx}`)) {
      idx++;
    }
    return `custom_${idx}`;
  },

  isDirty() {
    const base = this.savedRecipeSnapshot || VF_NEUTRAL_RECIPE;
    const keys = [
      "language", "reference_text", "source_type", "source_file", "source_seed", "source_speaker",
      "pitch_semitones", "pitch_dynamics", "vocal_tract_ratio",
      "breathiness", "roughness", "tremolo",
      "body_gain_db", "warmth_gain_db", "presence_gain_db", "air_gain_db",
      "blend_source_file", "blend_ratio"
    ];
    for (const k of keys) {
      const a = this.recipe[k] ?? "";
      const b = base[k] ?? "";
      if (typeof a === "number" || typeof b === "number") {
        if (Math.abs((Number(a) || 0) - (Number(b) || 0)) > 1e-4) return true;
      } else if (String(a) !== String(b)) {
        return true;
      }
    }
    return false;
  },

  updatePresetHeaderUi() {
    const titleEl = document.getElementById("vf-current-preset-name");
    if (titleEl) {
      titleEl.textContent = this.recipe.name || "Custom Timbre (Neutral)";
    }

    const badgeEl = document.getElementById("vf-preset-badge");
    const cat = this.activePresetMeta.sourceCategory;
    if (badgeEl) {
      if (cat === "custom") {
        badgeEl.textContent = "Custom";
        badgeEl.style.background = "rgba(6, 182, 212, 0.25)";
        badgeEl.style.color = "#67e8f9";
      } else if (cat === "base" || cat === "cinematic" || this.activePresetMeta.isBuiltin) {
        badgeEl.textContent = "Built-in";
        badgeEl.style.background = "rgba(255, 255, 255, 0.16)";
        badgeEl.style.color = "#f8fafc";
      } else {
        badgeEl.textContent = "Neutral";
        badgeEl.style.background = "rgba(148, 163, 184, 0.22)";
        badgeEl.style.color = "#cbd5e1";
      }
    }

    const dirtyEl = document.getElementById("vf-preset-dirty-dot");
    if (dirtyEl) {
      dirtyEl.style.display = this.isDirty() ? "inline-block" : "none";
    }

    const isSavedCustom = (cat === "custom" && Boolean(this.activePresetMeta.id));
    const renBtn = document.getElementById("vf-btn-rename-preset");
    const delBtn = document.getElementById("vf-btn-delete-preset");
    if (renBtn) renBtn.classList.toggle("is-disabled", !isSavedCustom);
    if (delBtn) delBtn.classList.toggle("is-disabled", !isSavedCustom);
  },

  async init() {
    this.radar = new window.VFRadarChart("vf-canvas-radar");
    this.spectro = new window.VFSpectrogram("vf-canvas-spectro");
    this.formants = new window.VFFormantVisualizer("vf-formants-container");

    this.bindInputs();
    await this.loadLanguage(this.recipe.language || "en", true);
    this.savedRecipeSnapshot = this._cloneRecipe(this.recipe);
    this.updateReadouts();
    this.updatePredictedRadar();
    this.updatePresetHeaderUi();
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
          this.updatePresetHeaderUi();
        };
      }
    });

    // Language change
    const langSel = document.getElementById("vf-sel-lang");
    if (langSel) {
      langSel.onchange = (e) => {
        this.recipe.language = e.target.value;
        this.loadLanguage(e.target.value, false);
        this.updatePresetHeaderUi();
      };
    }

    // Source type change
    const srcSel = document.getElementById("vf-sel-source-type");
    if (srcSel) {
      srcSel.onchange = (e) => {
        this.recipe.source_type = e.target.value;
        this.updateSourceUi();
        this.updatePresetHeaderUi();
      };
    }

    // Seed input change
    const seedInp = document.getElementById("vf-inp-seed");
    if (seedInp) {
      seedInp.oninput = (e) => {
        const parsed = parseInt(e.target.value, 10);
        if (!Number.isNaN(parsed)) {
          this.recipe.source_seed = parsed;
          this.updatePresetHeaderUi();
        }
      };
    }

    // Reference text change
    const refTxt = document.getElementById("vf-txt-reference");
    if (refTxt) {
      refTxt.oninput = (e) => {
        this.recipe.reference_text = e.target.value;
        this.updatePresetHeaderUi();
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
    await this.loadLanguage(lang, false);
    this.updatePresetHeaderUi();
  },

  async loadLanguage(lang, preserveRefText = false) {
    // 1. Instant update if window.VF_CORPUS_DATA is present
    if (window.VF_CORPUS_DATA && window.VF_CORPUS_DATA[lang]) {
      const cData = window.VF_CORPUS_DATA[lang];
      const corpusSel = document.getElementById("vf-sel-corpus");
      if (corpusSel && cData.samples && cData.samples.length > 0) {
        corpusSel.innerHTML = cData.samples.map(s => 
          `<option value="${encodeURIComponent(s.text)}">${s.label}</option>`
        ).join("");
        if ((!preserveRefText || !this.recipe.reference_text) && cData.samples[0]) {
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
            if (!preserveRefText || !this.recipe.reference_text) {
              this.recipe.reference_text = res.samples[0].text;
              const refTxt = document.getElementById("vf-txt-reference");
              if (refTxt) refTxt.value = res.samples[0].text;
            }
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
      this.updatePresetHeaderUi();
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

  async loadPreset(presetId, sourceCategory = null) {
    try {
      const isCustom = sourceCategory === "custom";
      const isBuiltin = !isCustom && (
        sourceCategory === "base"
        || sourceCategory === "cinematic"
        || presetId.startsWith("base_")
        || presetId.startsWith("cine_")
      );

      // 1. Instant client-side fallback from bundled static recipes (for built-ins)
      if (!isCustom && window.VF_STATIC_RECIPES && window.VF_STATIC_RECIPES[presetId]) {
        this.recipe = Object.assign(this._cloneRecipe(VF_NEUTRAL_RECIPE), window.VF_STATIC_RECIPES[presetId]);
        this.activePresetMeta = {
          id: this.recipe.id || presetId,
          name: this.recipe.name,
          sourceCategory: sourceCategory || this.recipe.category || (presetId.startsWith("cine_") ? "cinematic" : "base"),
          isBuiltin: true
        };
        this.savedRecipeSnapshot = this._cloneRecipe(this.recipe);
        this.syncSlidersToRecipe();
      }

      // 2. Query backend API for canonical data
      if (window.VFApi && window.VFApi.getRecipe) {
        const res = await window.VFApi.getRecipe(presetId, isCustom ? "custom" : null);
        if (res && res.ok && res.recipe) {
          this.recipe = Object.assign(this._cloneRecipe(VF_NEUTRAL_RECIPE), res.recipe);
          const resolvedCategory = isCustom
            ? "custom"
            : (sourceCategory || res.recipe.category || (isBuiltin ? (presetId.startsWith("cine_") ? "cinematic" : "base") : "custom"));
          this.activePresetMeta = {
            id: this.recipe.id,
            name: this.recipe.name,
            sourceCategory: resolvedCategory,
            isBuiltin: resolvedCategory !== "custom"
          };
          this.savedRecipeSnapshot = this._cloneRecipe(this.recipe);
          this.syncSlidersToRecipe();
        }
      }
      this.updatePresetHeaderUi();
      if (window.showToast) window.showToast(`Preset applied: ${this.recipe.name}`, "info");
    } catch (e) {
      console.error("[VoiceForge] Error loading preset:", e);
      if (window.showToast) window.showToast("Failed to load preset: " + e.message, "error");
    }
  },

  async _saveAsCustomNamed(presetName) {
    const cleanName = (presetName || "").trim();
    if (!cleanName) return;

    const customList = (window.VFPresets && window.VFPresets.allPresets && window.VFPresets.allPresets.custom) || [];
    if (customList.some(p => (p.name || "").trim().toLowerCase() === cleanName.toLowerCase())) {
      if (window.showToast) window.showToast(`A custom preset named '${cleanName}' already exists.`, "error");
      return;
    }

    const payload = this._cloneRecipe(this.recipe);
    payload.name = cleanName;
    payload.category = "custom";
    payload.description = payload.description && payload.description !== "Custom sculpted timbre"
      ? payload.description
      : `Custom sculpted timbre (${cleanName})`;

    const res = await window.VFApi.saveRecipe(payload, true);
    if (res && res.ok && res.recipe) {
      this.recipe = this._cloneRecipe(res.recipe);
      this.activePresetMeta = {
        id: this.recipe.id,
        name: this.recipe.name,
        sourceCategory: "custom",
        isBuiltin: false
      };
      this.savedRecipeSnapshot = this._cloneRecipe(this.recipe);
      this.syncSlidersToRecipe();
      this.updatePresetHeaderUi();
      if (window.VFPresets && window.VFPresets.refresh) {
        await window.VFPresets.refresh();
      }
      if (window.showToast) window.showToast(`Saved new custom profile '${this.recipe.name}'!`, "success");
    } else {
      throw new Error((res && res.error) || "Save failed");
    }
  },

  newPreset() {
    const defName = this._nextCustomName();
    this._modalPrompt("New Voice Forge Custom Profile Name:", defName, async (name) => {
      try {
        await this._saveAsCustomNamed(name);
      } catch (e) {
        console.error("[VoiceForge] Failed creating preset:", e);
        if (window.showToast) window.showToast("Save error: " + e.message, "error");
      }
    });
  },

  async updatePreset() {
    const isSavedCustom = (this.activePresetMeta.sourceCategory === "custom" && Boolean(this.activePresetMeta.id));
    if (!isSavedCustom) {
      const defName = this._nextCustomName();
      this._modalPrompt(
        "Built-in or neutral presets cannot be overwritten.\nEnter a name to save as a new custom profile:",
        defName,
        async (name) => {
          try {
            await this._saveAsCustomNamed(name);
          } catch (e) {
            console.error("[VoiceForge] Failed saving custom copy:", e);
            if (window.showToast) window.showToast("Save error: " + e.message, "error");
          }
        }
      );
      return;
    }

    try {
      const payload = this._cloneRecipe(this.recipe);
      payload.id = this.activePresetMeta.id;
      payload.category = "custom";
      const res = await window.VFApi.saveRecipe(payload, false);
      if (res && res.ok && res.recipe) {
        this.recipe = this._cloneRecipe(res.recipe);
        this.savedRecipeSnapshot = this._cloneRecipe(this.recipe);
        this.updatePresetHeaderUi();
        if (window.VFPresets && window.VFPresets.refresh) {
          await window.VFPresets.refresh();
        }
        if (window.showToast) window.showToast(`Preset '${this.recipe.name}' updated!`, "success");
      } else {
        throw new Error((res && res.error) || "Update failed");
      }
    } catch (e) {
      console.error("[VoiceForge] Failed updating preset:", e);
      if (window.showToast) window.showToast("Update error: " + e.message, "error");
    }
  },

  renamePreset(targetId = null, targetName = null) {
    const isCardCall = Boolean(targetId);
    const id = isCardCall ? targetId : this.activePresetMeta.id;
    const oldName = isCardCall ? (targetName || targetId) : (this.recipe.name || this.activePresetMeta.name);
    if (!id || (!isCardCall && this.activePresetMeta.sourceCategory !== "custom")) {
      if (window.showToast) window.showToast("Only saved Custom Profiles can be renamed. Click 'New' first.", "warning");
      return;
    }

    this._modalPrompt(`Rename custom profile '${oldName}' to:`, oldName, async (newName) => {
      const cleanName = (newName || "").trim();
      if (!cleanName || cleanName === oldName) return;

      const customList = (window.VFPresets && window.VFPresets.allPresets && window.VFPresets.allPresets.custom) || [];
      if (customList.some(p => p.id !== id && (p.name || "").trim().toLowerCase() === cleanName.toLowerCase())) {
        if (window.showToast) window.showToast(`A custom preset named '${cleanName}' already exists.`, "error");
        return;
      }

      try {
        const res = await window.VFApi.renameRecipe(id, cleanName);
        if (res && res.ok && res.recipe) {
          if (this.activePresetMeta.id === id) {
            this.recipe.name = res.recipe.name;
            this.activePresetMeta.name = res.recipe.name;
            if (this.savedRecipeSnapshot) this.savedRecipeSnapshot.name = res.recipe.name;
            this.updatePresetHeaderUi();
          }
          if (window.VFPresets && window.VFPresets.refresh) {
            await window.VFPresets.refresh();
          }
          if (window.showToast) window.showToast(`Preset renamed to '${res.recipe.name}'!`, "success");
        } else {
          throw new Error((res && res.error) || "Rename failed");
        }
      } catch (e) {
        console.error("[VoiceForge] Rename failed:", e);
        if (window.showToast) window.showToast("Rename error: " + e.message, "error");
      }
    });
  },

  resetPreset() {
    if (this.isDirty() && this.activePresetMeta.sourceCategory !== "neutral" && this.savedRecipeSnapshot) {
      this.recipe = this._cloneRecipe(this.savedRecipeSnapshot);
      this.syncSlidersToRecipe();
      this.updatePresetHeaderUi();
      if (window.showToast) window.showToast(`Sliders restored to '${this.recipe.name}'.`, "info");
      return;
    }

    this._modalConfirm("Reset all sculpting sliders and source settings to neutral defaults?", () => {
      this.recipe = this._cloneRecipe(VF_NEUTRAL_RECIPE);
      this.activePresetMeta = {
        id: "",
        name: VF_NEUTRAL_RECIPE.name,
        sourceCategory: "neutral",
        isBuiltin: false
      };
      this.savedRecipeSnapshot = this._cloneRecipe(VF_NEUTRAL_RECIPE);
      this.syncSlidersToRecipe();
      this.updatePresetHeaderUi();
      if (window.showToast) window.showToast("Mixer reset to neutral defaults.", "info");
    });
  },

  deletePreset(targetId = null, targetName = null) {
    const isCardCall = Boolean(targetId);
    const id = isCardCall ? targetId : this.activePresetMeta.id;
    const name = isCardCall ? (targetName || targetId) : (this.recipe.name || this.activePresetMeta.name);
    if (!id || (!isCardCall && this.activePresetMeta.sourceCategory !== "custom")) {
      if (window.showToast) window.showToast("Built-in or unsaved presets cannot be deleted.", "warning");
      return;
    }

    this._modalConfirm(`Are you sure you want to delete the custom profile '${name}'?`, async () => {
      try {
        const res = await window.VFApi.deleteRecipe(id);
        if (res && res.ok) {
          if (this.activePresetMeta.id === id) {
            this.recipe = this._cloneRecipe(VF_NEUTRAL_RECIPE);
            this.activePresetMeta = {
              id: "",
              name: VF_NEUTRAL_RECIPE.name,
              sourceCategory: "neutral",
              isBuiltin: false
            };
            this.savedRecipeSnapshot = this._cloneRecipe(VF_NEUTRAL_RECIPE);
            this.syncSlidersToRecipe();
            this.updatePresetHeaderUi();
          }
          if (window.VFPresets && window.VFPresets.refresh) {
            await window.VFPresets.refresh();
          }
          if (window.showToast) window.showToast(`Preset '${name}' deleted.`, "info");
        } else {
          throw new Error((res && res.error) || "Delete failed");
        }
      } catch (e) {
        console.error("[VoiceForge] Delete failed:", e);
        if (window.showToast) window.showToast("Delete error: " + e.message, "error");
      }
    });
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

    const seedInp = document.getElementById("vf-inp-seed");
    if (seedInp) seedInp.value = this.recipe.source_seed ?? 42;

    const langSel = document.getElementById("vf-sel-lang");
    if (langSel) langSel.value = this.recipe.language || "en";
    this.loadLanguage(this.recipe.language || "en", true);

    const refTxt = document.getElementById("vf-txt-reference");
    if (refTxt && this.recipe.reference_text !== undefined) refTxt.value = this.recipe.reference_text;

    const srcSel = document.getElementById("vf-sel-source-type");
    if (srcSel) srcSel.value = this.recipe.source_type || "synthetic_fish";

    this.updateSourceUi();
    this.updateReadouts();
    this.updatePredictedRadar();
    this.updatePresetHeaderUi();
  },

  async uploadCustomSource(file) {
    try {
      const btn = document.getElementById("vf-btn-upload-label");
      if (btn) btn.textContent = "Uploading...";
      console.debug("[VoiceForge] Uploading custom source audio:", file?.name, file?.size);
      const res = await window.VFApi.uploadSourceAudio(file);
      if (res && res.ok) {
        this.recipe.source_file = res.file_path;
        this.recipe.source_type = "file";
        const srcSel = document.getElementById("vf-sel-source-type");
        if (srcSel) srcSel.value = "file";
        this.updateSourceUi();
        this.updatePresetHeaderUi();
        if (window.showToast) window.showToast(`Audio uploaded successfully (${res.duration_seconds}s)`, "success");
      } else {
        throw new Error((res && res.error) || "Upload failed");
      }
    } catch (e) {
      console.error("[VoiceForge] Upload failed:", e);
      if (window.showToast) window.showToast("Upload error: " + e.message, "error");
    } finally {
      const btn = document.getElementById("vf-btn-upload-label");
      if (btn) btn.textContent = "Upload Audio";
    }
  },

  async _runWithProgress(title, prefix, fn) {
    const taskId = `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const progContainer = document.getElementById("vf-progress-container");
    let widget = null;
    let pollTimer = null;
    let pollBusy = false;

    if (progContainer && window.HecosProgress) {
      progContainer.style.display = "block";
      progContainer.innerHTML = "";
      widget = window.HecosProgress.attach(progContainer, {
        variant: "card",
        taskId: taskId,
        title: title,
        showCancel: false,
        showLog: true
      });
      widget.update({
        id: taskId,
        title: title,
        state: "running",
        percent: 2,
        message: "Connecting to Voice Forge pipeline..."
      });

      const pollOnce = async () => {
        if (pollBusy) return;
        pollBusy = true;
        try {
          const pr = await fetch(`/api/progress/${encodeURIComponent(taskId)}`, {
            credentials: "same-origin"
          });
          if (pr.ok) {
            const pd = await pr.json();
            if (pd && pd.ok && pd.task && widget) {
              widget.update(pd.task);
            }
          }
        } catch (_err) {
          // Ignore transient poll errors while SSE is active
        } finally {
          pollBusy = false;
        }
      };
      pollTimer = setInterval(pollOnce, 600);
    }

    try {
      const res = await fn(taskId);
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
      if (widget) {
        if (res && res.ok) {
          widget.update({
            state: "done",
            percent: 100,
            message: `${title} complete`
          });
        } else {
          const errText = (res && res.error) ? res.error : `${title} failed`;
          widget.update({
            state: "error",
            message: errText,
            error: errText
          });
        }
      }
      return res;
    } catch (e) {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
      if (widget) {
        widget.update({
          state: "error",
          message: e.message || `${title} error`,
          error: e.message || "Unexpected error"
        });
      }
      throw e;
    }
  },

  async triggerPreview() {
    const playBtn = document.getElementById("vf-btn-preview");
    const audioEl = document.getElementById("vf-audio-player");
    if (playBtn) {
      playBtn.classList.add("vf-pulsing");
      playBtn.disabled = true;
      playBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generating preview...`;
    }

    try {
      const title = `Preview: ${this.recipe.name || "Voice"}`;
      console.debug("[VoiceForge] Starting preview generation", { name: this.recipe.name, source: this.recipe.source_type, lang: this.recipe.language });
      const res = await this._runWithProgress(title, "vf_prev", (taskId) => window.VFApi.previewVoice(this.recipe, taskId));
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
        const msg = (res && res.error) ? res.error : "Preview failed";
        if (window.showToast) window.showToast(msg, "error");
      }
    } catch (e) {
      console.error("[VoiceForge] Preview error:", e);
      if (window.showToast) window.showToast("Preview error: " + e.message, "error");
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
      bakeBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Baking...`;
    }

    try {
      const title = `Bake to Fish Speech: ${this.recipe.name || "Voice"}`;
      console.debug("[VoiceForge] Starting bake", { name: this.recipe.name, id: this.recipe.id });
      const res = await this._runWithProgress(title, "vf_bake", (taskId) => window.VFApi.bakeVoice(this.recipe, true, taskId));
      if (res && res.ok) {
        if (window.showToast) {
          window.showToast(`Profile "${res.meta.name}" registered in Fish Speech!`, "success");
        }
        await window.VFPresets.refresh();
      } else {
        const msg = (res && res.error) ? res.error : "Bake failed";
        if (window.showToast) window.showToast(msg, "error");
      }
    } catch (e) {
      console.error("[VoiceForge] Bake error:", e);
      if (window.showToast) window.showToast("Bake error: " + e.message, "error");
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
