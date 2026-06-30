# 🛡️ 19. Seguridad Avanzada (Hecos PKI)

Hecos pone la seguridad en el centro, especialmente cuando se accede a la interfaz desde otros dispositivos.

- **Hecos CA**: El sistema actúa como su propia Autoridad de Certificación (Root CA), generando certificados HTTPS seguros y únicos para tu máquina.
- **Conexión Protegida**: Esto habilita el "candado verde" en el navegador, permitiendo el uso de funciones protegidas como el micrófono (WebRTC) en toda tu red local (LAN).
- **Autenticación Obligatoria**: El acceso a la WebUI siempre requiere un inicio de sesión. Puedes gestionar usuarios y contraseñas desde el panel de control.
- **Aislamiento de Datos (User Vaults)**: Los recuerdos, archivos personales y avatares están aislados en carpetas protegidas (`memory/vaults/username`).
- **Privacidad en 3 Niveles (v0.26.0)**: La WebUI proporciona controles granulares sobre la persistencia de datos:
  - `Normal`: Persistencia completa en disco.
  - `Auto-Wipe`: Mensajes solo en RAM, borrados al reiniciar el sistema.
  - `Incógnito`: Rastro cero. Hecos opera exclusivamente en RAM y el contexto se elimina al cambiar de chat, garantizando que no quede ningún rastro de la conversación en el servidor físico.
- **Sandbox**: El código generado por la IA se ejecuta en un entorno protegido (AST Sandbox) para evitar operaciones dañinas en tu sistema operativo.
