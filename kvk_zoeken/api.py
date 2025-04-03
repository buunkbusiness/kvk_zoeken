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
    
@frappe.whitelist()
def create_relation_from_kvk(kvk_nummer, administration=None, company_name=None, company_type=None, 
                            is_active=None, rsin_number=None, establishment_number=None, kvk_address=None):
    """
    Create a new Relation from KVK data using the fields directly in the Relation DocType
    """
    try:
        # Determine if we need to fetch KVK data or use provided parameters
        fetch_from_kvk = not company_name  # If company_name is not provided, fetch from KVK
        company_data = None
        
        # Get KVK data if needed
        if fetch_from_kvk:
            kvk_data = search_kvk(kvk_nummer=kvk_nummer)
            
            if not kvk_data or "resultaten" not in kvk_data or not kvk_data["resultaten"]:
                return {
                    "success": False,
                    "message": f"No data found for KVK number {kvk_nummer}"
                }
            
            company_data = kvk_data["resultaten"][0]
        
        # Check if relation with this KVK number already exists
        existing = frappe.get_all(
            "Relation", 
            filters={"kvk_number": kvk_nummer},
            fields=["name"]
        )
        
        if existing:
            return {
                "success": False,
                "message": f"A relation with KVK number {kvk_nummer} already exists",
                "relation": existing[0].name
            }
        
        # Create new relation
        relation = frappe.new_doc("Relation")
        relation.is_private_person = 0  # Companies from KVK are never private persons
        
        # Set KVK fields directly in the Relation DocType
        relation.kvk_number = kvk_nummer
        
        # Use provided values or get from KVK data
        if company_name:
            relation.company_name = company_name
        elif company_data:
            relation.company_name = company_data["naam"]
        else:
            # This should not happen, but just in case
            relation.company_name = f"Company {kvk_nummer}"
            
        if company_type:
            relation.company_type = company_type
        elif company_data:
            relation.company_type = company_data.get("type", "")
            
        if is_active is not None:
            relation.is_active = is_active
        elif company_data:
            relation.is_active = "Ja" if company_data.get("actief") == "Ja" else "Nee"
        else:
            relation.is_active = "Ja"  # Default to active
            
        if rsin_number:
            relation.rsin_number = rsin_number
        elif company_data:
            relation.rsin_number = company_data.get("rsin", "")
            
        if establishment_number:
            relation.establishment_number = establishment_number
        elif company_data:
            relation.establishment_number = company_data.get("vestigingsnummer", "")
            
        relation.relation_type = "Customer"  # Default type, can be changed later
        
        # Set administration if provided
        if administration:
            relation.administration = administration
        
        # Handle address information
        if kvk_address:
            relation.kvk_address = kvk_address
            
        # Also populate the standard address fields if KVK data is available
        if company_data and company_data.get("adres"):
            addr = company_data["adres"]
            
            # Format KVK address for the kvk_address field
            formatted_address = ""
            if addr.get("straatnaam") and addr.get("huisnummer"):
                street_address = f"{addr['straatnaam']} {addr['huisnummer']}"
                if addr.get("huisletter"):
                    street_address += addr["huisletter"]
                formatted_address += street_address
                relation.address1 = street_address
            elif addr.get("straatHuisnummer"):
                formatted_address += addr["straatHuisnummer"]
                relation.address1 = addr["straatHuisnummer"]
                
            if addr.get("postcode") or addr.get("plaats"):
                formatted_address += "\n"
                if addr.get("postcode"):
                    formatted_address += addr["postcode"] + " "
                    relation.postal_code = addr["postcode"]
                if addr.get("plaats"):
                    formatted_address += addr["plaats"]
                    relation.city = addr["plaats"]
        
            # Make sure to map the street address to address1 field
            if addr.get("straatnaam") and addr.get("huisnummer"):
                street_address = f"{addr['straatnaam']} {addr['huisnummer']}"
                if addr.get("huisletter"):
                    street_address += addr["huisletter"]
                relation.address1 = street_address
            elif addr.get("straatHuisnummer"):
                relation.address1 = addr["straatHuisnummer"]
                
            if addr.get("land"):
                formatted_address += "\n" + addr["land"]
                relation.country = addr["land"]
            else:
                relation.country = "Netherlands"  # Default for KVK
                
            # Set the formatted address if not provided
            if not kvk_address:
                relation.kvk_address = formatted_address
        
        relation.insert()
        
        return {
            "success": True,
            "message": "Relation created successfully",
            "relation": relation.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating relation from KVK: {str(e)}", "KVK API")
        return {
            "success": False,
            "message": str(e)
        }

