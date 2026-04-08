import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

class CAManager:
    """Gestisce la Zentra Local Root CA (Generazione, Caricamento e Salvataggio)"""
    
    def __init__(self, ca_dir="certs/ca"):
        self.ca_dir = ca_dir
        self.ca_key_path = os.path.join(ca_dir, "rootCA-key.pem")
        self.ca_cert_path = os.path.join(ca_dir, "rootCA.pem")
        
        if not os.path.exists(self.ca_dir):
            os.makedirs(self.ca_dir)

    def is_ca_ready(self):
        return os.path.exists(self.ca_key_path) and os.path.exists(self.ca_cert_path)

    def init_ca(self):
        """Inizializza o carica la Root CA"""
        if self.is_ca_ready():
            return self.load_ca()
        return self.generate_ca()

    def generate_ca(self):
        """Generates a new Root CA and saves it to disk"""
        print("[PKI] Generating new Zentra Root CA...")
        
        # 1. Genera Chiave Privata CA
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # 2. Informazioni del Certificato
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"IT"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Zentra State"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Zentra Local Network"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Zentra Core Authority"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"Zentra Local Root CA"),
        ])

        # 3. Costruzione Certificato (Validità 10 anni)
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=3650)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ), critical=True,
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False
        ).sign(private_key, hashes.SHA256())

        # 4. Salva su disco
        with open(self.ca_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(self.ca_cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print("[PKI] Zentra Root CA generated and saved successfully.")
        return private_key, cert

    def load_ca(self):
        """Loads Root CA from disk"""
        with open(self.ca_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
            )

        with open(self.ca_cert_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())

        return private_key, cert
