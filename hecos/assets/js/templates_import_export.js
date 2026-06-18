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
  }

});
