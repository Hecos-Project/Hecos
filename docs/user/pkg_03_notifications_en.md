# 🔔 Notifications Center

The **Notifications Center** module in Hecos is a powerful, plugin-driven event router. It acts as the central hub for dispatching alerts when important system events occur (e.g., system boot, errors, task completions, or failed logins). It delegates the actual delivery of messages to installed provider plugins like **MAIL** or **MESSENGER**, meaning it requires no credentials of its own.

---

## 🛠️ Key Features

1. **Event Routing**: Binds system events to specific destinations.
2. **Multi-Account Support**: Automatically selects the correct sender account or falls back to the global default.
3. **Smart Templating**: Send plain text alerts or rich HTML templates with variables.
4. **LLM Integration**: Fully manageable via AI chat using natural language.
5. **Direct Commands (HDCS)**: Native slash commands for quick, direct interaction from the chat interface.

---

## 📝 Available System Events

The Notifications Center can listen to and route the following built-in events:
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

## 🤖 AI and Direct Commands (HDCS)

You can manage your notification rules and destinations completely through the chat interface using natural language, or by using the precise **Direct Commands**.

### Direct Commands

Type these shortcuts in the chat to immediately trigger the Notifications Center:

* **`/notify`**: The main management command. You can use it to instruct the AI on what to do.
  * *Example*: `/notify list rules`
  * *Example*: `/notify add a new email destination for john@example.com`
  * *Example*: `/notify bind system_error to john_email`
  
* **`/alert`**: Instantly sends an ad-hoc notification to all your configured destinations (or a specific one).
  * *Example*: `/alert The system backup has finished successfully!`

### Natural Language Examples

Because all 8 core tools are exposed to the LLM, you don't even need slash commands if you prefer to converse naturally:
> *"Who receives notifications right now?"*
> *"Stop sending notifications to Marco when the system boots."*
> *"Create a new destination for Telegram and link it to flow_failed."*
> *"Send a test notification saying 'Hello World'."*

---

## ⚙️ Configuration via WebUI

If you prefer a graphical interface, the Notifications Center provides a dedicated configuration panel in the **Package Manager**:

1. Open the **Central Hub** and go to **Packages**.
2. Click the gear icon (⚙️) next to **Notifications Center**.
3. **Destinations**: Add, edit, or remove recipients (Email addresses, Contacts, or Messenger IDs).
4. **Event Rules**: Use the intuitive dropdowns to bind your destinations to specific system events.
5. **Templates**: Assign HTML templates to events for beautiful, customized alert emails.

---

## 📋 Notification History

Every notification dispatched by the system is recorded in the **Notification History** tab within the configuration panel. 
The history is neatly grouped by date (with expandable/collapsible accordions) and displays the recipient, the subject, and the exact timestamp of delivery.
