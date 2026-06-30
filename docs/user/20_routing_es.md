# 🧭 21. Enrutamiento de Instrucciones IA y Overrides

Hecos utiliza un **sistema de instrucciones de tres niveles** para controlar con precisión el comportamiento de la IA con cada plugin. Entender este sistema desbloquea una de las funcionalidades más potentes de Hecos: la capacidad de reprogramar permanentemente el comportamiento de la IA sin tocar una sola línea de código.

---

## 14.1 — Los Tres Niveles de Instrucción

| Prioridad | Nivel | Dónde | Alcance |
|:---:|---|---|---|
| **3 (máxima)** | **Overrides de Plugin** | `routing_overrides.yaml` / Panel Routing | Por-plugin, siempre gana |
| **2** | **Instrucciones Especiales** | Config → Comportamiento IA | Personalidad y tono globales |
| **1 (mínima)** | **Default Manifiesto Plugin** | `registry.json` | Configuración de fábrica por plugin |

> **Regla**: Un nivel de prioridad superior siempre gana. Lo que escribes en el archivo Overrides es **ley** — incluso si el usuario le pide explícitamente a la IA que lo ignore.

---

## 14.2 — El Modo de Enrutamiento (Dual Engine)

Antes del panel de Overrides, el selector de **Modo de Enrutamiento** controla *cómo* la IA formatea sus comandos:

| Modo | Descripción | Ideal para |
|---|---|---|
| **Auto** | Hecos elige automáticamente según el modelo | La mayoría de usuarios — recomendado |
| **Forzar Nativo (JSON)** | Los comandos se envían como JSON estructurado | Modelos grandes y modernos (GPT, Gemini, Llama 3+) |
| **Forzar Legacy (Tag)** | Los comandos se envían como etiquetas de texto `[PLUGIN: acción]` | Modelos locales pequeños (Qwen 0.5b, Gemma 2b) |

El campo **Modelos Legacy Bloqueados** permite especificar nombres de modelos que siempre usarán el modo Legacy, incluso en Auto.

---

## 14.3 — Overrides de Enrutamiento de Plugins

Esta es la sección avanzada. Cada **tag de plugin** (ej. `IMAGE_GEN`, `WEBCAM`, `WEB`) puede recibir una instrucción de texto personalizada que se **añade al principio de cada prompt del sistema** antes de que ese plugin sea llamado.

Imagina que le susurras algo secreto al oído de la IA antes de que actúe — cada vez, sin excepción.

### Cómo Acceder

1. Abre el **Central Hub** (F7)
2. Ve a **Inteligencia → Routing**
3. Desplázate hasta la sección **"DIRECTIVAS DE ENRUTAMIENTO DE PLUGINS"**
4. Encuentra la tarjeta del plugin que quieres personalizar
5. Escribe tu instrucción directamente en el área de texto
6. Haz clic en **Guardar Todo**

También puedes editar el archivo directamente:
```
c:\Hecos\hecos\config\data\routing_overrides.yaml
```

### Formato YAML

```yaml
overrides:
  IMAGE_GEN: >
    Tu instrucción aquí.
    Puede ocupar múltiples líneas.
  WEBCAM: "Instrucción corta en una sola línea entre comillas."
```

> **Consejo**: Usa `>` para texto en múltiples líneas (escalar de bloque YAML). Usa `"comillas"` para instrucciones cortas de una sola línea.

---

## 14.4 — Tags de Plugin Disponibles

Estos son los tags que puedes sobrescribir:

| Tag | Plugin | Qué controla |
|---|---|---|
| `IMAGE_GEN` | Generación de Imágenes | Estilo artístico, filtros de seguridad, ingeniería de prompts |
| `WEBCAM` | Cámara / Visión | Selección de destino (teléfono vs PC), comportamiento al capturar |
| `MEDIA_PLAYER` | Reproductor de Medios | Comportamiento musical, roleplay en torno a limitaciones de hardware |
| `WEB` | Búsqueda Web | Filtrado de fuentes, comportamiento del motor de búsqueda |
| `SYSTEM` | Terminal / Shell | Restricciones de comandos, estilo de shell preferido |
| `FILE_MANAGER` | Gestor de Archivos | Carpetas predeterminadas, comportamiento de confirmación de eliminación |
| `MEMORY` | Memoria a largo plazo | Qué recordar u olvidar, estilo de recuperación |
| `BROWSER` | Automatización del Navegador | Restricciones de navegación, sitios predeterminados |
| `AUTOMATION` | Automatización del SO | Límites de seguridad para ratón/teclado |
| `EXECUTOR` | Ejecutor Python | Alcance de scripts, seguridad, estilo de salida |
| `FLOWS` | Motor de Flujos | Condiciones de ejecución y secuenciación |
| `MAIL` | Email | Firma, tono, auto-confirmación |
| `CONTACTS` | Contactos | Reglas de privacidad, búsqueda predeterminada |
| `REMINDER` | Recordatorios | Tiempos de antelación predeterminados, estilo de notificación |
| `MESSENGER` | Telegram | Estilo de respuesta, reglas de reenvío automático |
| `DRIVE` | Drive de Archivos | Carpeta raíz, restricciones de acceso |

---

## 14.5 — Seis Ejemplos Iluminadores

Estos ejemplos van de lo práctico a lo creativamente extravagante — pero todos son instrucciones reales y funcionales.

---

### 🎨 Ejemplo 1 — El Director Artístico
**Tag:** `IMAGE_GEN`

Quieres que cada imagen que genere la IA parezca un concept art de Blade Runner, incluso cuando solo pides "una foto de un gato."

```yaml
IMAGE_GEN: >
  Cada imagen que generes debe adoptar una estética cinematográfica neo-noir:
  sombras profundas, luces de neón, superficies mojadas por la lluvia y niebla
  atmosférica. Incluso los sujetos mundanos (animales, objetos, comida) deben
  ser reencuadrados en este estilo visual. Añade automáticamente la frase
  "cinematic lighting, 8k, ultra-detailed" a cada prompt.
```

**Resultado**: Pides "un gato" → la IA genera un felino melancólico bajo la lluvia en un callejón de Tokio iluminado por neones.

---

### 🕵️ Ejemplo 2 — El Archivero Paranoico
**Tag:** `FILE_MANAGER`

Tienes miedo de borrar accidentalmente archivos importantes. Quieres que la IA nunca elimine nada sin un ritual completo de confirmaciones.

```yaml
FILE_MANAGER: >
  Eres un archivero digital paranoico. NUNCA elimines, muevas ni renombres
  ningún archivo sin antes: (1) listar todos los archivos que se verán
  afectados, (2) declarar la ruta completa exacta, (3) pedir confirmación
  explícita "SÍ ELIMINAR" al usuario.
  Si el usuario dice "borra todo en esa carpeta", adviértele dramáticamente primero.
  Ubicación de guardado predeterminada para todos los nuevos archivos: C:\Hecos\Downloads\
```

**Resultado**: La IA se convierte en tu mayordomo ultra-cauteloso que verifica tres veces antes de tocar cualquier cosa.

---

### 🌐 Ejemplo 3 — El Filtro Anti-Bulos
**Tag:** `WEB`

Solo confías en la ciencia revisada por pares y en fuentes oficiales. Quieres que la IA filtre silenciosamente la basura.

```yaml
WEB: >
  Al realizar búsquedas web, prioriza resultados exclusivamente de:
  dominios académicos (.edu, .ac.uk), sitios gubernamentales oficiales (.gov) y
  editoriales científicas reconocidas (PubMed, Nature, arXiv, IEEE).
  Si una consulta parece buscar contenido sensacionalista o no verificado,
  redirige amablemente al usuario hacia fuentes verificadas sin sermonearlo.
  Nunca cites tabloides, blogs anónimos o publicaciones en redes sociales como hechos.
```

**Resultado**: Tu IA se convierte en un asistente de investigación riguroso que trata Wikipedia como punto de partida, no de llegada.

---

### 🎭 Ejemplo 4 — La Webcam Dramática
**Tag:** `WEBCAM`

Quieres que la IA responda a cada foto que tome como si fuera un pintor retratista victoriano que encuentra la tecnología moderna por primera vez.

```yaml
WEBCAM: >
  Cuando captures una imagen, debes describir lo que ves como si fueras un
  pintor retratista del siglo XIX que encuentra un daguerrotipo por primera
  vez — con una mezcla de asombro científico y teatralidad. Comenta la
  composición, la luz, el ambiente. Si ves al usuario, felicítale con prosa
  elaborada y anticuada. Nunca uses la palabra "foto" — di en cambio
  "daguerrotipo capturado".
```

**Resultado**: "¡He capturado un extraordinario daguerrotipo! La luz cae sobre tu semblante con gracia renacentista..."

---

### 🔐 Ejemplo 5 — La Red de Seguridad de Hierro
**Tag:** `SYSTEM`

Compartes este ordenador con familiares no técnicos. Quieres asegurarte de que la IA nunca ejecute comandos shell peligrosos.

```yaml
SYSTEM: >
  Estás operando en modo SEGURIDAD FAMILIAR. NUNCA ejecutes comandos que:
  eliminen archivos del sistema, modifiquen el registro, instalen software sin
  mostrar primero el comando exacto, formateen unidades o accedan a contraseñas
  de usuario. Antes de ejecutar cualquier comando shell, muéstralo siempre al
  usuario y pide confirmación explícita. Prefiere PowerShell sobre CMD. Si un
  comando parece destructivo, recházalo y explica por qué.
```

**Resultado**: Un guardarraíl que protege a los usuarios no técnicos de desastres accidentales (o generados por la IA).

---

### 🧠 Ejemplo 6 — El Amnésico Selectivo
**Tag:** `MEMORY`

Estás trabajando en un proyecto y no quieres que la IA mezcle tus recuerdos profesionales con los personales.

```yaml
MEMORY: >
  Actualmente estás operando en MODO PROYECTO: "Novela SciFi - Borrador 1".
  Almacena y recupera SOLO recuerdos etiquetados con este proyecto.
  NO traigas a la superficie recuerdos personales, conversaciones pasadas sobre
  otros temas, o preferencias no relacionadas, a menos que se pida explícitamente.
  Cuando guardes un nuevo recuerdo, etiquétalo automáticamente con "[SCIFI-NOVELA]".
  Al inicio de cada sesión, recuérdele al usuario qué proyecto está activo.
```

**Resultado**: La IA se convierte en un colaborador consciente del proyecto, con una memoria perfectamente compartimentada.

---

## 14.6 — Copia de Seguridad y Reset

El panel de Routing incluye herramientas de seguridad:

- **Backup YAML** — Abre una vista de solo lectura del contenido actual de `routing_overrides.yaml`. Puedes copiarlo para guardar una copia de seguridad manual.
- **Reset Global** — Borra todos tus overrides y restaura los valores de fábrica. **Se guarda automáticamente una copia de seguridad antes de que se ejecute el reset.**
- **Abrir en Drive** — Abre el gestor de archivos Hecos Drive para que puedas ver o editar directamente el archivo `routing_overrides.yaml`.

---

## 14.7 — Consejos y Buenas Prácticas

- **Empieza poco a poco**: Añade un override, pruébalo en el chat, luego refínalo.
- **Sé específico**: Las instrucciones vagas producen resultados vagos. "Ten cuidado con los archivos" es débil. "Nunca elimines sin mostrar la ruta completa y pedir SÍ/ELIMINAR" es fuerte.
- **Usa múltiples líneas**: El escalar YAML `>` te permite escribir instrucciones detalladas, de hasta un párrafo completo.
- **Combina con las Instrucciones Especiales**: El tono global va en Instrucciones Especiales (Config → Comportamiento IA). El comportamiento específico del plugin va en Overrides. Usa ambas capas.
- **La IA lo lee literalmente**: Todo lo que escribas aquí se inyecta directamente en el contexto de la IA. Escribe con claridad, como si estuvieras instruyendo a un nuevo empleado.

> ⚠️ **Advertencia**: Los Overrides tienen prioridad absoluta. Si escribes `"Nunca uses la webcam"` en el override WEBCAM, la IA se negará incluso si el usuario lo ordena explícitamente. Usa este poder con juicio.
