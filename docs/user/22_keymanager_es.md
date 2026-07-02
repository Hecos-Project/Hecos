# 🔑 23. Gestor de Llaves y Failover

El Key Manager es el módulo central para la gestión de licencias y llaves API en Hecos.

- **Gestión de Llaves**: Puedes añadir, eliminar o modificar tus llaves API (OpenAI, Gemini, Anthropic) directamente desde el Panel de Configuración.
- **Seguridad**: Las llaves se almacenan de forma segura y nunca se exponen en los registros del sistema.
- **Failover Automático**: Si un proveedor de servicios no responde, Hecos puede intentar automáticamente usar un modelo o proveedor alternativo para completar tu solicitud.
- **Monitoreo de Tokens**: Visualiza el consumo de tokens en tiempo real para cada sesión de chat.

### ⚙️ Configuración Avanzada y Comportamiento de Failover

El Key Manager cuenta con una sección de **Configuración Avanzada** para permitirte optimizar cómo Hecos maneja las solicitudes API y el cambio de una clave a otra (Failover).

Aquí hay una explicación detallada de los parámetros:

1. **⏱️ Timeout solicitud cloud (segundos)**
   * **Qué hace**: Establece el tiempo máximo que Hecos esperará por una respuesta del proveedor cloud antes de rendirse con la clave actual.
   * **Por qué modificarlo**: Si la API está sobrecargada y no responde, un timeout demasiado alto bloquea Hecos en un estado "pensando" por mucho tiempo. Un valor más bajo (ej: 20-30s) permite a Hecos detectar rápidamente el problema y cambiar a una clave de respaldo.
   * **Recomendado**: 30 segundos.

2. **🔄 Cooldown de clave en error (segundos)**
   * **Qué hace**: Cuando una clave recibe un error de límite de tasa (HTTP 429) o un timeout, Hecos la pone "en pausa" (cooldown) por el tiempo especificado, evitando desperdiciar intentos.
   * **Por qué modificarlo**: Si usas APIs gratuitas que se bloquean por un minuto después de 10 mensajes, 60s es ideal. Si tienes pocas claves, podrías querer reducir este tiempo para volver a intentar antes con las mismas claves.
   * **Recomendado**: 60 segundos.

3. **🔁 Reintentos máximos de failover**
   * **Qué hace**: Determina el número máximo de *claves diferentes* que Hecos intentará contactar en secuencia para un solo mensaje del usuario antes de devolver un mensaje de error.
   * **Por qué modificarlo**: Para evitar bucles infinitos o solicitudes demasiado largas. Establécelo en un número igual a la cantidad de claves de respaldo que tienes para ese proveedor.
   * **Recomendado**: 5.

#### 💡 Cómo funciona el failover:
1. Hecos intenta la **clave #1** con el timeout configurado.
2. Si la API responde con un error (429 rate limit o 401 unauthorized) o se activa el **timeout**, Hecos marca esa clave como en "cooldown".
3. Hecos cambia automáticamente a la **clave #2** y vuelve a intentar.
4. Esto se repite hasta que una clave funciona, o hasta que se alcanza el límite de "Reintentos máximos de failover".
5. Las claves en cooldown vuelven a estar activas automáticamente una vez que ha transcurrido el tiempo configurado.
