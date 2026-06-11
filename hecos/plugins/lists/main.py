"""
MODULE: Lists Plugin — LLM Tools
DESCRIPTION: Exposes lists management tools to the Hecos agent loop.
"""

from hecos.core.logging import logger

try:
    from hecos.core.i18n import translator
except ImportError:
    class _DummyTranslator:
        def t(self, key, **kwargs): return key
    translator = _DummyTranslator()

from hecos.plugins.lists import store

class LISTSTools:
    """Hecos Lists plugin — exposes all list management LLM tools."""

    def __init__(self, config=None):
        self._cfg = config
        self.tag = "LISTS"
        self.desc = "Universal List Manager plugin"
        self.status = "ONLINE"

        self.slash_commands = [
            {
                "id": "lists",
                "aliases": ["/list", "/lists", "/liste"],
                "description": "Mostra tutte le liste attive",
                "usage": "/list",
                "example": "/list",
                "icon": "📋",
                "method": "list_lists",
                "args_schema": {},
                "requires_args": False,
            },
            {
                "id": "list_show",
                "aliases": ["/list show", "/lista"],
                "description": "Mostra il contenuto di una lista",
                "usage": "/lista <nome_lista>",
                "example": "/lista Spesa",
                "icon": "🔍",
                "method": "show_list",
                "args_schema": {"list_name": "str"},
                "requires_args": True,
            },
            {
                "id": "list_add",
                "aliases": ["/list add", "/lista aggiungi"],
                "description": "Aggiunge un elemento a una lista",
                "usage": "/list add <nome_lista> <elemento>",
                "example": "/list add Spesa Uova",
                "icon": "➕",
                "method": "add_to_list",
                "args_schema": {"list_name": "str", "items": "str"},
                "requires_args": True,
            },
            {
                "id": "list_new",
                "aliases": ["/list new", "/lista nuova"],
                "description": "Crea una nuova lista",
                "usage": "/list new <nome_lista>",
                "example": "/list new Film da vedere",
                "icon": "📝",
                "method": "create_list",
                "args_schema": {"name": "str"},
                "requires_args": True,
            },
            {
                "id": "list_done",
                "aliases": ["/list done", "/lista spunta"],
                "description": "Segna un elemento come completato",
                "usage": "/list done <nome_lista> <elemento>",
                "example": "/list done Spesa Uova",
                "icon": "✅",
                "method": "check_item",
                "args_schema": {"list_name": "str", "item_text": "str"},
                "requires_args": True,
            }
        ]

        self.config_schema = {
            "default_icon": {
                "type": "str",
                "default": "📋",
                "description": "Default icon for new lists"
            },
            "show_completed": {
                "type": "bool",
                "default": True,
                "description": "If true, show_list returns completed items as well"
            }
        }

    # ── LLM Tools ─────────────────────────────────────────────────────────────

    def create_list(self, name: str, icon: str = "📋", color: str = None) -> str:
        """Creates a new list."""
        try:
            if store.get_list_by_name(name):
                return f"⚠️ Una lista con il nome '{name}' esiste già."
            
            lst = store.create_list(name=name, icon=icon, color=color)
            if lst:
                return f"✅ Lista **{icon} {name}** creata con successo."
            return f"⚠️ Errore durante la creazione della lista '{name}'."
        except Exception as e:
            logger.error(f"[LISTS] create_list error: {e}")
            return f"⚠️ Errore di sistema: {e}"

    def list_lists(self) -> str:
        """Returns all active lists."""
        try:
            lists = store.get_lists(include_archived=False)
            if not lists:
                return "📭 Non ci sono liste attive."
            
            lines = ["📋 **Le tue liste:**\n"]
            for lst in lists:
                count = lst.get("pending_count", 0)
                lines.append(f"• {lst['icon']} **{lst['name']}** ({count} elementi da fare)")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"[LISTS] list_lists error: {e}")
            return f"⚠️ Errore durante il recupero delle liste: {e}"

    def show_list(self, list_name: str) -> str:
        """Shows the content of a specific list."""
        try:
            lst = store.get_list_by_name(list_name)
            if not lst:
                return f"⚠️ Nessuna lista trovata con il nome '{list_name}'."
            
            items = store.get_items(lst['id'])
            if not items:
                return f"{lst['icon']} La lista **{lst['name']}** è vuota."
            
            lines = [f"{lst['icon']} **{lst['name']}**:\n"]
            for item in items:
                status_icon = "✅" if item['status'] == 'done' else "⬜"
                priority_mark = "!" * item['priority'] if item['priority'] > 0 else ""
                label_mark = f" [{item['label']}]" if item.get('label') else ""
                
                # Strike through if done
                text = f"~~{item['text']}~~" if item['status'] == 'done' else item['text']
                lines.append(f"{status_icon} {text}{priority_mark}{label_mark}")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"[LISTS] show_list error: {e}")
            return f"⚠️ Errore durante la lettura della lista: {e}"

    def add_to_list(self, list_name: str, items: str, priority: int = 0, label: str = None) -> str:
        """Adds one or more items to a list (separated by comma or newline)."""
        try:
            lst = store.get_list_by_name(list_name)
            if not lst:
                # auto create
                lst = store.create_list(name=list_name)
            
            # split items by comma or newline
            import re
            item_list = [i.strip() for i in re.split(r'[,\\n]+', items) if i.strip()]
            
            added = 0
            for item_text in item_list:
                if store.add_item(lst['id'], text=item_text, priority=priority, label=label):
                    added += 1
                    
            if added == 0:
                return f"⚠️ Nessun elemento aggiunto."
            return f"✅ Aggiunti {added} element{'o' if added == 1 else 'i'} alla lista **{lst['name']}**."
        except Exception as e:
            logger.error(f"[LISTS] add_to_list error: {e}")
            return f"⚠️ Errore durante l'aggiunta: {e}"

    def check_item(self, list_name: str, item_text: str) -> str:
        """Marks an item as completed."""
        try:
            lst = store.get_list_by_name(list_name)
            if not lst:
                return f"⚠️ Lista '{list_name}' non trovata."
            
            items = store.get_items(lst['id'], status_filter='pending')
            # fuzzy search
            target = None
            text_lower = item_text.lower()
            for item in items:
                if text_lower in item['text'].lower():
                    target = item
                    break
            
            if not target:
                return f"⚠️ Nessun elemento da fare trovato contenente '{item_text}' in '{list_name}'."
            
            if store.update_item(target['id'], status='done'):
                return f"✅ Completato: ~~{target['text']}~~"
            return "⚠️ Errore durante l'aggiornamento dell'elemento."
        except Exception as e:
            logger.error(f"[LISTS] check_item error: {e}")
            return f"⚠️ Errore di sistema: {e}"

    def uncheck_item(self, list_name: str, item_text: str) -> str:
        """Marks an item as pending."""
        try:
            lst = store.get_list_by_name(list_name)
            if not lst:
                return f"⚠️ Lista '{list_name}' non trovata."
            
            items = store.get_items(lst['id'], status_filter='done')
            target = None
            text_lower = item_text.lower()
            for item in items:
                if text_lower in item['text'].lower():
                    target = item
                    break
            
            if not target:
                return f"⚠️ Nessun elemento completato trovato contenente '{item_text}' in '{list_name}'."
            
            if store.update_item(target['id'], status='pending'):
                return f"🔄 Ripristinato: {target['text']}"
            return "⚠️ Errore durante l'aggiornamento."
        except Exception as e:
            logger.error(f"[LISTS] uncheck_item error: {e}")
            return f"⚠️ Errore di sistema: {e}"

    def remove_from_list(self, list_name: str, item_text: str) -> str:
        """Deletes an item from a list."""
        try:
            lst = store.get_list_by_name(list_name)
            if not lst:
                return f"⚠️ Lista '{list_name}' non trovata."
            
            items = store.get_items(lst['id'])
            target = None
            text_lower = item_text.lower()
            for item in items:
                if text_lower in item['text'].lower():
                    target = item
                    break
            
            if not target:
                return f"⚠️ Elemento non trovato."
            
            if store.delete_item(target['id']):
                return f"🗑️ Rimosso '{target['text']}' dalla lista {lst['name']}."
            return "⚠️ Errore durante la rimozione."
        except Exception as e:
            logger.error(f"[LISTS] remove_from_list error: {e}")
            return f"⚠️ Errore di sistema: {e}"

    def clear_done(self, list_name: str) -> str:
        """Removes all completed items from a list."""
        try:
            lst = store.get_list_by_name(list_name)
            if not lst:
                return f"⚠️ Lista '{list_name}' non trovata."
            
            count = store.clear_done_items(lst['id'])
            return f"🧹 Rimossi {count} elementi completati dalla lista {lst['name']}."
        except Exception as e:
            logger.error(f"[LISTS] clear_done error: {e}")
            return f"⚠️ Errore di sistema: {e}"

    def delete_list(self, list_name: str) -> str:
        """Deletes an entire list."""
        try:
            lst = store.get_list_by_name(list_name)
            if not lst:
                return f"⚠️ Lista '{list_name}' non trovata."
            
            if store.delete_list(lst['id']):
                return f"🗑️ Lista **{lst['name']}** eliminata."
            return "⚠️ Errore durante l'eliminazione."
        except Exception as e:
            logger.error(f"[LISTS] delete_list error: {e}")
            return f"⚠️ Errore di sistema: {e}"

    def archive_list(self, list_name: str) -> str:
        """Archives a list so it doesn't show up in normal views."""
        try:
            lst = store.get_list_by_name(list_name)
            if not lst:
                return f"⚠️ Lista '{list_name}' non trovata."
            
            if store.update_list(lst['id'], archived=1):
                return f"📦 Lista **{lst['name']}** archiviata."
            return "⚠️ Errore durante l'archiviazione."
        except Exception as e:
            logger.error(f"[LISTS] archive_list error: {e}")
            return f"⚠️ Errore di sistema: {e}"


# ── Singleton & Hooks ──────────────────────────────────────────────────────────
tools = LISTSTools()

def on_load(config):
    tools._cfg = config
    logger.debug("LISTS", "Plugin loaded.")
    
    # Register API blueprint if web_ui is available
    try:
        from hecos.core.system import module_scanner
        webui_mod = module_scanner.get_module_instance("WEB_UI")
        if webui_mod and hasattr(webui_mod, 'app'):
            from hecos.plugins.lists.api import register_routes
            register_routes(webui_mod.app)
    except Exception as e:
        logger.warning("LISTS", f"Could not register API routes: {e}")
