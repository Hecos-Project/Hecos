# 💻 11. La Consola (CLI)

> *"La ventana de comandos donde el sistema piensa, realiza comprobaciones de seguridad y te permite gestionarlo todo."*

![Hecos - Helping Companion System](https://github.com/Hecos-Project/Hecos-Assets/blob/main//Hecos_Core_002.png?raw=true)


La **Consola de Hecos** es la ventana de terminal cruda y nativa que se abre al iniciar Hecos por primera vez. Es el corazón palpitante del sistema.

## ¿Por qué una Consola?
Mientras que la WebUI es la "cara" de Hecos, la Consola es el "cerebro". Garantiza una transparencia absoluta. Cada acción que realiza la IA, cada herramienta que invoca y cada llamada a la API que realiza se registra aquí en tiempo real.

## Características Principales
- **Telemetría en Tiempo Real:** Muestra el uso del hardware, el estado de carga del backend y los estados de los módulos activos.
- **Auditoría de Seguridad:** Observa cómo el sistema ejecuta los comandos. Si un flujo o plugin desencadena un proceso local (como abrir un archivo o ejecutar un script de Python), el comando exacto se imprime aquí.
- **Server Hub:** La Consola actúa como el servidor local para la WebUI. Cerrar esta ventana apaga todo el sistema Hecos.
- **Entrada Rápida e Historial (History):** Puedes escribir texto directamente en la consola para chatear con la IA si prefieres una experiencia solo de terminal sin distracciones. Presiona la **Flecha Arriba (↑)** y la **Flecha Abajo (↓)** para navegar por tus entradas anteriores (Historial de Entradas), como en una terminal Bash o Zsh. Este historial está sincronizado con la WebUI y se guarda localmente.
