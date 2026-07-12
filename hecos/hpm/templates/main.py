"""
MODULE: Templates Plugin — Main Entry Point
DESCRIPTION: Exposes TemplateTools to the Hecos agent loop.
             Allows the LLM to discover and render templates.
"""

from __future__ import annotations
import json
from typing import Optional

from .store import list_templates, render_template

class TemplateTools:
    """
    Hecos Templates Plugin — find and render message templates.
    """

    def __init__(self):
        self.tag    = "TEMPLATES"
        self.desc   = "Find and render predefined templates for emails and messages."
        self.status = "ONLINE"

    def list_templates(self, channel: Optional[str] = None) -> str:
        """
        List all available templates.
        :param channel: Optional channel filter (e.g. 'whatsapp', 'email', 'telegram', 'discord').
        """
        all_tpls = list_templates(channel=channel)
        if not all_tpls:
            return "❌ Nessun template trovato."
        
        lines = ["📝 **Template Disponibili:**"]
        for t in all_tpls:
            default_marker = " [DEFAULT]" if t.get("is_default") else ""
            vars_str = ", ".join(t.get("variables", []))
            lines.append(f"- ID: {t['id']} | Nome: {t['name']} | Canale: {t['channel']}{default_marker}")
            if vars_str:
                lines.append(f"  Variabili richieste: {vars_str}")
            if t.get("description"):
                lines.append(f"  Desc: {t['description']}")
            
        return "\n".join(lines)

    def render_template(self, template_id_or_name: str, variables: str) -> str:
        """
        Render a template by replacing its variables and combining header/body/footer.
        Use this before sending a message if you want to use a specific template.
        :param template_id_or_name: The ID or the exact Name of the template.
        :param variables: A JSON string containing the variables to inject (e.g. '{"nome": "Mario"}').
        """
        all_tpls = list_templates()
        
        # Find template by ID or exact Name (case-insensitive)
        target = None
        for t in all_tpls:
            if t["id"] == template_id_or_name or t["name"].lower() == template_id_or_name.lower():
                target = t
                break
                
        if not target:
            return f"❌ Template '{template_id_or_name}' non trovato."
            
        try:
            vars_dict = json.loads(variables) if variables else {}
        except json.JSONDecodeError:
            return "❌ Errore nel parse JSON delle variabili."
            
        rendered = render_template(target, vars_dict)
        
        if target["channel"] == "email":
            return f"OGGETTO: {rendered.get('subject', '')}\n\n{rendered.get('body_text', '')}"
        
        # Messenger channels
        parts = []
        if rendered.get("header"):
            parts.append(rendered["header"])
        if rendered.get("body_text"):
            parts.append(rendered["body_text"])
        if rendered.get("footer"):
            parts.append(rendered["footer"])
            
        return "\n\n".join(parts)
