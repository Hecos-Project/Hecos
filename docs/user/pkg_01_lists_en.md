# u{1F4CB} Lists Management

The Hecos **Lists** module is the ideal tool to organize your tasks, notes, shopping lists, or development tasks directly within the ecosystem. It is designed to be lightweight, accessible, and fast, offering both a full-screen Hub view and a practical widget for your Control Room.

---

## 📋 Where to Find Lists

You can access lists management in two different ways within the WebUI:

1. **Central Hub (Main Panel)**: Click on "Lists" in the left sidebar menu of the Central Hub. This full-screen view features a sidebar displaying all your lists and an extended central area to manage item details.
2. **Control Room Widget**: You can add the lists widget to your Control Room (the dashboard with a flexible grid). It is perfect for keeping an eye on your tasks while monitoring other modules of the system.

---

## ⌨️ Keyboard Navigation (Keyboard Shortcuts)

To ensure a lightning-fast experience, both the Control Room widget and the Central Hub view support **full keyboard navigation**. No mouse required!

### 🗺️ Switching Focus Between Sections
* **`Right Arrow (→)`**: When focusing the sidebar (list of lists), press the right arrow to jump directly to the first item of the selected list.
* **`Left Arrow (←)`**: When focusing the item list, press the left arrow to return to the sidebar lists.
* **`Up Arrow (↑)` on the first item**: If you are navigating the items and are on the first item in the list, pressing the up arrow will automatically return focus to the active list in the sidebar.

### 🗂️ Navigating and Managing Lists (Sidebar)
* **`Up Arrow (↑)` / `Down Arrow (↓)`**: Scroll vertically through your lists.
* **`Enter` / `Space`**: Select and open the highlighted list. The focus will automatically shift to the first item in the list so you can start working immediately.

### 📝 Navigating and Managing Items
* **`Up Arrow (↑)` / `Down Arrow (↓)`**: Scroll through the list of items in the currently opened list.
* **`Space` / `Enter`**: Toggle the selected item's status (check/uncheck). *(Only works when you are not currently editing the item's text)*.
* **`Delete` / `Backspace`**: Permanently delete the selected item. *(Only works when you are not currently editing)*.

---

## 📅 Automatic Date Tracking

Hecos automatically records important dates to help you track your activity history and evaluate productivity:

* **List Creation Date**: Automatically saved when you create a new list.
* **Item Creation Date**: Recorded for every single item added to a list.
* **Completion Date**: When you check off an item, Hecos records the exact timestamp of completion. If you reactivate the item, the completion date is cleared.

### 🔍 Viewing Dates
Depending on screen space, dates are rendered differently across the interfaces:
* **In the Central Hub (Full Screen)**: Dates are displayed inline. The creation date of the list appears next to its name in the sidebar. For items, creation and completion dates are displayed directly below each item's text.
* **In the Control Room Widget**: Due to limited space, date information appears as a **tooltip** when you hover the mouse over a list's name or an item.

---

## 💾 Exporting and Importing Lists

You can export your lists for backup or external use. Hecos supports exporting in three formats: **YAML**, **Plain Text (.txt)**, and **Markdown (.md)**.

> [!NOTE]
> **Automatic Naming**: To help you easily identify list files on your computer, every exported file is automatically saved with the prefix `hecos_list_` followed by the list name (e.g., `hecos_list_development.yaml`).

### Version & Date Tracking
All historical information is preserved during export:
* **Compatibility**: A comment is prepended to the exported file specifying the software and version of Hecos used to create it (e.g., `# List created with Hecos v-0.30.0`).
* **Preserved Dates**: Creation and completion dates are written and preserved in all exported formats, ensuring your historical data is kept when working outside the application.
