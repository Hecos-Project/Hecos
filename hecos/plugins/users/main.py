"""
MODULE: User Profile Tool - Hecos
DESCRIPTION: Provides AI tools to access and update the user's profile information on demand.
             This enables 'Lazy Load' optimization, reducing system prompt token overhead.
"""
from hecos.core.auth.auth_manager import auth_mgr
from hecos.core.logging import logger
from hecos.core.i18n import translator

class UserTools:
    def __init__(self):
        self.tag = "USERS"
        self.icon = "👥"
        self.desc = "Gestione informazioni utente e preferenze"
        self.esempio = "[USERS: get_profile]"

    def get_profile(self, username="admin"):
        """
        Retrieves the full profile of a user, including contact details and bio.
        Use this tool when you need to know the user's email, phone, or address.
        :param username: The username to retrieve (default: 'admin').
        """
        try:
            profile = auth_mgr.get_profile(username)
            if not profile:
                return f"No profile found for user '{username}'."
            
            # Format nicely for the LLM
            res = f"### PROFILE: {username} ###\n"
            for k, v in profile.items():
                val = v if v else "[not provided]"
                res += f"- {k}: {val}\n"
            return res
        except Exception as e:
            logger.error(f"[USER_PLUGIN] Error in get_profile: {e}")
            return f"Error retrieving profile: {e}"

    def update_profile(self, username="admin", **fields):
        """
        Updates one or more fields in the user's profile.
        Available fields: display_name, email, phone, address, city, bio_notes, preferred_language,
                          real_name, age, birthday, height, weight,
                          family_parents, family_siblings, family_partner, pets,
                          family_children, family_grandchildren,
                          education, title, gender, orientation, interests, extra_notes,
                          job_main, job_secondary.
        :param username: The username to update (default: 'admin').
        :param fields: Key-value pairs of fields to update.
        """
        if not fields:
            return "No fields provided for update."
            
        try:
            success = auth_mgr.update_profile(username, fields)
            if success:
                # If language was updated, sync it immediately
                if "preferred_language" in fields:
                    translator.set_language(fields["preferred_language"])
                    
                return f"Successfully updated profile for '{username}': {', '.join(fields.keys())}."
            else:
                return f"Failed to update profile for '{username}'. Field might not be in whitelist."
        except Exception as e:
            logger.error(f"[USER_PLUGIN] Error in update_profile: {e}")
            return f"Error updating profile: {e}"

    def status(self):
        return translator.t("online")

# Interface for the Hecos Plugin Loader
tools = UserTools()

def info():
    return {
        "tag": tools.tag,
        "desc": tools.desc,
        "icon": "👥",
        "esempio": tools.esempio,
        "comandi": {
            "get_profile": "Ottiene i dettagli completi del profilo (email, telefono, etc.)",
            "update_profile": "Aggiorna i campi del profilo utente"
        }
    }
