# 🪐 Hecos Wiki Maintenance

This guide explains how to keep the official GitHub Wiki synchronized with the project's internal documentation.

## 🚀 Quick Update
To update the public Wiki after making changes to the documentation files:

1. **Open PowerShell** in the project root.
2. **Run the deployment script**:
   ```powershell
   .\scripts\Auto-Wiki-Deploy.ps1
   ```
   *(Note: By default, it looks for the Wiki repo at `C:\Hecos-Core-Wiki`. If yours is elsewhere, use `.\scripts\Auto-Wiki-Deploy.ps1 -WikiPath "D:\your\path"`)`*

## 📁 File Structure
- **Source**: All markdown files in `docs/user/` and `docs/tech/`.
- **Navigation**: The sidebar is managed via `docs/_Sidebar.md`. **Edit this file** to change the Wiki menu structure.
- **Archive**: Original Wiki assets are located in the `Hecos-Core-Wiki` repository.

## ⚠️ Important Rules
1. **Always edit in the main repo**: Do not edit the Wiki directly on the GitHub web interface, as those changes will be overwritten by the next sync.
2. **Commit Often**: The script automatically adds a timestamp to the commit message for tracking.
3. **Sidebar Hub**: The `_Sidebar.md` in `docs/` is the authoritative source for the Wiki menu.

---
*Maintained by the Hecos Development Team*
