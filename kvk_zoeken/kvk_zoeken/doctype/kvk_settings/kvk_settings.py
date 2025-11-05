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
        """Test connection to both KVK APIs"""
        from kvk_zoeken.api import test_kvk_connection
        return test_kvk_connection()