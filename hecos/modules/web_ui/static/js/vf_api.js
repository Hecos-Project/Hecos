/**
 * Voice Forge - API Client
 * Wraps backend endpoints for recipes, preview synthesis, baking, and corpus.
 */

window.VFApi = {
  baseUrl: "/hecos/api/plugins/voice_forge",

  async _fetchJson(url, options = {}) {
    const defaultHeaders = {
      "Accept": "application/json",
      "X-Requested-With": "XMLHttpRequest"
    };
    if (options.body && typeof options.body === "string") {
      defaultHeaders["Content-Type"] = "application/json";
    }
    const finalOptions = Object.assign({
      credentials: "same-origin",
      headers: Object.assign(defaultHeaders, options.headers || {})
    }, options);

    const res = await fetch(url, finalOptions);
    if (!res.ok) {
      let errMsg = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        if (errJson && errJson.error) errMsg = errJson.error;
      } catch (e) {}
      console.error("[VoiceForge:API] Request failed:", url, errMsg);
      throw new Error(errMsg);
    }
    return await res.json();
  },

  async getLanguages() {
    return await this._fetchJson(`${this.baseUrl}/languages`);
  },

  async getCorpus(lang) {
    return await this._fetchJson(`${this.baseUrl}/corpus?lang=${encodeURIComponent(lang)}`);
  },

  async getPresets() {
    return await this._fetchJson(`${this.baseUrl}/presets`);
  },

  async getRecipe(id) {
    return await this._fetchJson(`${this.baseUrl}/recipe/${encodeURIComponent(id)}`);
  },

  async saveRecipe(recipe) {
    return await this._fetchJson(`${this.baseUrl}/recipe`, {
      method: "POST",
      body: JSON.stringify(recipe)
    });
  },

  async deleteRecipe(id) {
    return await this._fetchJson(`${this.baseUrl}/recipe/${encodeURIComponent(id)}`, {
      method: "DELETE"
    });
  },

  async previewVoice(recipe, taskId = null) {
    const payload = Object.assign({}, recipe);
    if (taskId) payload.task_id = taskId;
    console.debug("[VoiceForge:API] POST /preview", { taskId, name: recipe?.name, source: recipe?.source_type, language: recipe?.language });
    return await this._fetchJson(`${this.baseUrl}/preview`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  async bakeVoice(recipe, registerInAudioYaml = true, taskId = null) {
    const payload = { recipe, register_in_audio_yaml: registerInAudioYaml };
    if (taskId) payload.task_id = taskId;
    console.debug("[VoiceForge:API] POST /bake", { taskId, name: recipe?.name, registerInAudioYaml });
    return await this._fetchJson(`${this.baseUrl}/bake`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  async generateSeed(text, seed) {
    return await this._fetchJson(`${this.baseUrl}/generate_seed`, {
      method: "POST",
      body: JSON.stringify({ text, seed })
    });
  },

  async uploadSourceAudio(file) {
    const formData = new FormData();
    formData.append("audio_file", file);
    const res = await fetch(`${this.baseUrl}/upload_source`, {
      method: "POST",
      credentials: "same-origin",
      body: formData
    });
    if (!res.ok) {
      throw new Error(`Upload failed: HTTP ${res.status}`);
    }
    return await res.json();
  }
};
