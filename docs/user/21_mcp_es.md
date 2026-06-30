# 🔌 Universal Tool Hub (MCP Bridge)
Transforma Hecos en una superpotencia multi-herramienta conectando servidores externos a través del **Model Context Protocol**.

## ¿Qué es MCP?
El Model Context Protocol (MCP) es un estándar que permite a los agentes de IA conectarse de forma segura a herramientas externas como:
- **Búsqueda Web**: Brave Search, Google Search.
- **Herramientas de Desarrollo**: GitHub, GitLab, Terminal.
- **Bases de Datos**: PostgreSQL, SQLite.
- **Conocimiento**: Google Maps, Wikipedia.

## Configuración
Ve a **Configuración -> MCP Bridge** para gestionar tus servidores.
- **Presets**: Elige de una lista de servidores populares para una configuración rápida.
- **Servidores Personalizados**: Añade los tuyos especificando el comando (normalmente `npx`) y los argumentos.
- **Auto-Descubrimiento**: Hecos escanea automáticamente los servidores conectados y lista las herramientas disponibles en tiempo real.

## 🔎 Descubrimiento Multi-Registro
Hecos facilita la búsqueda de nuevas herramientas sin salir de la aplicación. Ve a la pestaña **Discovery** del MCP Bridge para buscar en múltiples registros:
- **Smithery.ai**: Explora miles de servidores MCP verificados por la comunidad.
- **MCPSkills**: Descubre agentes y conjuntos de herramientas especializados.
- **GitHub**: Instala directamente servidores alojados en repositorios de GitHub.
- **Hugging Face**: Accede a herramientas y modelos listos para la IA.

Simplemente haz clic en **"Install"** en cualquier herramienta descubierta, y Hecos gestionará automáticamente la configuración del entorno.

## Uso de Herramientas MCP
Una vez que un servidor esté conectado y aparezca como "connected" en el inventario:
1. La IA detectará automáticamente las nuevas capacidades.
2. Puedes pedir a Hecos que realice acciones como "Busca en Brave" o "Revisa mis issues de GitHub".
3. Hecos enrutará la solicitud al servidor MCP externo y devolverá los resultados.
