## 📁 3. Moduli Core

### 📁 app/ (Livello Applicativo)
- **`application.py`**: Orchestratore principale e loop TUI.
- **`config.py`**: Manager thread-safe per YAML + Pydantic.
- **`state_manager.py`**: Condivisione variabili runtime (singleton).

### 📁 core/ (Livello Engine)
- **`llm/brain.py`**: Il "Router" che sceglie il backend.
- **`keys/key_manager.py`**: Engine di failover per chiavi API multiple.
- **`processing/processore.py`**: Dispatcher logico per comandi e function calling.
- **`i18n/`**: Sistema di internazionalizzazione (singleton `translator.py`).
