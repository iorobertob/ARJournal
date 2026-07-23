/*
 * Attaches HLS playback (hls.js, or native HLS on Safari/iOS) to
 * <video data-hls> / <audio data-hls>, and applies download deterrents to all
 * protected players. Media is streamed in segments through signed URLs — there
 * is no single downloadable file, and the browser's download/PiP affordances
 * are removed. This deters casual downloading; it is not DRM.
 */
(function () {
  'use strict';

  function harden(el) {
    el.setAttribute('controlsList', 'nodownload noremoteplayback');
    try { el.disablePictureInPicture = true; } catch (e) {}
    el.addEventListener('contextmenu', function (e) { e.preventDefault(); });
  }

  function attachHls(el) {
    var url = el.getAttribute('data-hls');
    if (!url) return;
    harden(el);
    if (window.Hls && window.Hls.isSupported()) {
      var hls = new window.Hls({ maxBufferLength: 30, capLevelToPlayerSize: true });
      hls.loadSource(url);
      hls.attachMedia(el);
    } else if (el.canPlayType('application/vnd.apple.mpegurl')) {
      el.src = url;                       // Safari / iOS play HLS natively
    }
    // else: any <source> fallback in the markup is used as-is.
  }

  function init() {
    document.querySelectorAll('video[data-hls], audio[data-hls]').forEach(attachHls);
    document.querySelectorAll('video[data-protected], audio[data-protected]').forEach(harden);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
