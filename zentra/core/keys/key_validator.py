"""
MODULE: core/keys/key_validator.py
DESCRIPTION: Implements provider-specific validation logic for API keys.
"""

import requests
import time
from zentra.core.logging import logger

def validate_key(provider: str, value: str) -> dict:
    """
    Validate an API key for a specific provider.
    Returns: {"valid": bool, "status": str, "message": str}
    """
    provider = provider.lower()
    
    try:
        if provider == "huggingface":
            return _validate_hf(value)
        elif provider == "gemini":
            return _validate_gemini(value)
        elif provider == "groq":
            return _validate_groq(value)
        elif provider == "openai":
            return _validate_openai(value)
        elif provider == "anthropic":
            return _validate_anthropic(value)
        
        # Generic check for custom providers (not supported yet)
        return {"valid": True, "status": "unknown", "message": f"Validation not implemented for {provider}"}
        
    except Exception as e:
        logger.error(f"[Validator] Unexpected error for {provider}: {e}")
        return {"valid": False, "status": "unknown", "message": f"Error: {str(e)}"}

def _validate_hf(key: str) -> dict:
    try:
        # 1. Base identity check
        url = "https://huggingface.co/api/whoami-v2"
        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(url, headers=headers, timeout=5)
        
        if r.status_code != 200:
            if r.status_code == 401:
                return {"valid": False, "status": "invalid", "message": "Unauthorized (bad token)"}
            return {"valid": False, "status": "unknown", "message": f"HTTP {r.status_code}"}
        
        data = r.json()
        name = data.get("name", "User")
        
        # 2. PROACTIVE INFERENCE CHECK (Check if key has access/quota for common models)
        # We check the status of a popular model. If exhausted, this often returns 429/403.
        test_model = "black-forest-labs/FLUX.1-schnell"
        status_url = f"https://api-inference.huggingface.co/status/{test_model}"
        r_status = requests.get(status_url, headers=headers, timeout=5)
        
        if r_status.status_code == 429:
            return {"valid": False, "status": "rate_limited", "message": "HF Quota Exhausted / Rate Limited"}
        elif r_status.status_code == 403:
            return {"valid": False, "status": "invalid", "message": "Key lacks Inference API permissions"}
            
        return {"valid": True, "status": "valid", "message": f"Connected as {name}"}
        
    except Exception as e:
        return {"valid": False, "status": "unknown", "message": f"Network Error: {str(e)}"}

def _validate_gemini(key: str) -> dict:
    try:
        # Simplest metadata call that doesn't consume usage for text generation
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200:
            return {"valid": True, "status": "valid", "message": "Key is active"}
        elif r.status_code == 400:
            return {"valid": False, "status": "invalid", "message": "Invalid API key"}
        elif r.status_code == 429:
            return {"valid": False, "status": "rate_limited", "message": "Rate limited / Quota exhausted"}
        else:
            return {"valid": False, "status": "unknown", "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"valid": False, "status": "unknown", "message": f"Network Error: {str(e)}"}

def _validate_groq(key: str) -> dict:
    try:
        url = "https://api.groq.com/openai/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            return {"valid": True, "status": "valid", "message": "Connection successful"}
        elif r.status_code == 401:
            return {"valid": False, "status": "invalid", "message": "Invalid Groq API Key"}
        elif r.status_code == 429:
            return {"valid": False, "status": "rate_limited", "message": "Rate limit / Credit exhausted"}
        else:
            return {"valid": False, "status": "unknown", "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"valid": False, "status": "unknown", "message": f"Network Error: {str(e)}"}

def _validate_openai(key: str) -> dict:
    try:
        url = "https://api.openai.com/v1/models"
        headers = {"Authorization": f"Bearer {key}"}
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            return {"valid": True, "status": "valid", "message": "Key is active"}
        elif r.status_code == 401:
            return {"valid": False, "status": "invalid", "message": "Invalid / Expired Token"}
        elif r.status_code == 429:
            return {"valid": False, "status": "rate_limited", "message": "Quota exceeded / Rate limit"}
        else:
            return {"valid": False, "status": "unknown", "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"valid": False, "status": "unknown", "message": f"Network Error: {str(e)}"}

def _validate_anthropic(key: str) -> dict:
    try:
        # Anthropic doesn't have a generic "whoami" but a dummy message works
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        # Send an empty/bad payload to just check auth
        r = requests.post(url, headers=headers, json={}, timeout=10)
        
        # 400 Bad Request with "invalid_request_error" means auth was OK but payload was bad (Good!)
        # if key is bad, it gives 401.
        if r.status_code == 400:
            data = r.json()
            if data.get("error", {}).get("type") == "invalid_request_error":
                return {"valid": True, "status": "valid", "message": "Key is authorized"}
        
        if r.status_code == 401:
            return {"valid": False, "status": "invalid", "message": "Invalid API Key"}
        elif r.status_code == 429:
             return {"valid": False, "status": "rate_limited", "message": "Rate limit / Balance low"}
        else:
            return {"valid": False, "status": "unknown", "message": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"valid": False, "status": "unknown", "message": f"Network Error: {str(e)}"}
