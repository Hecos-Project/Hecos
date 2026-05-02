# 🛡️ 9. Seguridad Avanzada (Hecos PKI)

Hecos pone la seguridad en el centro, especialmente cuando se accede a la interfaz desde otros dispositivos.

- **Hecos CA**: El sistema actúa como su propia Autoridad de Certificación (Root CA), generando certificados HTTPS seguros y únicos para tu máquina.
- **Conexión Protegida**: Esto habilita el "candado verde" en el navegador, permitiendo el uso de funciones protegidas como el micrófono (WebRTC) en toda tu red local (LAN).
- **Autenticación Obligatoria**: El acceso a la WebUI siempre requiere un inicio de sesión. Puedes gestionar usuarios y contraseñas desde el panel de control.
- **Sandbox**: El código generado por la IA se ejecuta en un entorno protegido (AST Sandbox) para evitar operaciones dañinas en tu sistema operativo.
