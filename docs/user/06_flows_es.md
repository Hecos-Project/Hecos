# 🔀 7. Flows: Automatizaciones Visuales

El módulo **Flows** de Hecos es el "orquestador" del sistema. Le permite crear automatizaciones, rutinas y comportamientos complejos encadenando acciones de manera lógica y secuencial.

![Hecos - Flows Automatizaciones](https://github.com/Hecos-Project/Hecos-Assets/blob/main/////010_Hecos_Flows_001.png?raw=true)

Puede crear un flujo utilizando lenguaje natural (la IA lo escribirá por usted), dibujándolo a través del **Canvas Visual** (Node Palette) o escribiéndolo directamente en formato **YAML**.

---

## 1. Cómo Funciona (Conceptos Clave)

Un Flow se compone de una serie de **Nodos** (o *Pasos*). Cada nodo realiza una única operación específica (por ejemplo: esperar 5 segundos, enviar un correo electrónico, leer una cadena de texto).
- **Ejecución Lineal o Paralela**: Los nodos se pueden vincular entre sí. Si el *Nodo B* tiene una dependencia (`depends_on`) del *Nodo A*, el *Nodo B* solo se ejecutará cuando el *Nodo A* finalice con éxito. ¡Dos nodos sin dependencias se iniciarán en paralelo!
- **Compartir Variables**: Un nodo puede guardar su resultado utilizando la opción `output_as`. Por ejemplo, un nodo que verifica el clima puede guardar el resultado como `weather_data` y un nodo posterior puede leer esos datos.
- **Disparadores (Triggers)**: Cada flujo tiene un *disparador*. Puede ser manual (activado por un clic), temporal (por ejemplo, CRON "todos los lunes") o basado en un evento del sistema (por ejemplo, recibir un mensaje).

---

## 2. El Formato YAML y el parámetro `key`

Detrás de escena (o en el editor YAML integrado), cada flujo se describe en formato YAML (un estándar extremadamente legible y extendido). 
A diferencia de `JSON` (que utiliza llaves rígidas y comillas como `{"key": "value"}`), **YAML** utiliza una sangría simple (espacios) y la sintaxis `key: value`.

![Hecos - Flows Automatizaciones](https://github.com/Hecos-Project/Hecos-Assets/blob/main//////011_Hecos_Flows_002.png?raw=true)

### 💡 Resolver el error conceptual sobre "key"
Cuando está en el Editor de Nodos (haga doble clic en un nodo) y lee "Parameters (YAML)", o cuando ve un parámetro llamado `key` en informática, simplemente significa el **nombre identificativo de ese parámetro**.

Por ejemplo, si el sistema espera un parámetro YAML estructurado de esta manera:
```yaml
text: Buenos días, ¿estás listo para comenzar el día?
sound: alarm_1
```
En este ejemplo:
- `text` es la **key** (la clave/nombre del parámetro).
- `Buenos días, ¿estás listo...` es el **value** (el contenido/valor asignado).
Nunca escribe explícitamente la palabra `{key: algo}`, pero debe utilizar los nombres correctos esperados por el nodo (por ejemplo, `text: ...`, `seconds: ...`).

---

## 3. Editor de Nodos: Los parámetros explicados

Al hacer doble clic en un nodo en el Canvas, se abre el **Editor de Nodos**. Aquí se explica para qué sirven los distintos campos:

- **Step ID (Único)**: El identificador único de este nodo específico (por ejemplo, `notificacion_telegram`). No puede contener espacios. Permite que otros nodos hagan referencia a _este nodo específico_ como una dependencia.
- **Action**: El módulo a ejecutar (por ejemplo, `AUDIO__speak`, `LOGIC__delay`, `MAIL__send`). Determina qué hará el nodo.
- **Parameters (YAML)**: Aquí inserta la configuración del nodo utilizando la sintaxis YAML. Es donde le proporciona a la máquina los datos que necesita. Ejemplo para `AUDIO__speak`: 
  ```yaml
  text: Hola Universo, soy Hecos.
  ```

  > [!IMPORTANT]
  > **¡Cada nodo solo acepta sus propios parámetros específicos!**
  > Por ejemplo, escribir `text: Hola` funciona **solo** para nodos que hablan o escriben texto (como `AUDIO__speak` o `SYSTEM__chat_message`). Si lo coloca dentro de un nodo `LOGIC__delay`, se ignorará o arrojará un error, porque el nodo de retraso solo entiende estrictamente la clave `seconds: 10`.
  > Para ayudarle con esto, cada vez que arrastra un nodo al lienzo, **sus parámetros requeridos aparecerán automáticamente precompletados** (con valores de marcador de posición como `<string>` o `0`). ¡Solo necesita sobrescribir el marcador de posición con sus datos reales!

- **Output As (Variable)**: Muchos nodos generan un resultado (por ejemplo, leer la hora, el resultado de un cálculo, una respuesta de API). Si proporciona un nombre aquí (por ejemplo, `valor_clima`), el resultado producido por este nodo se convierte en una **Variable**. Los nodos posteriores pueden usar esta variable en sus Parámetros escribiendo `{{ valor_clima }}` (usando la sintaxis Jinja2).

![Hecos - Flows Automatizaciones](https://github.com/Hecos-Project/Hecos-Assets/blob/main///////012_Hecos_Flows_003.png?raw=true)

  Aquí hay 3 ejemplos prácticos completos para ayudarle a dominar cómo pasar datos entre nodos:

  **Ejemplo 1: Pasar Texto (Seguimiento del Clima)**
  Imagine tener un nodo API que obtiene el clima y desea que se hable en voz alta. 
  1. En el nodo `LOGIC__http_request`, establezca *Output As* en `resultado_clima`.
  2. Encadene un nodo de Sintetizador de Voz (`AUDIO__speak`) justo después de él.
  3. Haga doble clic en el nodo de voz para abrir sus Parámetros. En el campo *text*, escriba exactamente: `Atención, el pronóstico dice: {{ resultado_clima }}`.
  Cuando se ejecute el flujo, Hecos no leerá las llaves: ¡las reemplazará instantáneamente con los datos del clima en vivo! Así es como se pasan los datos.

  **Ejemplo 2: Operaciones Lógicas y Matemáticas**
  Las variables pueden transportar números, perfectos para establecer ramas alternativas.
  1. Agregue una acción que extraiga la hora actual y asigne al *Output As* el nombre `hora_actual`.
  2. Conecte este nodo a un bloque de cruce de caminos `LOGIC__if_else`.
  3. Dentro del parámetro *condition*, escriba: `{{ hora_actual.hour }} > 12`. 
  La expresión se evalúa matemáticamente. Ahora el sistema sabe que debe tomar la ruta *True* solo durante la tarde, bifurcando perfectamente la automatización utilizando datos generados solo milisegundos antes.

  **Ejemplo 3: Encadenamiento Múltiple (Prompting de IA)**
  ¡Nada le impide combinar y mezclar un montón de llaves en el mismo cuadro de parámetros!
  1. Suponga que ya obtuvo un resultado llamado `nombre_usuario` y otro llamado `estado_casa`.
  2. Arrastre un potente nodo de "Cerebro" `AI__prompt` al lienzo.
  3. En el parámetro libre *prompt*, escriba: `"Estimado agente, realice un informe sarcástico sobre el estado de la casa: {{ estado_casa }} y salude a mi jefe, {{ nombre_usuario }}."`
  4. Ahora establezca el *Output As* del nodo de IA en `traduccion_finalizada`. ¡Puede encadenar esto aún más en un correo electrónico simplemente escribiendo `{{ traduccion_finalizada }}` en el cuerpo de `MAIL__send`!

- **Depends On (IDs separados por comas)**: Una lista separada por comas de los **Step IDs** de todos los nodos que deben finalizar _con éxito_ antes de que este nodo pueda comenzar. Fuerza la ejecución secuencial.

---

## 4. Catálogo Completo de Nodos (Acciones Core)

El módulo Flows integra de forma nativa **19 acciones**. Además de estas, Hecos importa automáticamente todas las acciones de los Plugins activos del sistema (como la cámara `WEBCAM__capture` o el correo `MAIL__send`).

Aquí está la lista de los bloques de construcción fundamentales de Hecos Flows:

### 🛠️ Categoría LOGIC
Los directores y controladores de tráfico: retrasan, dividen, unen y evalúan decisiones dentro del flujo.

---

#### 1. `LOGIC__delay` — Pausa Temporizada
Pausa la ejecución del flujo durante un número preciso de segundos antes de pasar al siguiente nodo.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `seconds` | número | Segundos a esperar (por ejemplo, `5`, `30`, `120`) |

```yaml
- id: pausa_5_segundos
  action: LOGIC__delay
  params:
    seconds: 5
```

---

#### 2. `LOGIC__set_variable` — Establecer una Variable
Crea o sobrescribe una variable en el contexto del flujo con un valor estático o dinámico (Jinja2). A diferencia de `output_as`, esta variable está disponible para **todos** los nodos posteriores sin dependencias explícitas.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `name` | cadena | Nombre de la variable a crear (por ejemplo, `nombre_usuario`) |
| `value` | cualquiera | Valor a asignar. Puede contener `{{ variables }}` |

```yaml
- id: establecer_umbral
  action: LOGIC__set_variable
  params:
    name: umbral_temperatura
    value: 25

- id: saludo_personalizado
  action: LOGIC__set_variable
  params:
    name: mensaje
    value: "Buenos días {{ nombre_usuario }}, el umbral es {{ umbral_temperatura }}°C"
```

---

#### 3. `LOGIC__if_else` — Bifurcación Condicional (¡la más utilizada!)
Evalúa una expresión lógica/matemática de Jinja2 y **ejecuta solo una** de las dos ramas: `true_branch` si la condición es verdadera, `false_branch` si es falsa.

> [!IMPORTANT]
> **¿Por qué el nodo parece ejecutar ambas ramas?** Si deja `condition` vacío o sin completar, el motor se establece por defecto en `false` y siempre elige `false_branch`. Si tanto `true_branch` como `false_branch` están vacíos, no sucede nada. ¡Asegúrese de completar los tres campos!

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `condition` | cadena Jinja2 | La expresión a evaluar. **Debe devolver verdadero o falso.** Utilice `{{ variable }}` para datos dinámicos. |
| `true_branch` | dict | El nodo a ejecutar si la condición es **verdadera**. Contiene `action` y `params`. |
| `false_branch` | dict | El nodo a ejecutar si la condición es **falsa**. Contiene `action` y `params`. |

**Ejemplos de condiciones válidas:**
```yaml
# Comparación numérica
condition: "{{ temperatura | int }} > 30"

# Comparación de cadenas
condition: "{{ estado }} == 'activo'"

# Valor booleano directamente de una API
condition: "{{ sensor.detectado == true }}"

# Comparación de tiempo (notación de punto para campos dict)
condition: "{{ hora_actual.hour | int }} > 12"
```

**Ejemplo completo — Termostato inteligente:**
```yaml
- id: comprobar_temperatura
  action: LOGIC__if_else
  params:
    condition: "{{ temp_actual | int }} > 28"
    true_branch:
      action: AUDIO__speak
      params:
        text: "¡Hace calor! La temperatura es de {{ temp_actual }} grados. Encendiendo el aire acondicionado."
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "Temperatura normal: {{ temp_actual }}°C."
  depends_on:
    - leer_sensor
```

**Ejemplo con múltiples acciones en una rama (lista):**
```yaml
- id: comprobar_alarma
  action: LOGIC__if_else
  params:
    condition: "{{ movimiento_detectado == true }}"
    true_branch:
      - action: AUDIO__speak
        params:
          text: "¡Advertencia! ¡Movimiento detectado!"
      - action: AUDIO__play_alarm
        params:
          sound: alarm_urgent
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "Sin movimiento. Casa segura."
```

---

#### 4. `LOGIC__switch` — Selector de Vías Múltiples
Enrutamiento avanzado: evalúa una expresión y utiliza su resultado como una **clave** para elegir qué acción ejecutar entre muchas posibilidades. Como un if/else con muchas ramas.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `expression` | cadena Jinja2 | La expresión cuyo resultado (cadena) se utiliza como clave de búsqueda |
| `branches` | dict | Mapa de `clave: acción` — cada clave corresponde a un posible valor de la expresión |
| `default` | dict | Acción de respaldo si ninguna clave coincide (opcional) |

```yaml
- id: elegir_saludo
  action: LOGIC__switch
  params:
    expression: "{{ momento_dia }}"
    branches:
      mañana:
        action: AUDIO__speak
        params:
          text: "¡Buenos días! ¿Listo para un día productivo?"
      tarde:
        action: AUDIO__speak
        params:
          text: "¿Buenas tardes! ¿Cómo va el trabajo?"
      noche:
        action: AUDIO__speak
        params:
          text: "¡Buenas noches! Hora de relajarse."
    default:
      action: AUDIO__speak
      params:
        text: "¡Hola! No estoy seguro de qué hora es, pero estoy aquí para ti."
```

---

#### 5. `LOGIC__loop` — Bucle sobre una Lista
Itera sobre cada elemento de una lista (almacenada en una variable) y ejecuta una acción para cada uno.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `over` | cadena | El nombre de la variable que contiene la lista (por ejemplo, `destinatarios`) |
| `as_var` | cadena | El nombre de la variable temporal para el elemento actual (por ejemplo, `correo`) |
| `body` | dict | La acción a ejecutar para cada elemento. Use `{{ as_var }}` en params. |

```yaml
# Ejemplo: registrar un mensaje para cada habitación en la lista
- id: init_lista
  action: LOGIC__set_variable
  params:
    name: habitaciones
    value:
      - cocina
      - sala
      - dormitorio

- id: comprobar_cada_habitacion
  action: LOGIC__loop
  params:
    over: habitaciones
    as_var: habitacion
    body:
      action: SYSTEM__chat_message
      params:
        text: "Comprobación completada para: {{ habitacion }}"
  depends_on:
    - init_lista
```

---

#### 6. `LOGIC__template` — Constructor de Texto Jinja2
Renderiza una plantilla Jinja2 interpolando variables y guarda el resultado como una nueva variable. Perfecto para componer mensajes complejos antes de enviarlos.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `template` | cadena Jinja2 | El texto con variables a sustituir (use `{{ variable }}`) |
| `output_as` | cadena | Nombre de la variable en la que almacenar el resultado final |

```yaml
- id: componer_reporte
  action: LOGIC__template
  params:
    template: |
      Reporte para {{ hoy }}
      Temperatura: {{ temp }}°C
      Estado: {{ 'OK' if temp|int < 30 else 'CRÍTICO' }}
    output_as: texto_reporte
  depends_on:
    - leer_datos

- id: enviar_reporte
  action: MAIL__send
  params:
    to: admin@micasa.com
    subject: Reporte Diario
    body: "{{ texto_reporte }}"
  depends_on:
    - componer_reporte
```

---

#### 7. `LOGIC__and_gate` — Puerta AND (todas las condiciones)
Ejecuta `on_success` **solo si TODAS** las condiciones de la lista son verdaderas. Si al menos una es falsa, ejecuta `on_fail`.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `conditions` | lista de cadenas | Lista de expresiones Jinja2 a evaluar. Todas deben ser verdaderas. |
| `on_success` | dict | Acción a ejecutar si **todas** las condiciones se cumplen |
| `on_fail` | dict | Acción a ejecutar si **al menos una** condición falla (opcional) |

```yaml
- id: verificar_seguridad
  action: LOGIC__and_gate
  params:
    conditions:
      - "{{ cerradura.cerrada == true }}"
      - "{{ alarma.activa == true }}"
      - "{{ temperatura.celsius | int }} < 40"
    on_success:
      action: SYSTEM__chat_message
      params:
        text: "✅ Hogar seguro: cerradura cerrada, alarma activa, temperatura OK."
    on_fail:
      action: AUDIO__speak
      params:
        text: "¡Advertencia! ¡Al menos una condición de seguridad no se cumple!"
  depends_on:
    - comprobar_cerradura
    - comprobar_alarma
    - comprobar_temp
```

---

#### 8. `LOGIC__or_gate` — Puerta OR (al menos una condición)
Ejecuta `on_success` si **AL MENOS UNA** de las condiciones es verdadera. Ejecuta `on_fail` solo si **ninguna** de las condiciones es verdadera.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `conditions` | lista de cadenas | Lista de expresiones Jinja2. Solo una necesita ser verdadera. |
| `on_success` | dict | Acción si al menos una condición es verdadera |
| `on_fail` | dict | Acción si ninguna condición es verdadera (opcional) |

```yaml
- id: notificar_si_anomalia
  action: LOGIC__or_gate
  params:
    conditions:
      - "{{ uso_cpu | int }} > 90"
      - "{{ uso_ram | int }} > 85"
      - "{{ disco_lleno == true }}"
    on_success:
      action: AUDIO__speak
      params:
        text: "¡Advertencia: el sistema se está quedando sin recursos! Compruebe inmediatamente."
    on_fail:
      action: SYSTEM__chat_message
      params:
        text: "Sistema saludable. No se detectaron anomalías."
```

---

#### 9. `LOGIC__http_request` — Llamada API/Web
Realiza una solicitud HTTP a cualquier URL y guarda la respuesta JSON (o de texto) como una variable. Este es el nodo que conecta a Hecos con el mundo exterior.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `method` | cadena | Método HTTP: `GET`, `POST`, `PUT`, `DELETE` |
| `url` | cadena | URL de destino. Admite Jinja2 (por ejemplo, `https://api.ejemplo.com/{{ id }}`) |
| `headers` | dict | Encabezados opcionales (por ejemplo, `Authorization: Bearer TOKEN`) |
| `body` | dict o cadena | Cuerpo de la solicitud para POST/PUT (opcional) |
| `output_as` | cadena | Nombre de la variable para almacenar la respuesta JSON analizada |

```yaml
# GET simple — clima actual
- id: obtener_clima
  action: LOGIC__http_request
  params:
    method: GET
    url: "https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.1&current_weather=true"
    output_as: datos_clima

# Leer el resultado en el siguiente nodo
- id: anunciar_clima
  action: AUDIO__speak
  params:
    text: "La temperatura actual en Londres es de {{ datos_clima.current_weather.temperature }} grados."
  depends_on:
    - obtener_clima

# POST con autenticación — notificación de webhook
- id: notificar_webhook
  action: LOGIC__http_request
  params:
    method: POST
    url: "https://hooks.ejemplo.com/notify"
    headers:
      Authorization: "Bearer mi-token-secreto"
      Content-Type: "application/json"
    body:
      event: "flujo_completado"
      message: "{{ resultado }}"
    output_as: respuesta_webhook
```

### ⏰ Categoría TRIGGER
Indica cómo esta automatización "cobrará vida" automáticamente con el tiempo (estos campos modifican la raíz del flujo, no los bloques estándar).
10. **TRIGGER__cron**: El flujo se inicia automáticamente a las horas programadas utilizando UNIX Cron estándar (por ejemplo, `0 7 * * *`). *[Parámetros: `expression`]*
11. **TRIGGER__interval**: El flujo se repite constantemente cada "N" unidades de tiempo (por ejemplo, cada 10 `minutes`). *[Parámetros: `every`, `unit`]*
12. **TRIGGER__manual**: Este flujo está configurado estrictamente para ejecutarse manualmente mediante un botón "Play". Sin ejecución oculta en segundo plano. *[Sin parámetros]*

### 🔊 Categoría AUDIO
Eventos multimedia básicos reproducidos en el dispositivo principal.
13. **AUDIO__speak**: Activa el sintetizador de texto a voz para que la IA hable directamente. *[Parámetros: `text`]*
14. **AUDIO__play_alarm**: Reproduce en bucle uno de los tonos de llamada o alarmas prealmacenados dentro de Hecos. *[Parámetros: `sound`]*

### 💬 Categoría SYSTEM
Interactúa directamente con la memoria e interfaces de la IA central.
15. **SYSTEM__chat_message**: Guarda y muestra un mensaje de texto en el historial clásico de chat de Hecos, como si el asistente le estuviera escribiendo. *[Parámetros: `text`]*

### 🧠 Categoría AI
Permite que los Flows interactúen **bidireccionalmente** con el cerebro de la IA: no solo para escribir mensajes estáticos, sino para enviar prompts reales a la IA y capturar su respuesta como una variable.
16. **AI__prompt**: Envía un prompt de texto al AgentExecutor completo de Hecos (el cerebro completo, incluyendo enrutamiento, complementos y llamadas a herramientas). El flujo se **bloquea** hasta que la IA termina de responder; el texto de la respuesta se devuelve y se puede almacenar utilizando `output_as`. *[Parámetros: `prompt` (string), `save_to_chat` (bool, por defecto: true)]*
   > Nota: con `save_to_chat: true`, el par prompt+respuesta se escribe en el historial de chat como `[Flow] texto del prompt` (rol de usuario) y la respuesta de la IA (rol de asistente), para que siempre pueda revisar lo que el flujo "pensó".

---

### 🧭 Categoría CONTROL
Nodos para controlar el flujo de ejecución.

#### 17. `CONTROL__start` — Punto de Entrada del Flujo
Actúa como el punto de entrada obligatorio para la ejecución del flujo. Cualquier nodo que no esté conectado (directa o indirectamente a través de dependencias `depends_on`) a un nodo `CONTROL__start` no se ejecutará. Esto evita la ejecución accidental de ramas flotantes o aisladas.

Si un flujo contiene uno o más nodos `CONTROL__start`, la ejecución comenzará exclusivamente a partir de ellos. Si el nodo `CONTROL__start` está deshabilitado (usando `disable_mode: stop`), la ejecución de todo el flujo fallará de inmediato.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `priority` | entero | Orden de prioridad de inicio (por defecto: `0`). Los nodos de inicio con valores más bajos se ejecutan primero (por ejemplo, `0` antes de `1`). |

**Ejemplo 1: Inicio lineal simple**
Un flujo básico que se inicia explícitamente desde el nodo de Inicio y habla un saludo.
```yaml
- id: inicio_1
  action: CONTROL__start
  params:
    priority: 0

- id: notificar_hola
  action: AUDIO__speak
  params:
    text: "Sistema listo e iniciado."
  depends_on:
    - inicio_1
```

**Ejemplo 2: Ejecución ordenada de múltiples ramas**
Dos nodos de inicio ejecutados en secuencia temporal utilizando prioridad. `inicializar` se ejecuta primero, seguido de `iniciar_operacion`.
```yaml
- id: inicializar
  action: CONTROL__start
  params:
    priority: 0

- id: set_var
  action: LOGIC__set_variable
  params:
    name: estado_sistema
    value: "listo"
  depends_on:
    - inicializar

- id: iniciar_operacion
  action: CONTROL__start
  params:
    priority: 1

- id: ejecutar_tarea
  action: SYSTEM__chat_message
  params:
    text: "Ejecución iniciada. Estado del sistema: {{ estado_sistema }}"
  depends_on:
    - iniciar_operacion
```

**Ejemplo 3: Verificación de seguridad al inicio**
Al iniciar, el flujo verifica una condición antes de continuar, deteniéndose si es necesario.
```yaml
- id: inicio_seguridad
  action: CONTROL__start
  params:
    priority: 0

- id: comprobar_conexion
  action: LOGIC__http_request
  params:
    method: GET
    url: "https://api.ipify.org?format=json"
    output_as: datos_ip
  depends_on:
    - inicio_seguridad

- id: verificar_ip
  action: LOGIC__if_else
  params:
    condition: "{{ datos_ip is defined and datos_ip.ip != '' }}"
    true_branch:
      action: SYSTEM__chat_message
      params:
        text: "Verificación completada. IP: {{ datos_ip.ip }}"
    false_branch:
      action: LOGIC__abort
      params:
        reason: "Sin conexión a internet al iniciar."
  depends_on:
    - comprobar_conexion
```

---

### 🔄 Categoría FLOWS
Nodos dedicados a administrar y orquestar otros flujos.

#### 18. `FLOWS__run_flow` — Ejecutar Flujo Externo
Le permite llamar y ejecutar otro flujo guardado dentro de Hecos, lo que hace posible estructurar automatizaciones de manera modular (como subrutinas o bibliotecas).

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `flow_id` | cadena | El ID del flujo externo a ejecutar (por ejemplo, el nombre de archivo, `morning_routine`) |
| `wait` | booleano | Si es `true` (por defecto), espera a que el subflujo se complete antes de continuar. Si es `false`, lo inicia en segundo plano en paralelo. |
| `pass_context` | booleano | Si es `true` (por defecto), pasa todas las variables actuales del flujo de llamada al subflujo. |

**Ejemplo 1: Ejecución modular síncrona (Espera)**
El flujo principal ejecuta el subflujo de apagado total de luces, espera a que se complete y luego anuncia las buenas noches.
```yaml
- id: inicio_1
  action: CONTROL__start

- id: apagar_casa
  action: FLOWS__run_flow
  params:
    flow_id: "apagado_luces_total"
    wait: true
    pass_context: false
  depends_on:
    - inicio_1

- id: saludo_final
  action: AUDIO__speak
  params:
    text: "Todas las luces se han apagado. ¡Buenas noches!"
  depends_on:
    - apagar_casa
```

**Ejemplo 2: Ejecución asíncrona (Segundo plano - Fire and Forget)**
El flujo activa una sincronización de datos pesada en segundo plano sin bloquear la interacción del usuario o el resto del flujo actual.
```yaml
- id: inicio_1
  action: CONTROL__start

- id: activar_respaldo
  action: FLOWS__run_flow
  params:
    flow_id: "respaldo_diario_nas"
    wait: false
    pass_context: true
  depends_on:
    - inicio_1

- id: notificacion_inmediata
  action: SYSTEM__chat_message
  params:
    text: "La copia de seguridad se ha iniciado en segundo plano. Puede continuar usando Hecos libremente."
  depends_on:
    - inicio_1
```

**Ejemplo 3: Paso dinámico de parámetros**
Establece variables en el flujo de llamada y las pasa al flujo hijo para personalizar su salida.
```yaml
- id: inicio_1
  action: CONTROL__start

- id: set_datos
  action: LOGIC__set_variable
  params:
    name: destinatario_notificacion
    value: "Tony"
  depends_on:
    - inicio_1

- id: enviar_notificacion_personalizada
  action: FLOWS__run_flow
  params:
    flow_id: "enviar_notificacion_telegram"
    wait: true
    pass_context: true
  depends_on:
    - set_datos
```

---

### 👤 Categoría USER
Nodos dedicados a interacciones interactivas directas con el usuario.

#### 19. `USER__ask_input` — Solicitar Entrada del Usuario
Pausa la ejecución del flujo y espera a que el usuario proporcione una entrada a través del chat (texto) o la voz. La respuesta recibida se almacena en la variable definida en el campo *Output As* del nodo (por ejemplo, `user_input`) para que la utilicen los bloques posteriores.

Si el flujo se interrumpe o cancela (a través del botón "Stop"), el nodo detecta la cancelación, desbloquea la espera y finaliza limpiamente.

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `prompt` | cadena | La pregunta/indicación para enviar al chat y, opcionalmente, leer en voz alta. |
| `speak` | booleano | Si es `true` (por defecto), lee el prompt en voz alta mediante síntesis de voz (TTS). |
| `intercept_mode` | opción (`auto`\|`explicit`\|`api_only`) | **auto**: cualquier mensaje en el chat se captura como la respuesta.<br>**explicit**: responde solo si el mensaje comienza con `@flow` (por ejemplo, `@flow 22`). Recomendado si se usan múltiples clientes de chat.<br>**api_only**: solo responde a través de una llamada API POST a `/api/flows/<run_id>/input`. |
| `multi_run_priority`| opción (`first`\|`all`) | Si múltiples flujos están esperando entrada:<br>**first**: asigna la respuesta solo al flujo más antiguo.<br>**all**: envía la misma respuesta a todos los flujos en espera. |
| `timeout_seconds` | entero | Tiempo máximo de espera en segundos antes de expirar (por defecto: `0` = esperar para siempre). |
| `on_timeout_continue`| booleano | Si es `true` (por defecto: `false`), continúa la ejecución con una cadena vacía (`""`) al expirar el tiempo en lugar de fallar el flujo. |

**Ejemplo 1: Elección interactiva (Sí/No)**
Pregunta al usuario si quiere escuchar un chiste, intercepta cualquier respuesta en el chat y bifurca la ejecución.
```yaml
- id: inicio_1
  action: CONTROL__start

- id: solicitar_eleccion
  action: USER__ask_input
  params:
    prompt: "¿Te gustaría escuchar un chiste?"
    speak: true
    intercept_mode: "auto"
    timeout_seconds: 60
  output_as: respuesta_chiste
  depends_on:
    - inicio_1

- id: evaluar_respuesta
  action: LOGIC__if_else
  params:
    condition: "'si' in {{ respuesta_chiste | lower }} or 'ok' in {{ respuesta_chiste | lower }}"
    true_branch:
      action: AUDIO__speak
      params:
        text: "¿Por qué los científicos no confían en los átomos? ¡Porque lo componen todo!"
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "No hay problema, tal vez la próxima vez."
  depends_on:
    - solicitar_eleccion
```

**Ejemplo 2: Punto de consigna numérico seguro con tiempo de espera**
Solicita ingresar una temperatura objetivo explícitamente (usando `@flow <temperatura>`). Si el usuario no responde dentro de 15 segundos, continúa usando el valor predeterminado.
```yaml
- id: inicio_1
  action: CONTROL__start

- id: solicitar_temperatura
  action: USER__ask_input
  params:
    prompt: "¿A qué temperatura le gustaría configurar el termostato? Responda escribiendo '@flow <grados>'"
    speak: false
    intercept_mode: "explicit"
    timeout_seconds: 15
    on_timeout_continue: true
  output_as: grados_elegidos
  depends_on:
    - inicio_1

- id: verificar_y_configurar
  action: LOGIC__if_else
  params:
    condition: "{{ grados_elegidos != '' }}"
    true_branch:
      action: SYSTEM__chat_message
      params:
        text: "Configurando la temperatura a {{ grados_elegidos }} grados."
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "Sin respuesta. Manteniendo la temperatura predeterminada en 20 grados."
  depends_on:
    - solicitar_temperatura
```

**Ejemplo 3: Análisis de sentimiento de la entrada**
Pregunta al usuario cómo se siente, pasa la entrada a la IA para analizar su estado de ánimo y responde en consecuencia.
```yaml
- id: inicio_1
  action: CONTROL__start

- id: solicitar_animo
  action: USER__ask_input
  params:
    prompt: "¡Hola! ¿Cómo va tu día hoy?"
    speak: true
    intercept_mode: "auto"
    timeout_seconds: 0
  output_as: animo_usuario
  depends_on:
    - solicitar_animo

- id: analizar_sentimiento
  action: AI__prompt
  params:
    prompt: "El usuario respondió: '{{ animo_usuario }}'. Analiza su estado de ánimo (positivo/negativo/neutral) y responde con una sola frase de apoyo o felicidad adecuada para su estado de ánimo."
    save_to_chat: true
  depends_on:
    - solicitar_animo
```

---

## 5. Ejemplos Prácticos Completos

A continuación se muestran tres ejemplos de flujos YAML completos, perfectos para analizar cómo se comportan los nodos con variables (`output_as`), dependencias y en paralelo.

### Ejemplo 1: Rutina de la Mañana con Variables Dinámicas
Este flujo introduce el encadenamiento de parámetros: Hecos adquiere la hora actual, almacenándola en la variable `current_time` mediante el uso de `output_as`, y luego la recita en el siguiente paso interpolándola dentro de las llaves `{{ current_time }}`.

```yaml
name: Rutina de Mañana Avanzada
trigger:
  type: manual
pipeline:
  - id: paso_alarma
    action: AUDIO__play_alarm
    params:
      sound: gentle_wake

  - id: paso_pausa
    action: LOGIC__delay
    params:
      seconds: 5
    depends_on:
      - paso_alarma

  - id: obtener_hora_actual
    action: EXECUTOR__get_time
    # Guardamos la salida en la variable 'current_time'
    output_as: current_time
    depends_on:
      - paso_pausa

  - id: paso_saludo
    action: AUDIO__speak
    params:
      # Usamos la salida generada por el bloque "obtener_hora_actual"
      text: "¡Buenos días! Actualmente son las {{ current_time }}, debes levantarte."
    depends_on:
      - obtener_hora_actual
```

### Ejemplo 2: Alerta de Seguridad de Hogar Múltiple (Paralelismo)
En este flujo veremos el **paralelismo en acción**. Los dos bloques `notify_voice` y `send_email_alert` comparten exactamente la misma dependencia (`wait_for_arming`). Esto significa que, una vez que termina `LOGIC__delay`, Hecos ejecutará ambas notificaciones simultáneamente, realizando multitarea asíncrona real.

```yaml
name: Alerta de Seguridad Múltiple
trigger:
  type: manual
pipeline:
  - id: wait_for_arming
    action: LOGIC__delay
    params:
      seconds: 30

  - id: notify_voice
    action: AUDIO__speak
    params:
      text: "Advertencia, el sistema de seguridad automático ha sido iniciado y armado."
    depends_on:
      - wait_for_arming

  - id: send_email_alert
    action: MAIL__send
    params:
      to: admin@micasa.com
      subject: "Alarma Hecos"
      body: "Le notificamos que el sistema de seguridad ha sido armado."
    depends_on:
      - wait_for_arming
```

### Ejemplo 3: Control de Dispositivo con API y Eventos Secuenciales
Este bloque llama a los servidores de una API y, solo después de una pausa, produce un cierre. ¡Imagine esto como una macro de hogar inteligente que se conecta a Philips Hue o Home Assistant!

```yaml
name: Cafetera Inteligente
trigger:
  type: interval
  every: 6
  unit: hours
pipeline:
  - id: call_coffee_api
    action: LOGIC__http_request
    params:
      method: "POST"
      url: "http://192.168.1.50/api/coffee_maker/start"
      body:
        mode: "espresso_macchiato"

  - id: announce_start
    action: AUDIO__speak
    params:
      text: "La operación para hacer un espresso fantástico está en marcha."
    depends_on:
      - call_coffee_api

  - id: wait_brewing
    action: LOGIC__delay
    params:
      seconds: 40
    depends_on:
      - announce_start

  - id: announce_ready
    action: AUDIO__speak
    params:
      text: "Tu café altamente aromático está listo."
    depends_on:
      - wait_brewing
```

> Nota: ¡Todos estos archivos de ejemplo representan fielmente en formato de texto la estructura exacta que el sistema maneja cuando conecta, desconecta o escribe parámetros dentro de su Canvas visual interactivo!

---

## 6. Ejemplos Avanzados: Escenarios Reales y Singulares

Estos tres ejemplos demuestran el verdadero potencial de Flows: algoritmos condicionales, cadenas de procedimientos temporizadas e integraciones de estilo ciencia ficción. Úselos como inspiración y modifique los parámetros para adaptarlos a su propio entorno.

---

### 🧮 Ejemplo A — El Algoritmo Bitcoin Watchdog
*Escenario: Cada 10 minutos, Hecos consulta la API de CoinGecko, recupera el precio actual de Bitcoin y toma una decisión: si el precio cae por debajo de 60.000 €, grita en voz alta y le envía un correo electrónico urgente; si supera los 100.000 €, lo celebra con usted en el chat. De lo contrario, simplemente registra el precio de forma silenciosa.*

Esta es la forma más pura de un algoritmo: entrada de datos → procesamiento → acción condicional.

```yaml
name: Algoritmo Bitcoin Watchdog
trigger:
  type: interval
  every: 10
  unit: minutes
pipeline:
  # PASO 1: Llamar a la API pública de CoinGecko (cero claves API, costo cero)
  - id: get_bitcoin_price
    action: LOGIC__http_request
    params:
      method: GET
      url: "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur"
      output_as: api_response

  # PASO 2: Extraer el valor numérico bruto de la respuesta JSON
  - id: extract_price
    action: LOGIC__template
    params:
      template: "{{ api_response.bitcoin.eur }}"
      output_as: btc_price
    depends_on:
      - get_bitcoin_price

  # PASO 3: Construir un mensaje legible
  - id: format_message
    action: LOGIC__template
    params:
      template: "Bitcoin vale actualmente {{ btc_price }} euros."
      output_as: price_summary
    depends_on:
      - extract_price

  # PASO 4: BIFURCACIÓN — Evaluar el precio usando if_else
  - id: check_crash
    action: LOGIC__if_else
    params:
      condition: "{{ btc_price | int }} < 60000"
      true_branch:
        action: AUDIO__speak
        params:
          text: "¡ALERTA ROJA! ¡Bitcoin acaba de caer a {{ btc_price }} euros! ¡Abra Coinbase AHORA!"
      false_branch:
        action: SYSTEM__chat_message
        params:
          text: "📊 {{ price_summary }} — situación normal."
    depends_on:
      - format_message

  # PASO 5 (paralelo al 4): Comprobar la hipótesis MOON
  - id: check_moon
    action: LOGIC__if_else
    params:
      condition: "{{ btc_price | int }} > 100000"
      true_branch:
        action: AUDIO__speak
        params:
          text: "¡AAAA! ¡Superamos los cien mil euros! ¡Estamos en Marte! 🚀"
      false_branch:
        action: LOGIC__delay
        params:
          seconds: 1  # sin acción, espera simbólica
    depends_on:
      - format_message

  # PASO 6: Si está cayendo, también envía un correo electrónico urgente
  - id: emergency_mail
    action: MAIL__send
    params:
      to: me@myemail.com
      subject: "⚠️ Alerta de caída de Bitcoin — Hecos Watchdog"
      body: "{{ price_summary }} — El precio está por debajo del umbral crítico. Compruébelo inmediatamente."
    depends_on:
      - check_crash
```

---

### 🍮 Ejemplo B — El Chef Robótico: Soufflé de Chocolate Paso a Paso
*Escenario: Una receta interactiva que reemplaza el temporizador de su teléfono por Hecos guiándole vocalmente paso a paso, con cuentas regresivas precisas, alarmas y recordatorios de chat para cada fase crítica. Sígalo y su soufflé quedará perfecto.*

Esta es la forma de un flujo de receta de procedimiento: canalización secuencial pura con retrasos quirúrgicos.

```yaml
name: Receta de Soufflé de Chocolate
trigger:
  type: manual
pipeline:
  # FASE 1 - Preparación: anuncio y configuración
  - id: begin_recipe
    action: AUDIO__speak
    params:
      text: "Bienvenido a la receta de soufflé de chocolate. Prepare 200 gramos de chocolate negro, 4 huevos y un poco de mantequilla."

  - id: set_oven_temp
    action: SYSTEM__chat_message
    params:
      text: "🍫 **RECETA ACTIVA** — Precaliente el horno a 190°C. Engrase con mantequilla y azúcar 4 moldes para soufflé."
    depends_on:
      - begin_recipe

  # FASE 2 - Derretir el chocolate (7 minutos al baño maría)
  - id: announce_melt
    action: AUDIO__speak
    params:
      text: "Now melt the chocolate using a bain-marie. I will notify you in 7 minutes."
    depends_on:
      - set_oven_temp

  - id: wait_melt
    action: LOGIC__delay
    params:
      seconds: 420  # 7 minutos
    depends_on:
      - announce_melt

  - id: alarm_melt_done
    action: AUDIO__play_alarm
    params:
      sound: chime_success
    depends_on:
      - wait_melt

  - id: say_melt_done
    action: AUDIO__speak
    params:
      text: "El chocolate está listo. Retírelo del fuego y agregue la mantequilla. Luego separe las yemas de las claras de huevo."
    depends_on:
      - alarm_melt_done

  # FASE 3 - Batir las claras de huevo (estimado 4 min con batidor eléctrico)
  - id: announce_whip
    action: AUDIO__speak
    params:
      text: "Comience a batir las claras a punto de nieve. Le avisaré en 4 minutos cuando estén listas."
    depends_on:
      - say_melt_done

  - id: wait_whip
    action: LOGIC__delay
    params:
      seconds: 240  # 4 minutos
    depends_on:
      - announce_whip

  - id: say_whip_done
    action: AUDIO__speak
    params:
      text: "¡Las claras están listas! Incorpórelas suavemente al chocolate de abajo hacia arriba. Luego llene los moldes hasta las tres cuartas partes."
    depends_on:
      - wait_whip

  # FASE 4 - Horneado (EXACTAMENTE 12 minutos, ¡no abra el horno!)
  - id: announce_baking
    action: AUDIO__speak
    params:
      text: "Colóquelos en el horno. Advertencia: sáquelos en exactamente 12 minutos. NO abra el horno antes, ¡de lo contrario se bajarán!"
    depends_on:
      - say_whip_done

  - id: chat_baking_warning
    action: SYSTEM__chat_message
    params:
      text: "⏱️ **Horneado del soufflé iniciado** — ¡No abra el horno! Temporizador: 12 minutos. El final del horneado se acerca."
    depends_on:
      - say_whip_done

  - id: wait_baking
    action: LOGIC__delay
    params:
      seconds: 720  # exactamente 12 minutos
    depends_on:
      - announce_baking

  - id: final_alarm
    action: AUDIO__play_alarm
    params:
      sound: alarm_urgent
    depends_on:
      - wait_baking

  - id: final_announcement
    action: AUDIO__speak
    params:
      text: "¡AHORA! ¡Saque los soufflés del horno AHORA MISMO y sírvalos de inmediato! ¡Buen provecho!"
    depends_on:
      - final_alarm

  - id: final_chat
    action: SYSTEM__chat_message
    params:
      text: "✅ **¡Soufflé terminado!** Sirva dentro de los 60 segundos posteriores al horneado. ¡Buen provecho, chef!"
    depends_on:
      - final_alarm
```

---

### 🤖 Ejemplo C — El Centinela de la Medianoche (Ciencia Ficción en el Hogar)
*Escenario: Cada noche a la medianoche, Hecos se despierta como un guardián robótico silencioso. Consulta tres API de hogar inteligente (cerradura inteligente, cámara de vigilancia, sensor de temperatura), valida los resultados mediante una puerta lógica AND y, solo si todo está bien, envía un informe en el chat. Si algo es anómalo, activa una alarma de voz + un correo electrónico de alerta con formato personalizado. Un verdadero sistema de seguridad programado en YAML.*

```yaml
name: Centinela del Hogar de Medianoche
trigger:
  type: cron
  expression: "0 0 * * *"  # cada noche a las 00:00
pipeline:
  # FASE 1 - Anuncio silencioso en el chat (sin audio - ¡es de noche!)
  - id: begin_patrol
    action: SYSTEM__chat_message
    params:
      text: "🌙 **Patrulla Nocturna Iniciada** — Hecos está comprobando el estado de la casa..."

  # FASE 2 (paralela) - Consultar 3 API de hogar inteligente simultáneamente
  - id: check_lock
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.10/api/smart_lock/status"
      output_as: lock_status
    depends_on:
      - begin_patrol

  - id: check_camera
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.11/api/camera/motion_detected"
      output_as: camera_status
    depends_on:
      - begin_patrol

  - id: check_temperature
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.12/api/thermostat/current_temp"
      output_as: temp_data
    depends_on:
      - begin_patrol

  # FASE 3 - PUERTA AND: proceder solo si la cerradura está cerrada y no hay movimiento
  - id: security_gate
    action: LOGIC__and_gate
    params:
      conditions:
        - "{{ lock_status.locked == true }}"
        - "{{ camera_status.motion == false }}"
      on_success:
        action: SYSTEM__chat_message
        params:
          text: "✅ **Hogar SEGURO** — Cerradura: cerrada | Cámara: sin movimiento | Temp: {{ temp_data.celsius }}°C"
      on_fail:
        action: AUDIO__speak
        params:
          text: "¡ADVERTENCIA! ¡La patrulla nocturna ha detectado una anomalía! ¡Compruebe la casa de inmediato!"
    depends_on:
      - check_lock
      - check_camera
      - check_temperature

  # FASE 4 - Componer un informe formateado y enviarlo por correo
  - id: compose_report
    action: LOGIC__template
    params:
      template: |
        INFORME NOCTURNO DE HECOS — Medianoche
        Cerradura: {{ lock_status.locked | ternary('CERRADA', 'ABIERTA!!') }}
        Movimiento de Cámara: {{ camera_status.motion | ternary('¡DETECTADO!', 'Ninguno') }}
        Temperatura Interior: {{ temp_data.celsius }}°C
        Estado General: {{ 'TODO DESPEJADO' if lock_status.locked and not camera_status.motion else 'ANOMALÍA DETECTADA' }}
      output_as: night_report
    depends_on:
      - security_gate

  - id: send_night_report
    action: MAIL__send
    params:
      to: me@myemail.com
      subject: "🌙 Informe Nocturno de Hecos — Casa Monitoreada"
      body: "{{ night_report }}"
    depends_on:
      - compose_report
```

> 💡 **Desafío extra**: conecte este flujo a la acción `WEBCAM__capture` para adjuntar una foto real de la cámara interna al informe de medianoche. ¡Simplemente agregue un nodo entre `check_camera` and `compose_report`!

---

## 7. El Ejecutor y Comandos del Sistema (Shell y Python)

Entre los nodos más potentes de Hecos se encuentran los relacionados con el módulo **EXECUTOR**. Estos nodos le permiten salir de los límites de la automatización estándar y emitir comandos reales a su sistema operativo (Windows o Linux).

### 7.1 Ejecución Visible vs. Invisible (Segundo Plano)

Al utilizar la línea de comandos (Shell) a través de Hecos, debe decidir si el usuario debe ver lo que está sucediendo o si todo debe ejecutarse silenciosamente detrás de escena.

- **`EXECUTOR__execute_background_command`**: Este nodo está diseñado para ejecutar comandos en modo *silencioso* (headless). No se abrirá ninguna ventana negra en el escritorio. El comando se ejecutará en las sombras y la salida se guardará en un archivo de registro. Es perfecto para descargar archivos, iniciar servidores o realizar operaciones de mantenimiento sin molestarle.
  *Advertencia*: Si simplemente escribe `cmd` o `bash` aquí, el nodo creará una terminal invisible que esperará infinitamente su entrada, ¡bloqueando el flujo!
- **`EXECUTOR__execute_shell_command`**: Si desea **abrir visiblemente** un programa o una ventana de símbolo del sistema en el escritorio, debe "desacoplar" el proceso utilizando el comando nativo de su sistema operativo, como `start` (en Windows) o `gnome-terminal` (en Linux).

> [!TIP]
> **¿Cómo ejecutar múltiples comandos seguidos?** ¡No es necesario utilizar un nodo para cada comando! Puede utilizar el operador `&&` para concatenarlos en una sola cadena. Hecos los ejecutará estrictamente en secuencia. Ejemplo: `ipconfig && mkdir nueva_carpeta && echo "¡Listo!"`

#### Ejemplo 1: Crear una Carpeta Silenciosamente (Segundo Plano)
*Escenario: Un flujo crea un directorio de copia de seguridad sin mostrar nada en la pantalla.*
```yaml
  - id: crear_respaldo_silencioso
    action: EXECUTOR__execute_background_command
    params:
      command: "mkdir C:\backup_hecos && echo Carpeta de respaldo creada"
```

#### Ejemplo 2: Abrir un Símbolo del Sistema Visible (Solo Windows)
*Escenario: Quiere que Hecos abra una ventana de CMD negra, haga un PING a Google y mantenga la ventana abierta para que pueda leer el resultado.*
```yaml
  - id: abrir_cmd_visible
    action: EXECUTOR__execute_shell_command
    params:
      # El parámetro /k ("keep") mantiene la ventana abierta. Use /c ("close") para cerrarla.
      command: "start cmd /k \"ping 8.8.8.8 && echo ¡Ping completado!\""
```

### 7.2 El Problema Multiplataforma (Windows vs. Linux)

Si escribe `start cmd` en un nodo de shell, acaba de hacer que su flujo sea **incompatible con Linux o Mac**. En Linux, `cmd` no existe y el flujo arrojara un error. ¿Cómo se resuelve este problema si quiere crear automatizaciones universales?

Tiene dos soluciones:
1. **Utilice nodos nativos de Hecos**: En lugar de utilizar `execute_shell_command` y escribir `mkdir` o `taskkill`, ¡utilice los nodos ejecutores dedicados! Por ejemplo: `EXECUTOR__create_dir`, `EXECUTOR__read_file` o `EXECUTOR__kill_process`. Hecos resolverá por sí solo si está en Windows o Linux y ejecutará el comando correcto.
2. **¡Utilice el creador de scripts definitivo: Python!**

### 7.3 `EXECUTOR__run_python_code`: El Creador de Scripts Universal Definitivo

En lugar de volverse loco con comandos concatenados por `&&` o archivos `.bat`, puede utilizar el nodo `EXECUTOR__run_python_code`. Este nodo le proporciona un editor real donde puede insertar un script de Python.

**¿Por qué usar Python en lugar de la Shell?**
- **Es Multiplataforma**: El mismo script de Python se ejecuta exactamente igual en Windows, Linux y Raspberry Pi.
- **Es Potente**: Puede utilizar bucles lógicos complejos, cálculos matemáticos o formatear datos mucho mejor que en un símbolo del sistema.
- **Variables**: ¡Puede devolver el resultado de su script (mediante `print`) para guardarlo en una variable `output_as` y pasarlo a los nodos posteriores!

#### Ejemplo 3: Un Script de Python Multiplataforma Universal
*Escenario: Un script de Python que detecta por sí solo en qué sistema operativo está, crea de forma segura una carpeta en el escritorio del usuario y devuelve el resultado a Hecos para que lo lea en voz alta.*
```yaml
  - id: script_python_universal
    action: EXECUTOR__run_python_code
    params:
      code: |
        import os
        from pathlib import Path
        
        # Encontrar la carpeta del Escritorio tanto en Windows como en Linux
        desktop_dir = Path.home() / "Desktop"
        nueva_carpeta = desktop_dir / "Hecos_Magic_Folder"
        
        if not nueva_carpeta.exists():
            nueva_carpeta.mkdir()
            print("¡He creado la carpeta mágica en el escritorio!")
        else:
            print("La carpeta ya existía, no hay problema.")
    output_as: resultado_script

  - id: anunciar_resultado
    action: AUDIO__speak
    params:
      text: "{{ resultado_script }}"
    depends_on:
      - script_python_universal
```

¡De esta manera ha creado una automatización que puede compartir con cualquier persona, independientemente de la PC o del sistema operativo que use!

