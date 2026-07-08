# 📁 3. Módulos Core

Hecos se divide en distintos paquetes lógicos:

- `hecos.core.agent`: Gestiona el ciclo de razonamiento y la interacción con LiteLLM.
- `hecos.core.config`: Maneja la carga y validación de archivos YAML (Pydantic v2).
- `hecos.core.memory`: Base de datos SQLite y gestión de la persistencia de la arquitectura.
- `hecos.core.security`: Motor PKI para HTTPS y Sandbox AST para la ejecución segura de código.
- `hecos.hpm`: Directorio raíz para todos los módulos HPM y paquetes instalados.
- `hecos.core.package_manager`: Gestor de paquetes (HPM), instalación y validación de firmas (Ed25519) para módulos y plugins.

---

## Herramienta de Desarrollo HPM CLI

El sistema incluye una herramienta CLI para que los desarrolladores externos empaqueten y firmen sus módulos, ubicada en `scripts/hpm_cli.py`. Esta herramienta garantiza que ningún paquete pueda ser modificado después de su publicación.

### 1. Generación de Claves (Ed25519)
Para firmar paquetes, necesitas un par de claves.
```bash
python scripts/hpm_cli.py keygen --out-dir keys
```
- **`private.pem`**: Mantén esto en secreto. Sirve para firmar.
- **`public.pem`**: Compártela. Copia esta clave en `hecos/data/trusted_keys/` para que Hecos confíe en los paquetes firmados por ti.

### 2. Empaquetado y Firma (Pack & Sign)
Prepara el directorio de tu módulo (ej. `mi_modulo/`) asegurándote de que contenga el archivo `hpkg_manifest.toml`.
```bash
python scripts/hpm_cli.py pack --src mi_modulo/ --key keys/private.pem --out mi_modulo_v1.hpkg
```
El script calculará el hash (SHA-256) de cada archivo dentro del directorio, firmará el manifiesto usando la clave privada y creará un archivo `.hpkg` listo para su distribución.

> **Nota**: Durante el desarrollo local, puedes omitir la verificación de firma marcando "Allow unsigned packages" en la WebUI del Package Manager.
