/**
 * audio_encoder.js
 * Pure functionality for encoding an AudioBuffer to WAV format locally in-browser.
 */

window._audioBufferToWav = function(buffer) {
  const numChannels = 1; // Force mono for speech_recognition
  const sampleRate = 16000; // Force 16kHz
  
  return new Promise((resolve) => {
    const offlineCtx = new OfflineAudioContext(numChannels, buffer.duration * sampleRate, sampleRate);
    const source = offlineCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(offlineCtx.destination);
    source.start();
    offlineCtx.startRendering().then(renderedBuffer => {
      const length = renderedBuffer.length * 2;
      const wav = new ArrayBuffer(44 + length);
      const view = new DataView(wav);
      let offset = 0;
      
      function writeString(s) { for (let i=0; i<s.length; i++) { view.setUint8(offset + i, s.charCodeAt(i)); } offset += s.length; }
      
      writeString('RIFF');
      view.setUint32(offset, 36 + length, true); offset += 4;
      writeString('WAVE');
      writeString('fmt ');
      view.setUint32(offset, 16, true); offset += 4;
      view.setUint16(offset, 1, true); offset += 2;
      view.setUint16(offset, numChannels, true); offset += 2;
      view.setUint32(offset, sampleRate, true); offset += 4;
      view.setUint32(offset, sampleRate * 2, true); offset += 4;
      view.setUint16(offset, 2, true); offset += 2;
      view.setUint16(offset, 16, true); offset += 2;
      writeString('data');
      view.setUint32(offset, length, true); offset += 4;
      
      const channelData = renderedBuffer.getChannelData(0);
      let pcmIndex = 0;
      while (pcmIndex < channelData.length) {
        let s = Math.max(-1, Math.min(1, channelData[pcmIndex]));
        s = s < 0 ? s * 0x8000 : s * 0x7FFF;
        view.setInt16(offset, s, true);
        offset += 2;
        pcmIndex++;
      }
      resolve(new Blob([view], { type: 'audio/wav' }));
    });
  });
};
