/**
 * Hecos Media Player — Filmstrip Submodule (player_filmstrip.js)
 * Renders the bottom thumbnail strip / dot navigation in the media player.
 */

(function (global) {
  'use strict';

  /**
   * @param {HTMLElement} container - The filmstrip element
   * @param {Array}   playlist  - Array of items
   * @param {number}  current   - Active index
   * @param {Function} urlFor   - Function to resolve item URL
   * @param {Function} onSelect - Callback(index)
   */
  function render(container, playlist, current, urlFor, onSelect) {
    if (!container) return;
    container.innerHTML = '';

    var useThumbs = playlist.length <= 24;

    playlist.forEach(function (item, i) {
      if (useThumbs) {
        var th = document.createElement('div');
        th.className = 'hmp-film-thumb' + (i === current ? ' active' : '');
        th.title = item.name || '';

        if (item.type === 'image') {
          var img = document.createElement('img');
          img.src     = urlFor(item);
          img.loading = 'lazy';
          th.appendChild(img);
        } else if (item.type === 'video') {
          th.textContent = '🎬';
        } else {
          th.textContent = '🎵';
        }

        th.addEventListener('click', function () { onSelect(i); });
        container.appendChild(th);

      } else {
        var dot = document.createElement('div');
        dot.className = 'hmp-film-dot' + (i === current ? ' active' : '');
        dot.title = item.name || '';
        dot.addEventListener('click', function () { onSelect(i); });
        container.appendChild(dot);
      }
    });

    // Scroll active item into view
    var active = container.querySelector('.active');
    if (active) {
      active.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
    }
  }

  global.HMPFilmstrip = { render: render };

})(window);
