/**
 * palettes.js
 * Static copy of HECOS_PALETTES embedded inside the React bundle.
 * This avoids race conditions with window.HECOS_PALETTES loading order.
 *
 * Keep in sync with:
 *   hecos/modules/web_ui/static/js/aesthetic_picker/palettes.js
 */
const PALETTES = {
  dark: [
    { label: "Dark Slate",     hex: "#1e293b" },
    { label: "Midnight Space", hex: "#0f172a" },
    { label: "Deep Crimson",   hex: "#450a0a" },
    { label: "Forest Night",   hex: "#064e3b" },
    { label: "Plum",           hex: "#2e1065" },
    { label: "Dark Mocha",     hex: "#3f2c25" },
  ],
  light: [
    { label: "Soft Pearl",      hex: "#f8fafc" },
    { label: "Sky Blue",        hex: "#f0f9ff" },
    { label: "Mint Glass",      hex: "#ecfdf5" },
    { label: "Blush Rose",      hex: "#fff1f2" },
    { label: "Lavender Dream",  hex: "#f5f3ff" },
    { label: "Warm Sand",       hex: "#fafaf9" },
  ],
  vibrant: [
    { label: "Electric Blue",  hex: "#3b82f6" },
    { label: "Neon Pink",      hex: "#ec4899" },
    { label: "Volt Green",     hex: "#84cc16" },
    { label: "Sunset Orange",  hex: "#f97316" },
    { label: "Cyber Yellow",   hex: "#eab308" },
    { label: "Deep Violet",    hex: "#8b5cf6" },
  ],
};

/**
 * Returns the merged palette object: built-in + any extras from window.HECOS_PALETTES
 * that the host page may have injected.
 */
export function getPalettes() {
  const win = (typeof window !== 'undefined' && window.HECOS_PALETTES) || {};
  return { ...PALETTES, ...win };
}

export default PALETTES;
