/* cmd_search.js — HDCS Palette Search Engine */

export async function fetchAllCommands() {
    try {
        const res = await fetch('/api/commands/list');
        const data = await res.json();
        return data.ok ? data.commands : [];
    } catch (e) {
        console.error("HDCS fetch error:", e);
        return [];
    }
}

export function filterCommands(commands, query) {
    if (!query) return commands;
    
    // Check if query looks like a specific command being typed (e.g. "/img foto")
    // If it has a space, we match the first part exactly
    const parts = query.split(' ');
    const searchWord = parts[0].toLowerCase();
    
    const isCommandTyped = query.startsWith('/') && parts.length > 1;

    return commands.filter(cmd => {
        // If a full command with arguments is typed, only show that exact command
        if (isCommandTyped) {
            return cmd.aliases.some(a => a.toLowerCase() === searchWord);
        }
        
        // Otherwise do a fuzzy search
        const q = query.toLowerCase().replace('/', '');
        const haystack = [
            cmd.id,
            ...cmd.aliases,
            cmd.description,
            cmd.category
        ].join(' ').toLowerCase();
        
        return haystack.includes(q);
    });
}
