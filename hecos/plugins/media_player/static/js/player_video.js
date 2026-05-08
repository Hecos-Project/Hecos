/**
 * Hecos Media Player — Video Submodule (player_video.js)
 * Handles rendering of video media in the player stage.
 */

(function (global) {
  'use strict';

  function render(stage, url) {
    var video = document.createElement('video');
    video.src       = url;
    video.controls  = true;
    video.autoplay  = true;
    video.playsInline = true;
    video.className = 'hmp-video';
    stage.appendChild(video);
  }

  global.HMPVideo = { render: render };

})(window);
