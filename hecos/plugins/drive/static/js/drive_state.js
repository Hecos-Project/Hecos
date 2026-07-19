// ─── Global State ────────────────────────────────────────────────────────────

let currentPath = "";        // currently visible directory (relative to drive root)
let allEntries  = [];        // all entries for the current directory
let sortKey     = "name";
let sortAsc     = true;
let treeData    = {};        // path → [dir entries], lazy cache

let currentRootLabel = "";   // e.g. "C:/"  – set from API response
let currentAbsPath   = "";   // full absolute path of current dir
