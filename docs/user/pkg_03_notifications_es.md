# 🔔 Notifications Center

El módulo **Notifications Center** (Centro de Notificaciones) en Hecos es un potente enrutador de eventos impulsado por complementos. Actúa como el núcleo central para el envío de alertas cuando ocurren eventos importantes en el sistema (por ejemplo, arranque del sistema, errores, finalización de tareas o inicios de sesión fallidos). Delega la entrega real de mensajes a los complementos instalados, como **MAIL** o **MESSENGER**, lo que significa que no requiere credenciales propias.

---

## 🛠️ Características Principales

1. **Enrutamiento de Eventos**: Vincula eventos del sistema a destinos específicos.
2. **Soporte Multicuenta**: Selecciona automáticamente la cuenta del remitente correcta o utiliza la predeterminada global.
3. **Plantillas Inteligentes**: Envía alertas de texto sin formato o ricas plantillas HTML con variables.
4. **Integración con IA**: Completamente manejable a través del chat utilizando lenguaje natural.
5. **Comandos Directos (HDCS)**: Comandos rápidos nativos (slash commands) para una interacción rápida desde la interfaz de chat.

---

## 📝 Eventos de Sistema Disponibles

El Centro de Notificaciones puede escuchar y enrutar los siguientes eventos incorporados:
- `system_boot`
- `system_shutdown`
- `system_error`
- `flow_started`
- `flow_completed`
- `flow_failed`
- `package_installed`
- `package_updated`
- `package_removed`
- `security_login_failed`
- `security_new_device`
- `backup_started`
- `backup_completed`
- `backup_failed`
- `custom`

---

## 🤖 Inteligencia Artificial y Comandos Directos (HDCS)

Puedes administrar tus reglas de notificación y destinos completamente a través de la interfaz de chat usando lenguaje natural, o mediante los precisos **Comandos Directos**.

### Comandos Directos

Escribe estos atajos en el chat para activar inmediatamente el Centro de Notificaciones:

* **`/notify`**: El comando de gestión principal. Puedes usarlo para instruir a la IA sobre qué hacer.
  * *Ejemplo*: `/notify listar reglas`
  * *Ejemplo*: `/notify agregar un nuevo destino de correo para juan@example.com`
  * *Ejemplo*: `/notify vincular system_error a correo_juan`
  
* **`/alert`**: Envía instantáneamente una notificación ad hoc a todos los destinos configurados (o a uno específico).
  * *Ejemplo*: `/alert ¡La copia de seguridad del sistema ha finalizado con éxito!`

### Ejemplos en Lenguaje Natural

Debido a que las 8 herramientas principales están expuestas a la IA, ni siquiera necesitas comandos directos si prefieres conversar de forma natural:
> *"¿Quién recibe las notificaciones ahora mismo?"*
> *"Deja de enviar notificaciones a Marcos cuando el sistema se inicie."*
> *"Crea un nuevo destino para Telegram y vincúlalo a flow_failed."*
> *"Envía una notificación de prueba que diga 'Hola Mundo'."*

---

## ⚙️ Configuración a través de WebUI

Si prefieres una interfaz gráfica, el Centro de Notificaciones proporciona un panel de configuración dedicado en el **Package Manager**:

1. Abre el **Central Hub** y ve a **Packages**.
2. Haz clic en el ícono de engranaje (⚙️) junto a **Notifications Center**.
3. **Destinos**: Agrega, edita o elimina destinatarios (direcciones de correo electrónico, contactos o ID de Messenger).
4. **Reglas de Eventos**: Usa los menús desplegables intuitivos para vincular tus destinos a eventos específicos del sistema.
5. **Plantillas**: Asigna plantillas HTML a los eventos para alertas hermosas y personalizadas.

---

## 📋 Historial de Notificaciones (History)

Cada notificación enviada por el sistema se registra en la pestaña **Notification History** dentro del panel de configuración. 
El historial está cuidadosamente agrupado por fecha (con secciones que se pueden expandir/contraer) y muestra el destinatario, el asunto y la marca de tiempo exacta de la entrega.
