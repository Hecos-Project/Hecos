import json
from typing import Dict, Any, List
from hecos.core.logging import logger

def analyze_goal_and_plan(goal: str, installed_modules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes a high level goal against currently installed modules.
    Returns a plan structure detailing what can be done immediately 
    and what modules are missing.
    """
    # In a full implementation, this might call the LLM internally to map goal -> required capabilities -> missing modules.
    # For now, it provides a structured response format that the LLM can interpret and fill in.
    
    installed_ids = [m.get("id") for m in installed_modules]
    
    plan = {
        "goal": goal,
        "status": "ready",
        "missing_capabilities": [],
        "proposed_flow_steps": []
    }
    
    # Very basic mock analysis
    if "weather" in goal.lower() and "weather_app" not in installed_ids:
        plan["status"] = "missing_modules"
        plan["missing_capabilities"].append("weather_data")
        
    if "email" in goal.lower() and "email_client" not in installed_ids:
        plan["status"] = "missing_modules"
        plan["missing_capabilities"].append("email_sending")
        
    return plan
