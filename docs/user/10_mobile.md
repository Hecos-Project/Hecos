## 📱 10. Interfaccia Mobile-First e Audio WebRTC

Zentra è ottimizzato per l'uso su smartphone e tablet.
- **Menu Hamburger**: Su schermi piccoli, la sidebar scompare e viene sostituita da un menu a scorrimento (accessibile tramite l'icona `☰` in alto a sinistra).
- **Audio Push-to-Talk (PTT)**: Dal PC si usa `Ctrl+Shift` globale, mentre **da telefono o browser** si usa il pulsante Microfono accanto al box chat.
  - **Walkie-Talkie (Hold)**: Tieni premuto il pulsante 🎙️, parla, rilascia per inviare l'audio.
  - **Mani Libere (Tap-To-Toggle)**: Fai un click veloce sul pulsante 🎙️. Apparirà il lucchetto (🔴 🔓) e la registrazione continuerà mentre appoggi il telefono. Ripremi per stoppare e convertire in testo usando l'API client-side WebRTC nativa e il convertitore server-side locale Pydub.
- **Neural TTS Autoplay**: Nonostante i blocchi Apple/Android sui media, la sintesi vocale TTS partirà sempre automaticamente alla risposta usando un ingegnoso proxy player HTML5 integrato nel framework.
