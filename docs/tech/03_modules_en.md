# 📁 3. Core Modules

Hecos is divided into distinct logical packages:

- `hecos.core.agent`: Manages the reasoning cycle and interaction with LiteLLM.
- `hecos.core.config`: Handles loading and validation of YAML files (Pydantic v2).
- `hecos.core.memory`: SQLite database and persistence architecture management.
- `hecos.core.security`: PKI engine for HTTPS and AST Sandbox for secure code execution.
- `hecos.hpm`: Root directory for all HPM modules and installed packages.
- `hecos.core.package_manager`: Package Manager (HPM), handling installation and signature validation (Ed25519) for modules and plugins.

---

## HPM CLI Development Tool

The system includes a CLI tool for third-party developers to pack and sign their modules, located at `scripts/hpm_cli.py`. This tool ensures that no package can be modified after release.

### 1. Generating Keys (Ed25519)
To sign packages, you need a key pair.
```bash
python scripts/hpm_cli.py keygen --out-dir keys
```
- **`private.pem`**: Keep this secret. Used for signing.
- **`public.pem`**: Share this. Copy this key into `hecos/data/trusted_keys/` so Hecos can trust packages signed by you.

### 2. Packing & Signing
Prepare your module directory (e.g. `my_module/`) ensuring it contains the `hpkg_manifest.toml` file.
```bash
python scripts/hpm_cli.py pack --src my_module/ --key keys/private.pem --out my_module_v1.hpkg
```
The script will compute the hash (SHA-256) of every file inside the directory, sign the manifest using the private key, and create an `.hpkg` archive ready for distribution.

> **Note**: During local development, you can bypass signature verification by checking "Allow unsigned packages" in the Package Manager WebUI.
