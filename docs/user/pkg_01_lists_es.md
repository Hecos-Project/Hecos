# 📋 Gestión de Listas

El módulo **Lists** (Gestión de Listas) de Hecos es la herramienta ideal para organizar tus tareas, notas, listas de compras o apuntes de desarrollo directamente dentro del ecosistema. Está diseñado para ser ligero, accesible y rápido, ofreciendo tanto una vista completa a pantalla completa en el Central Hub como un práctico widget para tu Control Room.

---

## 📋 Dónde Encontrar las Listas

Puedes acceder a la gestión de listas de dos formas diferentes dentro de la WebUI:

1. **Central Hub (Panel Principal)**: Haz clic en la opción "Lists" en el menú lateral izquierdo del Central Hub. Esta pantalla a pantalla completa ofrece una barra lateral con todas tus listas y un área central extendida para gestionar los elementos en detalle.
2. **Control Room Widget**: Puedes añadir el widget de listas en tu Control Room (el tablero con cuadrícula flexible). Es perfecto para vigilar tus tareas pendientes mientras monitoreas otros módulos del sistema.

---

## ⌨️ Navegación por Teclado (Accesos Directos)

Para que la experiencia de uso sea extremadamente rápida, tanto el widget de la Control Room como la pantalla del Central Hub admiten **navegación completa mediante teclado**. ¡No es necesario tocar el ratón!

### 🗺️ Cambiar de Sección
* **`Flecha Derecha (→)`**: Cuando estés en la barra lateral (lista de listas), presiona la flecha derecha para saltar directamente al primer elemento de la lista seleccionada.
* **`Flecha Izquierda (←)`**: Cuando estés en la lista de elementos, presiona la flecha izquierda para volver a la barra lateral de listas.
* **`Flecha Arriba (↑)` en el primer elemento**: Si estás navegando por los elementos y te encuentras en el primero de la lista, al presionar la flecha arriba volverás automáticamente a enfocar la lista activa en la barra lateral.

### 🗂️ Navegar y Gestionar Listas (Barra Lateral)
* **`Flecha Arriba (↑)` / `Flecha Abajo (↓)`**: Desplázate verticalmente por tus listas.
* **`Enter` / `Espacio`**: Selecciona y abre la lista enfocada. El foco se moverá automáticamente al primer elemento para que puedas empezar a trabajar de inmediato.

### 📝 Navegar y Gestionar Elementos
* **`Flecha Arriba (↑)` / `Flecha Abajo (↓)`**: Desplázate por la lista de elementos dentro de la lista abierta.
* **`Espacio` / `Enter`**: Marca el elemento seleccionado como completado (tachado) o desmárcalo. *(Solo funciona si no estás editando el texto del elemento)*.
* **`Supr (Delete)` / `Retroceso (Backspace)`**: Elimina definitivamente el elemento seleccionado. *(Solo funciona si no estás editando)*.

---

## 📅 Seguimiento Automático de Fechas

Hecos registra automáticamente las fechas importantes para ayudarte a realizar un seguimiento de tu historial de actividades y evaluar la productividad:

* **Fecha de Creación de la Lista**: Se guarda automáticamente en el momento en que creas una nueva lista.
* **Fecha de Creación del Elemento**: Se registra para cada elemento individual añadido a una lista.
* **Fecha de Finalización**: Cuando marcas un elemento como completado, Hecos almacena la fecha y hora exactas de finalización. Si reactivas el elemento, la fecha de finalización se borra.

### 🔍 Dónde Visualizar las Fechas
Dependiendo del espacio en pantalla, las fechas se muestran de dos formas diferentes:
* **En el Central Hub (Pantalla Completa)**: Las fechas son visibles directamente en texto claro. La fecha de creación de la lista aparece junto a su nombre en la barra lateral. Para los elementos, las fechas de creación y de posible finalización se muestran debajo de cada fila de elementos.
* **En el Widget de la Control Room**: Debido al espacio reducido del widget, la información de las fechas aparece convenientemente en forma de **tooltip** (un cuadro de diálogo informativo) cuando pasas el ratón sobre el nombre de una lista o sobre un elemento.

---

## 💾 Exportación e Importación de Listas

Puedes exportar tus listas para usarlas en otro lugar o compartirlas. Hecos admite la exportación en tres formatos: **YAML**, **Texto Plano (.txt)** y **Markdown (.md)**.

> [!NOTE]
> **Nomenclatura Automática**: Para ayudarte a reconocer fácilmente tus archivos en el ordenador, cada exportación se guarda automáticamente con el prefijo `hecos_list_` seguido del nombre de la lista (por ejemplo: `hecos_list_desarrollo.yaml`).

### Trazabilidad de Versión y Fechas
Toda la información histórica se mantiene fielmente durante la exportación:
* **Compatibilidad**: En la parte superior del archivo se inserta un comentario que especifica el software y la versión exacta de Hecos utilizada para generarlo (ej. `# List created with Hecos v-0.30.0` en inglés por razones de estandarización).
* **Fechas incluidas**: Las fechas de creación y finalización se escriben y conservan en todos los formatos exportados, lo que garantiza que no se pierdan los datos históricos al trabajar fuera de la aplicación.
