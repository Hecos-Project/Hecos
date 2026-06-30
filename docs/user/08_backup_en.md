# 💾 Centralized Backup

> *"A one-click solution to safely store your entire Hecos configuration and memories."*

The **Centralized Backup** is a core module of the Hecos WebUI designed to give you peace of mind. Since Hecos runs entirely locally and saves your data on your own hard drive, it is crucial to have an easy way to back up your system.

## What it backs up
When you trigger a Centralized Backup, Hecos packages the following into a single compressed archive:
- **`config/`**: All your custom settings, API keys, and system parameters.
- **`workspace/`**: Your flows, personas, and custom data.
- **`memory/`**: The SQLite database containing all your chat histories (Episodic Memory Vault).
- **`plugins/`**: Any custom or downloaded packages you have installed.

## How to use it
1. Open the **Central Hub** (F7).
2. Navigate to the **System** or **Data** category (depending on your layout).
3. Click the **Generate Backup** button.
4. Hecos will compile the ZIP file in the background and automatically start the download through your browser.

## Restoration
To restore a backup, simply extract the downloaded ZIP archive over your existing Hecos installation folder, overwriting the existing folders. Your system will return exactly to the state it was in at the time of the backup.
