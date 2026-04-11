# 📁 3. Módulos Core

### 📁 app/ (Capa de Aplicación)
- **`application.py`**: Orquestador principal.
- **`config.py`**: Gestor de YAML con validación Pydantic.

### 📁 core/ (Capa del Motor)
- **`llm/brain.py`**: El enrutador de backend.
- **`keys/key_manager.py`**: Motor de failover para llaves de API.
- **`processing/processore.py`**: Despachador de comandos lógicos.
