# 🌐 Hecos Proxy

> *"Un proxy de enrutamiento local integrado para evitar restricciones y conectar de forma segura tus módulos a la web."*

El **Hecos Proxy** es un módulo backend especializado integrado directamente en la infraestructura de la WebUI. Actúa como un intermediario seguro entre tu instancia local de Hecos y el internet externo.

## ¿Para qué sirve?
Los navegadores web modernos aplican reglas de seguridad estrictas (como CORS - Intercambio de Recursos de Origen Cruzado) que impiden que una página web local (`localhost`) obtenga datos directamente de las API externas.
Por ejemplo, si un Widget del Clima que se ejecuta en tu Control Room intenta obtener datos de una API meteorológica, el navegador podría bloquear la solicitud.

## Cómo funciona
En lugar de que los widgets realicen solicitudes directamente a sitios externos, envían la solicitud al Hecos Proxy local:
`http://localhost:5000/api/proxy?url=https://external-api.com`

El backend de Hecos (Python) obtiene entonces los datos de forma segura y se los devuelve al widget de la WebUI, evitando por completo las restricciones CORS del navegador.

## Características
- **Omisión de CORS:** Esencial para widgets dinámicos que necesitan extraer datos en vivo de Internet.
- **Enrutamiento Seguro:** Hecos desinfecta y controla las solicitudes proxy salientes.
- **Inyección de Autenticación:** El proxy se puede configurar para inyectar de forma segura tus claves de API en las solicitudes sin exponerlas nunca al navegador frontend (evitando fugas).
