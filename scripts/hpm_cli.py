#!/usr/bin/env python3
"""
hpm_cli.py
─────────────────────────────────────────────────────────────────────────────
Hecos Package Manager — Developer CLI Tool

Usage:
  1. Generate keys:
     python hpm_cli.py keygen --out-dir keys

  2. Pack and sign a plugin directory:
     python hpm_cli.py pack --src my_plugin/ --key keys/private.pem --out my_plugin_v1.hpkg
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import json
import base64
import hashlib
import zipfile
import argparse

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("Error: The 'cryptography' library is not installed.")
    print("Please install it using: pip install cryptography")
    sys.exit(1)


def generate_keys(out_dir: str):
    """Generate Ed25519 private and public keys."""
    os.makedirs(out_dir, exist_ok=True)
    private_key_path = os.path.join(out_dir, "private.pem")
    public_key_path = os.path.join(out_dir, "public.pem")

    if os.path.exists(private_key_path):
        print(f"Error: {private_key_path} already exists. Refusing to overwrite.")
        sys.exit(1)

    print("Generating Ed25519 key pair...")
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open(private_key_path, "wb") as f:
        f.write(private_bytes)

    with open(public_key_path, "wb") as f:
        f.write(public_bytes)

    # In Hecos, trusted keys must be named .pem (already the case)
    print(f"Keys generated successfully in '{out_dir}'")
    print(f"Private Key: {private_key_path} (KEEP THIS SECRET)")
    print(f"Public Key : {public_key_path} (Copy this to hecos/data/trusted_keys/ to trust this developer)")


def pack_and_sign(src_dir: str, private_key_path: str, out_file: str):
    """Pack a directory into a .hpkg file and sign it."""
    is_toml = False
    manifest_path = os.path.join(src_dir, "hpkg_manifest.toml")
    if os.path.isfile(manifest_path):
        is_toml = True
    else:
        manifest_path = os.path.join(src_dir, "hpkg_manifest.json")
        if not os.path.isfile(manifest_path):
            print(f"Error: {manifest_path} not found (neither .toml nor .json).")
            print("A package must contain an 'hpkg_manifest.toml' or '.json' file at the root.")
            sys.exit(1)

    if not os.path.isfile(private_key_path):
        print(f"Error: Private key '{private_key_path}' not found.")
        sys.exit(1)

    # 1. Load Private Key
    try:
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            print("Error: The provided key is not an Ed25519 private key.")
            sys.exit(1)
    except Exception as e:
        print(f"Error loading private key: {e}")
        sys.exit(1)

    # 2. Hash all files in the directory (except manifest)
    print(f"Scanning directory: {src_dir}")
    file_hashes = {}
    for root, _, files in os.walk(src_dir):
        for fname in files:
            if fname in ["hpkg_manifest.json", "hpkg_manifest.toml"]:
                continue

            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, src_dir).replace("\\", "/")
            
            sha256 = hashlib.sha256()
            with open(fpath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            
            file_hashes[rel_path] = sha256.hexdigest()

    # 3. Load Manifest and update hashes
    try:
        if is_toml:
            import tomllib
            with open(manifest_path, "rb") as f:
                manifest = tomllib.load(f)
        else:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
    except Exception as e:
        print(f"Error reading manifest: {e}")
        sys.exit(1)

    manifest["file_hashes"] = file_hashes

    # 4. Canonicalize manifest and sign it
    # Strip existing signature if any
    manifest.pop("signature", None)
    
    # Dump to canonical JSON string
    payload_bytes = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode("utf-8")
    
    print("Signing package manifest...")
    signature_bytes = private_key.sign(payload_bytes)
    manifest["signature"] = base64.b64encode(signature_bytes).decode("utf-8")

    # 5. Create the ZIP archive
    print(f"Creating archive: {out_file}")
    with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write the updated manifest directly from memory
        manifest_name = "hpkg_manifest.toml" if is_toml else "hpkg_manifest.json"
        
        if is_toml:
            import tomli_w
            manifest_data = tomli_w.dumps(manifest).encode("utf-8")
        else:
            manifest_data = json.dumps(manifest, indent=2).encode("utf-8")
            
        zf.writestr(manifest_name, manifest_data)
        
        # Write all other files
        for root, _, files in os.walk(src_dir):
            for fname in files:
                if fname in ["hpkg_manifest.json", "hpkg_manifest.toml"]:
                    continue
                fpath = os.path.join(root, fname)
                arcname = os.path.relpath(fpath, src_dir).replace("\\", "/")
                zf.write(fpath, arcname)

    print("Package built and signed successfully!")
    print(f"Package: {out_file}")
    print(f"Files hashed: {len(file_hashes)}")


def main():
    parser = argparse.ArgumentParser(description="Hecos Package Manager (HPM) Developer CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # keygen
    parser_keygen = subparsers.add_parser("keygen", help="Generate an Ed25519 key pair")
    parser_keygen.add_argument("--out-dir", required=True, help="Directory to save the keys")

    # pack
    parser_pack = subparsers.add_parser("pack", help="Pack and sign a directory into a .hpkg file")
    parser_pack.add_argument("--src", required=True, help="Source directory containing the plugin")
    parser_pack.add_argument("--key", required=False, help="Path to the private.pem key (defaults to config)")
    parser_pack.add_argument("--out", required=True, help="Output .hpkg file path")

    args = parser.parse_args()

    if args.command == "keygen":
        generate_keys(args.out_dir)
    elif args.command == "pack":
        if not args.key:
            try:
                # Fallback to system config
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from hecos.app.config import ConfigManager
                cfg_mgr = ConfigManager()
                hpm_cfg = cfg_mgr.config.get("hpm", {})
                args.key = hpm_cfg.get("private_key_path")
                if not args.key:
                    print("Error: --key not provided and 'private_key_path' not configured in Hecos.")
                    sys.exit(1)
            except ImportError:
                print("Error: Hecos ConfigManager not found. Provide --key.")
                sys.exit(1)
            except Exception as e:
                print(f"Error loading Hecos config: {e}")
                sys.exit(1)
                
        pack_and_sign(args.src, args.key, args.out)


if __name__ == "__main__":
    main()
