# ⌨️ 12. Comandos Directos (HDCS)

Imagine tener una **varita mágica** que le permita dar órdenes precisas a Hecos sin tener que mantener una larga conversación con la Inteligencia Artificial. Esta varita mágica se llama **HDCS (Hecos Direct Command System)**, o simplemente: **Comandos Directos**.

Normalmente, cuando escribe a Hecos, la IA tiene que leer su mensaje, pensar en lo que quiere hacer, elegir la herramienta adecuada y luego ejecutarla. Sin embargo, a veces sabe *exactamente* lo que quiere hacer y quiere que suceda **inmediatamente**, ¡en un abrir y cerrar de ojos!

Para eso sirven los comandos directos. Todos comienzan con una barra diagonal **`/`** (slash) y le dicen al sistema que ejecute una acción de inmediato, evitando por completo el "cerebro" de la IA.

![Hecos - Direct Comands](https://github.com/Hecos-Project/Hecos-Assets/blob/main///004_HecosChat_Direct_Commands.png?raw=true)


---

## 🎩 Cómo usarlos en el Chat

¡Usar comandos directos en el chat es tan fácil como usar emojis en WhatsApp!

1. Haga clic en la barra de chat donde suele escribir sus mensajes.
2. Escriba el carácter **`/`** (barra diagonal).
3. **¡Magia!** Aparecerá un menú desplegable justo encima del cuadro de texto.
4. Este menú contiene *todos* los comandos disponibles en el sistema, tanto los alias amigables para el usuario como las herramientas de plugin autogeneradas.
5. Puede desplazarse por la lista con el mouse o las teclas de flecha del teclado, o puede seguir escribiendo para filtrar la lista. Por ejemplo, si escribe `/weather`, verá aparecer el comando del clima.
6. Presione **Tab** o haga clic en el comando con el mouse para elegirlo.
7. Si el comando necesita información adicional (como la ciudad para el clima), dejará un espacio para usted. Escriba, por ejemplo, `/weather London` y presione **Enter**. ¡Listo!

---

## 🔍 El "Spotlight": Comandos siempre al alcance de su mano

¿Qué pasa si no está en el chat? Quizás esté mirando la página de plugins o leyendo otra pantalla. ¡No se preocupe! Puede usar comandos directos *donde sea* que esté gracias al **Spotlight**.

El Spotlight es una barra de búsqueda flotante especial. Para invocarla:
1. Presione la combinación secreta en su teclado: **`Ctrl + Alt + Espacio`** (presione Control, Alt y la barra espaciadora a la vez).
2. La pantalla se oscurecerá ligeramente y aparecerá una hermosa barra de búsqueda en el centro.
3. Escriba lo que está buscando (por ejemplo, `img` o `weather` o `calendar`).
4. Seleccione el comando con las teclas de flecha y presione **Enter**. 
5. ¡Hecos ejecutará la acción instantáneamente en segundo plano y le mostrará un pequeño mensaje de confirmación!

---

## 🎤 Comandos de Voz (Dictado)

¡Puede lanzar comandos directos simplemente **hablando**! Si utiliza la función de dictado por voz, el sistema es capaz de comprender cuándo desea ejecutar un comando en lugar de enviar un mensaje de texto normal.

Para activarlo, simplemente comience su frase (como la primera palabra) con uno de los siguientes "disparadores" de voz:
* **"Comando"** (por ejemplo, *"Comando weather London"*)
* **"Command"** (por ejemplo, *"Command clear"*)
* **"Slash"** (por ejemplo, *"Slash help"*)

El sistema interceptará automáticamente la palabra clave, la transformará en el símbolo `/` y enviará la instrucción directamente al motor de comandos. Es extremadamente útil si no tiene las manos libres para escribir.

---

## 🧩 Uso de Comandos Directos en "Flows"

Flows es el lugar donde crea rutinas automáticas vinculando muchos nodos entre sí como si fueran ladrillos de Lego. 
A veces, es posible que desee utilizar un comando directo dentro de un Flow, para garantizar que una acción se ejecute con precisión sin preguntar a la IA.

Para hacer esto, solo necesita usar un nodo especial:
1. En el menú de la izquierda de Flows, abra la categoría **SYSTEM** o **EXECUTOR**.
2. Busque el ladrillo llamado **`execute_slash_command`** y arrástrelo a su pantalla.
3. Este nodo tiene un campo de texto llamado `command`. ¡Ahí es donde debe escribir el comando que desea ejecutar!
4. **El truco del mago:** Si hace clic en el cuadro de texto del nodo y escribe `/`, el menú desplegable de autocompletar se abrirá como en el chat. Seleccione el comando y se escribirá por usted.
5. Alternativamente, siempre puede presionar `Ctrl + Alt + Espacio` para buscar el comando. Si está dentro del cuadro de texto del nodo, presionar Enter no ejecutará el comando de inmediato, sino que lo **pegará** mágicamente en el nodo, ¡listo para ser guardado!

---

## 📖 Catálogo Completo de Comandos Directos

Aquí está la lista completa de todos los comandos directos integrados en Hecos, categorizados. Cada comando incluye su descripción, alias alternativos y 3 ejemplos prácticos de uso.

### 1. Comandos del Sistema (Categoría CORE)

Estos son los comandos fundamentales para administrar la aplicación Hecos, la sesión de chat y las configuraciones del sistema.

| Comando Base | Alias Alternativos | Descripción |
| :--- | :--- | :--- |
| `/help` | `/?`, `/comandi` | Muestra la lista de todos los comandos slash disponibles y las capacidades activas en el sistema. |
| `/status` | `/info` | Muestra el estado del sistema (modelo de IA activo, plugins cargados, uso de RAM y versión de Hecos). |
| `/clear` | `/pulisci`, `/reset` | Borra todo el historial de conversación del chat actual para liberar memoria. |
| `/config get` | | Lee un valor de configuración interna utilizando la notación de puntos (por ejemplo, `categoria.clave`). |
| `/config set` | | Establece temporalmente un valor de configuración en la memoria RAM. |
| `/reload` | `/reload_commands` | Fuerza la recarga del registro de comandos (útil después de instalar nuevos plugins). |

#### Ejemplos Prácticos:
* **`/help`**
  1. `/help` (muestra la lista principal de comandos)
  2. `/?` (muestra la ayuda de referencia rápida)
  3. `/comandi` (muestra la lista de comandos en italiano)
* **`/status`**
  1. `/status` (visualiza el modelo activo y los recursos)
  2. `/info` (muestra la versión de Hecos en ejecución)
  3. `/status` (útil para verificar si el backend de Ollama/Kobold está en línea)
* **`/clear`**
  1. `/clear` (vacía la pantalla de chat actual)
  2. `/pulisci` (borra el contexto de la conversación)
  3. `/reset` (inicia una conversación desde cero)
* **`/config get`**
  1. `/config get ai.model` (muestra el modelo de IA configurado)
  2. `/config get reminder.reminder_mode` (muestra el modo de alerta de recordatorio actual)
  3. `/config get system.theme` (muestra el tema de la interfaz)
* **`/config set`**
  1. `/config set ai.model gemini/gemini-2.0-flash` (establece temporalmente el modelo en Gemini 2.0 Flash)
  2. `/config set reminder.max_reminders 30` (limita los recordatorios activos a 30)
  3. `/config set system.theme dark` (cambia el tema de la interfaz a oscuro)
* **`/reload`**
  1. `/reload` (recarga todos los comandos registrados)
  2. `/reload_commands` (actualiza la lista de autocompletado)
  3. `/reload` (ejecutar si un plugin recién cargado no aparece en el autocompletado)

---

### 2. Comandos de Flujos (Categoría FLOWS)

Estos comandos le permiten enumerar, ejecutar y verificar el estado de los flujos de automatización creados en la sección **Flows**.

| Comando Base | Alias Alternativos | Descripción |
| :--- | :--- | :--- |
| `/flow list` | `/flows`, `/flow ls` | Enumera todos los flujos disponibles guardados en el espacio de trabajo (`workspace/flows/`). |
| `/flow run` | `/flow exec` | Ejecuta un flujo específico inmediatamente por su nombre. |
| `/flow trigger` | `/trigger` | Activa manualmente un flujo específico (funciona idénticamente a run). |
| `/flow status` | `/flow log` | Muestra el último registro de ejecución (el resultado de la última ejecución) de un flujo. |

#### Ejemplos Prácticos:
* **`/flow list`**
  1. `/flow list` (enumera flujos con su tipo de disparador y estado activo/inactivo)
  2. `/flows` (enumera todos los archivos YAML de flujo rápidamente)
  3. `/flow ls` (muestra una lista compacta de flujos)
* **`/flow run`**
  1. `/flow run morning_routine` (ejecuta la rutina matutina programada inmediatamente)
  2. `/flow run check_weather_alert` (ejecuta el flujo de comprobación del clima)
  3. `/flow exec turn_off_everything` (ejecuta el flujo de apagado del sistema)
* **`/flow status`**
  1. `/flow status morning_routine` (muestra si la rutina matutina tuvo éxito o falló)
  2. `/flow log check_weather_alert` (imprime los registros de ejecución y errores para la comprobación del clima)
  3. `/flow status data_backup` (lee el registro del flujo de respaldo)

---

### 3. Comandos de Plugins (Categoría PLUGINS)

Estos comandos son expuestos por los diversos módulos opcionales habilitados en Hecos.

| Comando Base | Alias Alternativos | Descripción |
| :--- | :--- | :--- |
| `/soul` | `/persona`, `/personality` | Cambia el alma/personalidad activa de la IA (por ejemplo, profesional, juguetona, etc.). |
| `/souls` | `/personas` | Enumera todas las almas/personalidades instaladas en el sistema. |
| `/calendar` | `/calendario`, `/appuntamenti` | Enumera los próximos eventos del Calendario Hecos. |
| `/img` | `/image`, `/photo`, `/foto` | Genera una imagen de IA a partir de una descripción de texto. |
| `/list` | `/lists`, `/liste` | Enumera todas las listas activas (Compras, Tareas, etc.). |
| `/lista` | | Muestra todos los elementos dentro de una lista específica. |
| `/list add` | `/lista aggiungi` | Agrega un elemento a una lista (crea la lista si no existe). |
| `/list done` | `/lista spunta` | Marca un elemento como completado en una lista. |
| `/reminder` | `/ricorda`, `/promemoria` | Programa un nuevo recordatorio utilizando expresiones de tiempo en lenguaje natural. |
| `/reminders` | `/promemoria list` | Enumera todos los recordatorios activos junto con sus IDs únicos. |
| `/weather` | `/meteo`, `/tempo` | Muestra las condiciones climáticas actuales o los pronósticos para una ciudad. |

#### Ejemplos Prácticos:
* **`/soul`**
  1. `/soul Motoko` (cambia la personalidad activa a "Motoko")
  2. `/persona 2` (cambia a la segunda personalidad en la lista)
  3. `/personality Jarvis` (cambia la personalidad al estilo "Jarvis")
* **`/calendar`**
  1. `/calendar` (muestra la agenda para los próximos días)
  2. `/calendario` (muestra los próximos eventos)
  3. `/appuntamenti` (enumera las citas de hoy)
* **`/img`**
  1. `/img a little space kitten wearing an astronaut helmet` (genera la imagen)
  2. `/photo cyberpunk portrait of a girl, neon lights, 8k` (genera un render de estilo fotográfico)
  3. `/foto oil painting of a sunset over the sea` (genera un render de estilo artístico)
* **`/list` / `/lista` / `/list add` / `/list done`**
  1. `/list add Shopping Eggs` (agrega "Eggs" a la lista "Shopping")
  2. `/lista Shopping` (muestra los elementos dentro de la lista "Shopping")
  3. `/list done Shopping Eggs` (marca "Eggs" como completado/comprado)
* **`/reminder` / `/reminders`**
  *(Consulte la sección dedicada a continuación para obtener detalles de uso detallados)*
  1. `/reminder buy milk at 18:30` (establece un recordatorio para las 18:30 de hoy)
  2. `/reminders` (enumera los recordatorios activos y sus IDs cortos)
  3. `/ricorda call mom in 15 minutes` (establece un recordatorio relativo)
* **`/weather`**
  1. `/weather London` (muestra el clima para Londres)
  2. `/meteo Milan` (muestra el clima para Milán en italiano)
  3. `/weather` (muestra el clima para la ciudad de origen configurada por defecto)

---

## ⏰ Deep Dive: Uso de Recordatorios (`/reminder` vs `/reminder.set_reminder`)

El plugin de recordatorios ofrece dos formas de invocación a través de comandos directos. Comprender la diferencia es clave para evitar errores de sintaxis.

### 1. El Comando Amigable: `/reminder`

Este comando está diseñado para la interacción humana. Utiliza un analizador inteligente de lenguaje natural que analiza la cadena de entrada, extrae la hora/fecha y el texto del recordatorio, y lo registra.

* **Sintaxis:** `/reminder <qué recordar> at/in/on <hora/fecha>`
* **Cómo funciona:** El sistema lee todo lo que sigue al comando, busca preposiciones como "at", "in", "on", "alle", "tra", "il" y calcula la fecha de activación correcta automáticamente.

#### Ejemplos Correctos:
1. **`/reminder pick up dry cleaning at 17:45`** (establece un recordatorio para las 17:45 de hoy)
2. **`/ricorda turn off the oven in 20 minutes`** (establece un recordatorio relativo que expira en exactamente 20 minutos)
3. **`/promemoria call doctor on 25/08 at 09:00`** (establece un recordatorio para una fecha y hora futuras específicas)
4. **`/reminder take the cake out of the oven in 30 minutes --interactive`** (añada `--interactive` o `-i` para forzar un recordatorio interactivo que repite la alarma hasta que se detenga o posponga explícitamente)

> [!TIP]
> Si desea verificar los recordatorios activos o cancelar uno de ellos, escriba `/reminders`. Mostrará todos los recordatorios activos con sus IDs de 8 caracteres. Puede cancelar un recordatorio utilizando el comando autogenerado `/reminder.cancel_reminder <ID>` (por ejemplo, `/reminder.cancel_reminder a1b2c3d4`).

---

### 2. El Comando Técnico/Autogenerado: `/reminder.set_reminder`

Este comando pertenece a la categoría de comandos autogenerados (ver más abajo) y se asigna directamente a la firma interna de la función Python.

* **Por qué falla en el Chat:** La función Python espera parámetros separados: `title` y `when`. Si escribe `/reminder.set_reminder buy milk at 18:30`, el ejecutor del comando asigna toda la cadena `"buy milk at 18:30"` al primer parámetro (`title`), dejando vacío el segundo parámetro requerido (`when`). Esto da como resultado un error de sintaxis:
  `❌ Argumentos incorrectos para /reminder.set_reminder` (falta el argumento requerido 'when').
* **Cuándo usarlo:** Es extremadamente útil en **Flows**, donde los parámetros se asignan explícitamente en campos separados, o para llamar a herramientas que solo aceptan un argumento.

---

## ⚙️ Comandos Avanzados Autogenerados (`/<tag>.<method>`)

Hecos presenta una capacidad especial: **genera automáticamente un comando directo para cada método de herramienta expuesto por cualquier plugin o módulo**, en el formato:
`/<plugin_tag>.<method_name>`

Estos comandos están destinados a desarrolladores y flujos de automatización, pero están disponibles para usar en el chat o en Spotlight.

### ¿Cómo funcionan?
Cuando escribe un comando como `/<tag>.<method> <argumentos>`, Hecos toma el texto que sigue al comando y lo pasa como el **primer argumento posicional** al método Python subyacente. Si el método requiere solo un parámetro, funcionará de inmediato.

#### Comandos Autogenerados Populares:
* **`/executor.reboot_system`** (reinicia Hecos)
  * Ejemplo 1: `/executor.reboot_system` (reinicia inmediatamente, no se requieren argumentos)
  * Ejemplo 2: `/executor.reboot_system`
  * Ejemplo 3: `/executor.reboot_system`
* **`/executor.kill_process`** (mata un proceso de Windows por su nombre)
  * Ejemplo 1: `/executor.kill_process chrome.exe` (termina Google Chrome)
  * Ejemplo 2: `/executor.kill_process notepad` (cierra el Bloc de notas)
  * Ejemplo 3: `/executor.kill_process vlc` (cierra el reproductor VLC)
* **`/browser.open_url`** (abre una página en el navegador controlado por IA)
  * Ejemplo 1: `/browser.open_url https://www.google.com` (abre Google)
  * Ejemplo 2: `/browser.open_url https://wikipedia.org` (abre Wikipedia)
  * Ejemplo 3: `/browser.open_url localhost:7070` (abre la WebUI local de Hecos)
