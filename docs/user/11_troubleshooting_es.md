# 🛠️ 11. Resolución de Problemas

Si encuentras dificultades, sigue estos pasos rápidos para restaurar el funcionamiento correcto de Zentra Core.

- **Reinicio de Consola**: Si la interfaz de terminal parece congelada, intenta presionar `CTRL+C` para forzar la parada y reiniciar el programa.
- **Problemas de Audio**: Verifica que el micrófono esté seleccionado correctamente en el panel **F7** bajo `AUDIO`. Si usas la WebUI, asegúrate de haber aceptado los certificados de seguridad Zentra PKI.
- **Errores de Backend de IA**: Asegúrate de que Ollama o tu proveedor en la nube estén activos y accesibles.
- **Bucle de Activación de Audio:** Ajusta el `Energy Threshold` en **F7 → Listening** para calibrar el ruido de fondo.

### 🆘 Panel de Mantenimiento y Reparación
Si experimentas problemas con las rutas (ej. Piper no encontrado) o necesitas gestionar el servicio en segundo plano:
1. Abre el **Panel de Control de Zentra** (F7 o `/zentra/config/ui`).
2. Ve a la pestaña **Ayuda**.
3. Localiza la sección **🔧 MANTENIMIENTO Y REPARACIÓN**.
4. Desde aquí puedes ejecutar un **Chequeo Completo del Sistema**, **Arreglar Rutas Corruptas** o **Desinstalar el Servicio**.

- **Logs del Sistema**: Para problemas persistentes, consulta los archivos en la carpeta `logs/` para un análisis detallada.
