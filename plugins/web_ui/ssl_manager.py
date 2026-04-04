"""
MODULE: SSL Certificate Manager
DESCRIPTION: Generates or loads a self-signed TLS certificate for the WebUI HTTPS server.
             Uses cryptography library (preferred) with fallback to OpenSSL CLI.
"""

import os
import datetime

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def get_cert_paths(cert_file: str = "certs/cert.pem", key_file: str = "certs/key.pem"):
    """Returns absolute paths for cert and key files."""
    if not os.path.isabs(cert_file):
        cert_file = os.path.join(_PROJECT_ROOT, cert_file)
    if not os.path.isabs(key_file):
        key_file = os.path.join(_PROJECT_ROOT, key_file)
    return cert_file, key_file


def certs_exist(cert_file: str, key_file: str) -> bool:
    """Check if both certificate files already exist."""
    return os.path.exists(cert_file) and os.path.exists(key_file)


def generate_self_signed_cert(cert_file: str, key_file: str, hostname: str = "localhost") -> bool:
    """
    Generate a self-signed TLS certificate valid for 10 years.
    Uses the `cryptography` library (pip install cryptography).

    Args:
        cert_file: Destination path for the certificate (.pem).
        key_file: Destination path for the private key (.pem).
        hostname: Hostname for the Subject/SAN.

    Returns:
        True on success, False on failure.
    """
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import ipaddress

        # Ensure directory exists
        os.makedirs(os.path.dirname(cert_file), exist_ok=True)

        # Generate RSA private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IT"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Zentra-Core"),
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ])

        # Build the certificate
        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))  # 10 years
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(hostname),
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        # Write private key
        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        # Write certificate
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"[SSL] Self-signed certificate generated: {cert_file}")
        return True

    except ImportError:
        print("[SSL] WARNING: 'cryptography' library not found. Run: pip install cryptography")
        return False
    except Exception as e:
        print(f"[SSL] Certificate generation failed: {e}")
        return False


def ensure_certificates(cert_file: str = "certs/cert.pem",
                        key_file: str = "certs/key.pem",
                        hostname: str = "localhost") -> tuple[str, str] | None:
    """
    Ensure TLS certificates exist, generating them if necessary.

    Returns:
        Tuple (cert_path, key_path) if ready, or None if generation failed.
    """
    cert_file, key_file = get_cert_paths(cert_file, key_file)

    if certs_exist(cert_file, key_file):
        print(f"[SSL] Using existing certificate: {cert_file}")
        return cert_file, key_file

    print("[SSL] No certificate found. Generating self-signed certificate...")
    success = generate_self_signed_cert(cert_file, key_file, hostname)
    if success:
        return cert_file, key_file
    return None
