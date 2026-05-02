# 🔑 13. Gestor de Llaves y Failover

El Key Manager es el módulo central para la gestión de licencias y llaves API en Hecos.

- **Gestión de Llaves**: Puedes añadir, eliminar o modificar tus llaves API (OpenAI, Gemini, Anthropic) directamente desde el Panel de Configuración.
- **Seguridad**: Las llaves se almacenan de forma segura y nunca se exponen en los registros del sistema.
- **Failover Automático**: Si un proveedor de servicios no responde, Hecos puede intentar automáticamente usar un modelo o proveedor alternativo para completar tu solicitud.
- **Monitoreo de Tokens**: Visualiza el consumo de tokens en tiempo real para cada sesión de chat.
