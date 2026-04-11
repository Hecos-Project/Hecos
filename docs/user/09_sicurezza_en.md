# 🛡️ 9. Advanced Security (Zentra PKI)

Version 0.15.2 introduces a built-in **PKI (Public Key Infrastructure)** for secure HTTPS connections across your local network.

### Certificates & Root CA
To unlock features like **Microphone** and **Webcam** on mobile browsers (which require secure contexts), Zentra acts as its own Certificate Authority:
1. **Root CA**: Automatically generated at first startup in `certs/ca/`.
2. **Installation**: Download and install the `Root CA` certificate on your remote device (Mobile or PC) and set it to "Trusted".
3. **Download**: Available via the **Security** tab in the Config Panel.
