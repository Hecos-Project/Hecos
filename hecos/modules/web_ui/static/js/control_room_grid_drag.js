/**
 * Hecos Control Room - Drag Module (GridStack.js)
 * GridStack handles all drag-and-drop natively.
 * This module is kept as a compatibility stub so other modules don't break.
 */
(function (global) {
    'use strict';

    // No-op: GridStack manages drag internally via grid.enableMove()
    const bindEvents = (card, grid) => {
        // Intentionally empty — GridStack owns drag/drop
    };

    global._roomGridDrag = { bindEvents };

})(window);
