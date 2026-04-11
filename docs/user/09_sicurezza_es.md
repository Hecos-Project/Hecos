# 🛡️ 9. Seguridad Avanzada (Zentra PKI)

Zentra introduce una infraestructura **PKI (Public Key Infrastructure)** integrada para conexiones HTTPS seguras en tu red local.

### Certificados y Root CA
Para habilitar funciones como el **Micrófono** y la **Webcam** en navegadores móviles, Zentra actúa como su propia Autoridad de Certificación:
1. **Root CA**: Generada automáticamente al primer inicio en `certs/ca/`.
2. **Instalación**: Descarga e instala el certificado `Root CA` en tu dispositivo remoto y márcalo como "Confiable".
3. **Descarga**: Disponible en la pestaña **Security** del Panel de Configuración.
