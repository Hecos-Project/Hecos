# 💬 Chat y UI

> *"La interfaz conversacional principal donde hablas con Hecos, envías imágenes y activas comandos. Un nexo cibernético que conecta tu núcleo local con la nube."*
> — Tour WebUI Hecos

El **Chat** es la interfaz principal de la WebUI de Hecos. Proporciona un entorno rico y moderno para interactuar con tu IA.

![Hecos Chat Interface](https://github.com/Hecos-Project/Hecos-Assets/blob/main/Hecos_ImageGen_Module_1.png?raw=true)

---

### 🎛️ VISTA GENERAL DEL SISTEMA

---

## Características Clave
- **Texto Enriquecido y Código:** Admite renderizado completo de Markdown, tablas y bloques de código con resaltado de sintaxis.
- **Entrada Multimodal:** Arrastra y suelta imágenes directamente en el chat para que Hecos las analice utilizando sus capacidades de Visión.
- **Integración de Voz:** Haz clic en el icono del micrófono o usa `Ctrl+Shift+Z` para dictar mensajes utilizando la función Push-to-Talk.
- **Historial de Sesiones:** La barra lateral izquierda te permite administrar múltiples conversaciones, renombrarlas o eliminarlas. Todas las sesiones se guardan en tu Bóveda de Memoria Episódica local.
- **Modos de Privacidad:** Elige entre Normal (guardado), Auto-Wipe (solo en RAM) o Incógnito (sin dejar rastro) para cada conversación.
- **Comandos Directos:** Escribe `/` en la barra de entrada para acceder al HDCS (Hecos Direct Command System) para acciones instantáneas sin rodeos conversacionales.

---

## 🛠️ Análisis Profundo: La Interfaz Cibernética

### 1. Barra Lateral Izquierda: Configuración Neural
La barra lateral actúa como el panel de control y telemetría para la sesión activa. Moviéndose de arriba a abajo:

* **Estado del Sistema:** Diagnósticos en tiempo real que muestran el tipo de arquitectura (backend **Cloud** o **Local**), el **Nombre del Modelo** activo y la matriz de personalidad cargada, conocida como el **Alma** (Soul, por ejemplo, `Motoko Kusanagi`).
* **Capa de Privacidad:** Estados de conversación reforzados cibernéticamente:
    * `Normal`: Operaciones estándar, registros persistentes.
    * `Auto-Wipe`: Sesión en memoria volátil; los datos se borran automáticamente de la RAM al reiniciar el sistema.
    * `Incognito`: Enrutamiento oscuro. Cero huellas, cero registros, cero rastros dejados atrás.
* **Cuadrícula de Audio:** Panel de telemetría de voz de alta fidelidad con tres estados de alternancia:
    * `Continuous Audio`: Escucha persistente en segundo plano.
    * `Voice Activation`: Activa el procesamiento al detectar actividad de voz (VAD).
    * `PTT (Push-to-Talk)`: Entrada de modo dual. Haz clic en el icono de chat para cambiar entre Encendido/Apagado estándar o PTT. Alternativamente, usa la combinación de teclas rápidas **`Ctrl+Shift`** para activar un modo de walkie-talkie a nivel de hardware.
* **Control Room:** Un nodo plegable y deslizable integrado directamente dentro de la vista de chat para administrar widgets activos, pipelines de widgets y estados ambientales.
* **Enlace del Administrador de Paquetes:** Ubicado en la parte inferior absoluta de la barra lateral, este acceso directo del terminal omite el Central Hub, llevándote directamente a la matriz de instalación/actualización de módulos.

![Hecos Chat Interface](https://github.com/Hecos-Project/Hecos-Assets/blob/main/Hecos_Chat_0020.png?raw=true)

### 2. Motor de Chat Principal y Terminal Superior
La vista de procesamiento central maneja el renderizado de datos y el monitoreo ambiental.

* **Indicadores del Panel Superior:** Relés de acceso rápido que rastrean el estado del flujo de audio junto con los nodos de macro-navigación: **Central Hub**, **Drive** (el administrador de archivos local de Hecos) y el **Panel de Flows** para el enrutamiento de automatización visual.
* **Indicador en Línea:** Un faro de estado central que pulsa visualmente para confirmar si el núcleo local o el proxy en la nube está transmitiendo activamente las respuestas.
* **Barra de Entrada Dinámica y HDCS (Sistema de Comandos Directos de Hecos):** Inicializar la entrada de texto con el carácter **`/`** despliega instantáneamente la ventana superpuesta de Comandos Directos. 
    
    Los comandos también se pueden vincular a través de síntesis de voz. Decir **"slash"**, **"command"** o **"comando"** seguido del identificador de la directiva activa el script de inmediato. 
    
    > *Ejemplo de Ejecución:* Pronunciar *"slash souls"* se compila en `/souls`, activando una impresión de diagnóstico completa de todas las almas de compañía instaladas localmente sin obstruir la ventana del contexto del chat.
