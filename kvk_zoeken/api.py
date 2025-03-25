import frappe
import requests
from urllib.parse import urlencode
from frappe.utils import now_datetime

@frappe.whitelist()
def search_kvk(search_term=None, kvk_nummer=None, naam=None, postcode=None, 
               huisnummer=None, plaats=None, pagina=1, resultaten_per_pagina=10):
    """
    Search the KVK API with various parameters
    """
    # Get KVK Settings
    try:
        settings = frappe.get_single("KVK Settings")
    except frappe.DoesNotExistError:
        frappe.throw("KVK Settings not found. Please create settings first.")
    
    if not settings.enabled:
        frappe.throw("KVK API integration is not enabled")
    
    base_url = settings.api_url
    api_key = settings.api_key
    
    if not api_key:
        frappe.throw("KVK API key not configured. Please set it in KVK Settings.")
    
    # Headers for the request
    headers = {
        "apikey": api_key,
        "Accept": "application/json"
    }
    
    # Build query parameters
    params = {}
    
    # If a generic search term is provided, determine what it might be
    if search_term:
        # Check if it's a KVK number (8 digits)
        if search_term.isdigit() and len(search_term) == 8:
            params["kvkNummer"] = search_term
        # Check if it looks like a postcode
        elif len(search_term) >= 6 and search_term[:4].isdigit() and search_term[4:].isalpha():
            params["postcode"] = search_term
        # Otherwise treat as a name
        else:
            params["naam"] = search_term
    
    # Add specific parameters if provided
    if kvk_nummer:
        params["kvkNummer"] = kvk_nummer
    if naam:
        params["naam"] = naam
    if postcode:
        params["postcode"] = postcode
    if huisnummer:
        params["huisnummer"] = huisnummer
    if plaats:
        params["plaats"] = plaats
    
    # Pagination parameters
    params["pagina"] = pagina
    params["resultatenPerPagina"] = resultaten_per_pagina
    
    try:
        # Make the request to the KVK API
        response = requests.get(
            f"{base_url}?{urlencode(params)}",
            headers=headers
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Return the JSON response
        return response.json()
    
    except requests.exceptions.RequestException as e:
        frappe.log_error(f"KVK API Error: {str(e)}")
        return {"error": str(e)}