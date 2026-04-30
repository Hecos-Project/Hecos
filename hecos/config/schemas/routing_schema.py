from pydantic import BaseModel
from typing import Dict

class RoutingOverrides(BaseModel):
    """
    Schema for central routing overrides managed in routing_overrides.yaml.
    Priority: User Override > Plugin Manifest > Core Default.
    """
    overrides: Dict[str, str] = {}
