## 🛠️ 5. Best Practices Sviluppatori

- **Usa sempre `logger`**: Evita il `print` diretto; usa `core.logging.logger`.
- **Sync vs Async**: Usa i lock forniti se chiami la UI da thread di background.
- **Persistenza Config**: Usa `config_manager.set(...)` e `save()` per mantenere la coerenza tra sessioni.
- **Modularità**: Mantieni i plugin isolati e usa il sistema di estensioni per funzionalità pesanti.
