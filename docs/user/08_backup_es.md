# 💾 9. Copia de Seguridad Centralizada

> *"Una solución de un solo clic para almacenar de forma segura toda tu configuración y memorias de Hecos."*

La **Copia de Seguridad Centralizada** (Backup Centralizado) es un módulo central de la WebUI de Hecos diseñado para darte tranquilidad. Dado que Hecos se ejecuta de forma completamente local y guarda tus datos en tu propio disco duro, es crucial tener una forma fácil de hacer una copia de seguridad del sistema.

## Qué se guarda
Cuando activas una Copia de Seguridad Centralizada, Hecos empaqueta lo siguiente en un solo archivo comprimido:
- **`config/`**: Todas tus configuraciones personalizadas, claves de API y parámetros del sistema.
- **`workspace/`**: Tus flujos, personalidades (personas) y datos personalizados.
- **`memory/`**: La base de datos SQLite que contiene todos tus historiales de chat (Episodic Memory Vault).
- **`plugins/`**: Cualquier paquete personalizado o descargado que hayas instalado.

## Cómo usarlo
1. Abre el **Central Hub** (F7).
2. Navega a la categoría **Sistema** o **Datos** (dependiendo de tu diseño).
3. Haz clic en el botón **Generar Copia de Seguridad**.
4. Hecos compilará el archivo ZIP en segundo plano e iniciará automáticamente la descarga a través de tu navegador.

## Restauración
Para restaurar una copia de seguridad, simplemente extrae el archivo ZIP descargado sobre tu carpeta de instalación de Hecos existente, sobrescribiendo las carpetas actuales. Tu sistema volverá exactamente al estado en el que estaba en el momento de la copia de seguridad.
