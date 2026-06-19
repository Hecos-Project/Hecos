/**
 * Template Import/Export Logic
 * Extends the TemplateManager namespace
 */

Object.assign(TemplateManager, {
  
  async exportTemplates() {
    try {
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast('Preparing export...', 'info');
      }

      const res = await fetch('/api/templates/export');
      if (!res.ok) throw new Error('Failed to export templates');
      
      const data = await res.json();
      if (!data.templates) throw new Error('Invalid export format');

      const defaultFilename = `hecos_templates_backup_${new Date().toISOString().split('T')[0]}.json`;
      const content = JSON.stringify(data, null, 2);

      if (window.showSaveFilePicker) {
        try {
          const fileHandle = await window.showSaveFilePicker({
            suggestedName: defaultFilename,
            types: [{
              description: 'JSON Files',
              accept: { 'application/json': ['.json'] },
            }],
          });
          const writable = await fileHandle.createWritable();
          await writable.write(content);
          await writable.close();
        } catch (err) {
          // If user cancelled the save dialog, just return silently
          if (err.name === 'AbortError') return;
          throw err;
        }
      } else {
        // Fallback for browsers that do not support showSaveFilePicker
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = defaultFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
      
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast(`Exported ${data.count} templates successfully`, 'success');
      }
    } catch (err) {
      console.error('Export error:', err);
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast(err.message, 'error');
      } else {
        alert('Export error: ' + err.message);
      }
    }
  },

  async importTemplates(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Optional: Ask user if they want to Duplicate or Restore (overwrite)
    // For automated backups, we default to Restore. But here we can ask.
    let mode = 'restore';
    const msg = "Do you want to overwrite existing templates with the same ID? \n\n" +
                "OK = Restore exactly as backup (Overwrite)\n" +
                "Cancel = Import as Copies (Duplicate with 'v2' names)";
                
    if (!confirm(msg)) {
      mode = 'duplicate';
    }

    try {
      const text = await file.text();
      const payload = JSON.parse(text);
      
      if (!payload.templates || !Array.isArray(payload.templates)) {
        throw new Error("Invalid file format. 'templates' array not found.");
      }

      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast(`Importing ${payload.templates.length} templates...`, 'info');
      }

      const res = await fetch(`/api/templates/import?mode=${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ templates: payload.templates })
      });

      const result = await res.json();
      if (!result.ok) throw new Error(result.error || 'Import failed');

      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast(`Successfully imported ${result.imported_count} templates!`, 'success');
      }

      // Reload sidebar list
      await TemplateManager.init();
      
    } catch (err) {
      console.error('Import error:', err);
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast(err.message, 'error');
      } else {
        alert('Import error: ' + err.message);
      }
    } finally {
      // Reset input so the same file can be selected again
      event.target.value = '';
    }
  },

  async exportSingleTemplate() {
    const select = document.getElementById('tpl-single-export-select');
    if (!select || !select.value) {
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast('Please select a template to export first.', 'error');
      }
      return;
    }
    
    const templateId = select.value;
    try {
      const res = await fetch(`/api/templates/${templateId}`);
      if (!res.ok) throw new Error('Failed to fetch template');
      const data = await res.json();
      if (!data.template) throw new Error('Template not found');

      // The export format must match the import format: { templates: [ templateObj ] }
      const exportObj = {
        templates: [data.template],
        count: 1,
        exported_at: new Date().toISOString()
      };
      
      const safeName = (data.template.name || 'template').replace(/[^a-z0-9]/gi, '_').toLowerCase();
      const defaultFilename = `template_${safeName}.json`;
      const content = JSON.stringify(exportObj, null, 2);

      if (window.showSaveFilePicker) {
        try {
          const fileHandle = await window.showSaveFilePicker({
            suggestedName: defaultFilename,
            types: [{ description: 'JSON Files', accept: { 'application/json': ['.json'] } }]
          });
          const writable = await fileHandle.createWritable();
          await writable.write(content);
          await writable.close();
        } catch (err) {
          if (err.name === 'AbortError') return;
          throw err;
        }
      } else {
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = defaultFilename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
      
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast('Template exported successfully', 'success');
      }
    } catch (err) {
      console.error('Export single template error:', err);
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast(err.message, 'error');
      }
    }
  },

  async importSingleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over');
    if (event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files.length > 0) {
      const file = event.dataTransfer.files[0];
      await this._processSingleImportFile(file);
    }
  },

  async importSingleFile(event) {
    const file = event.target.files[0];
    if (!file) return;
    await this._processSingleImportFile(file);
    event.target.value = '';
  },

  async _processSingleImportFile(file) {
    try {
      const text = await file.text();
      const payload = JSON.parse(text);
      
      if (!payload.templates || !Array.isArray(payload.templates) || payload.templates.length === 0) {
        throw new Error("Invalid file format. Ensure this is a valid Template JSON file.");
      }

      // Single import logic always imports as duplicate (new ID) to prevent breaking existing ones
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast('Importing template...', 'info');
      }

      const res = await fetch(`/api/templates/import?mode=duplicate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ templates: payload.templates })
      });

      const result = await res.json();
      if (!result.ok) throw new Error(result.error || 'Import failed');

      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast(`Template imported successfully!`, 'success');
      }

      await TemplateManager.init();
    } catch (err) {
      console.error('Single import error:', err);
      if (typeof window.ui !== 'undefined' && window.ui.showToast) {
        ui.showToast(err.message, 'error');
      } else {
        alert('Import error: ' + err.message);
      }
    }
  }

});
