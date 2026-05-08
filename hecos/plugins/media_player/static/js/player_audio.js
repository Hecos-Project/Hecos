/**
 * Hecos Media Player — Audio Submodule (player_audio.js)
 * Handles rendering of audio media in the player stage.
 */

(function (global) {
  'use strict';

  function render(stage, url, name) {
    var wrap = document.createElement('div');
    wrap.id = 'hmp-audio-cover';

    var icon = document.createElement('div');
    icon.className   = 'hmp-audio-icon';
    icon.textContent = '🎵';

    var label = document.createElement('div');
    label.className   = 'hmp-audio-name';
    label.textContent = name || '';

    var audio = document.createElement('audio');
    audio.src      = url;
    audio.controls = true;
    audio.autoplay = true;

    wrap.appendChild(icon);
    wrap.appendChild(label);
    wrap.appendChild(audio);
    stage.appendChild(wrap);
  }

  global.HMPAudio = { render: render };

})(window);
