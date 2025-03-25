# Copyright (c) 2025, Buunk Business and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document

class KVKSettings(Document):
    def validate(self):
        if self.enabled and not self.api_key:
            frappe.throw("API Key is required when KVK integration is enabled")
    
    @frappe.whitelist()
    def test_connection(self):
        if not self.api_key:
            return {"success": False, "message": "API Key is required"}
    
        try:
            headers = {
                "apikey": self.api_key,
                "Accept": "application/json"
            }
        
            # Log the headers for debugging (without the full API key)
            masked_key = self.api_key[:4] + "..." + self.api_key[-4:] if len(self.api_key) > 8 else "****"
            frappe.log_error(f"Headers: {{'apikey': '{masked_key}', 'Accept': 'application/json'}}", "KVK API Test")
        
            # Test with a simple query
            response = requests.get(
                f"{self.api_url}?kvkNummer=69599084",
                headers=headers
            )
        
            # Log the response for debugging
            frappe.log_error(f"Response status: {response.status_code}, Content: {response.text[:500]}", "KVK API Test")
        
            # Check if we get a valid response
            if response.status_code == 400 and "Invalid kvkNummer" in response.text:
                return {"success": True, "message": "Connection successful (API key is valid)"}
            elif response.status_code == 200:
                return {"success": True, "message": "Connection successful"}
            else:
                return {
                    "success": False, 
                    "message": f"Connection failed with status code {response.status_code}: {response.text}",
                    "details": {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                }
            
        except Exception as e:
            frappe.log_error(f"Connection test error: {str(e)}", "KVK API Test")
            return {"success": False, "message": f"Connection failed: {str(e)}"}