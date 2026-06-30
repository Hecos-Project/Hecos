# 🌐 Hecos Proxy

> *"An integrated local routing proxy to bypass restrictions and securely connect your modules to the web."*

The **Hecos Proxy** is a specialized backend module integrated directly into the WebUI infrastructure. It acts as a secure middleman between your local Hecos instance and the external internet.

## Why is it needed?
Modern web browsers enforce strict security rules (like CORS - Cross-Origin Resource Sharing) that prevent a local web page (`localhost`) from fetching data directly from external APIs. 
For example, if a Weather Widget running in your Control Room tries to fetch data from a weather API, the browser might block the request.

## How it works
Instead of widgets making requests directly to external sites, they send the request to the local Hecos Proxy:
`http://localhost:5000/api/proxy?url=https://external-api.com`

The Hecos backend (Python) then fetches the data securely and hands it back to the WebUI widget, completely bypassing browser CORS restrictions.

## Features
- **CORS Bypass:** Essential for dynamic widgets that need to pull live data from the internet.
- **Secure Routing:** Hecos sanitizes and controls outgoing proxy requests.
- **Authentication Injection:** The proxy can be configured to securely inject your API keys into requests without ever exposing them to the frontend browser (preventing leaks).
