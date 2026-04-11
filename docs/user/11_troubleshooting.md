## 🛠️ 11. Risoluzione Problemi Hardware

1. **Bug dell'interferenza grafica (Dashboard):** L'engine di Zentra unisce asincronamente i thread UI. Ogni compenetrazione di testi è risolta dal blocco totale `(Thread Join)` ad inizio chiamata del menu F7.
2. **Logs:** I Log di Zentra si conservano nella directory `/logs`. Da Config F7 è possibile nascondere il report log dalla chat per favorire leggibilità di testo.
3. **Loop di Innesco Audio:** Regolare il parametro `Soglia Energia` in **F7 → Ascolto** per calibrare i rumori di fondo ambientali se il microfono hardware è impazzito.
