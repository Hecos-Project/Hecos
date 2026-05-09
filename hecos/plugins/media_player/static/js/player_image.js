/**
 * Hecos Media Player — Image Submodule (player_image.js)
 * Handles rendering of images in the media player stage.
 * Supports pinch-to-zoom and double-click to zoom on desktop.
 */

(function (global) {
  'use strict';

  function render(stage, url, name) {
    var wrap = document.createElement('div');
    wrap.className = 'hmp-img-wrap';

    var img = document.createElement('img');
    img.src = url;
    img.alt = name || '';
    img.draggable = false;

    // Double-click zoom toggle
    var zoomed = false;
    img.addEventListener('dblclick', function () {
      zoomed = !zoomed;
      img.classList.toggle('hmp-img-zoomed', zoomed);
      wrap.style.overflow = zoomed ? 'auto' : 'hidden';
      wrap.style.cursor   = zoomed ? 'move'   : 'default';
    });

    wrap.appendChild(img);
    stage.appendChild(wrap);
  }

  global.HMPImage = { render: render };

})(window);
