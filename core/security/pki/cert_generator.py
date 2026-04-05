import os
import datetime
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

class CertGenerator:
    """Genera certificati Host firmati dalla Zentra Root CA"""

    def __init__(self, ca_manager, certs_dir="certs"):
        self.ca = ca_manager
        self.certs_dir = certs_dir
        
        self.cert_path = os.path.join(self.certs_dir, "cert.pem")
        self.key_path = os.path.join(self.certs_dir, "key.pem")

        if not os.path.exists(self.certs_dir):
            os.makedirs(self.certs_dir)

    def generate_host_cert(self, local_ip="127.0.0.1"):
        """Generates and signs the final host certificate for the given IP"""
        print(f"[PKI] Generating secure host certificate for: {local_ip}")
        
        ca_key, ca_cert = self.ca.init_ca()

        # 1. Genera PrivKey Host
        host_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # 2. Struttura del Subject
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"IT"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Zentra Core"),
            x509.NameAttribute(NameOID.COMMON_NAME, str(local_ip)),
        ])

        # 3. Subject Alternative Names (SAN) per i browser moderni (Chrome/Safari)
        san_list = [x509.DNSName(u"localhost"), x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))]
        try:
            if local_ip not in ["127.0.0.1", "localhost"]:
                san_list.append(x509.IPAddress(ipaddress.IPv4Address(local_ip)))
        except Exception:
            # Se non è un formato IP valido lo aggiungiamo come DNS
            san_list.append(x509.DNSName(str(local_ip)))

        # iOS accetta max 398 giorni di validità (mettiamo 365 per sicurezza)
        cert_builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            host_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False
            ), critical=True
        ).add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=True
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(host_key.public_key()),
            critical=False
        )

        # Aggiungiamo l'AuthorityKeyIdentifier che punta alla Root CA
        cert = cert_builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False
        ).sign(ca_key, hashes.SHA256()) # Firmato dalla CA!

        # 4. Salva su disco
        with open(self.key_path, "wb") as f:
            f.write(host_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(self.cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print("[PKI] Host certificate generated and signed with Zentra Root CA.")
        return self.cert_path, self.key_path
