import frappe
import requests
from urllib.parse import urlencode
from frappe.utils import now_datetime

@frappe.whitelist()
def search_kvk(search_term=None, kvk_nummer=None, naam=None, postcode=None, 
               huisnummer=None, huisletter=None, plaats=None, straatnaam=None,
               pagina=1, resultaten_per_pagina=10):
    """
    Search the KVK API with various parameters
    
    Args:
        search_term: Generic search term (will be interpreted as KVK number, postcode, or name)
        kvk_nummer: KVK number (8 digits)
        naam: Company name
        postcode: Postal code
        huisnummer: House number
        huisletter: House letter
        plaats: City
        straatnaam: Street name
        pagina: Page number (default: 1)
        resultaten_per_pagina: Results per page (default: 10, max: 100)
        
    Returns:
        dict: KVK API response or error message
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
    
    # Add specific parameters if provided - using the correct parameter names from the API schema
    if kvk_nummer:
        params["kvkNummer"] = kvk_nummer
    if naam:
        params["naam"] = naam
    if postcode:
        params["postcode"] = postcode
    if huisnummer:
        params["huisnummer"] = huisnummer
    if huisletter:
        params["huisletter"] = huisletter
    if plaats:
        params["plaats"] = plaats
    if straatnaam:
        params["straatnaam"] = straatnaam
    
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
    
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        error_message = f"HTTP Error: {status_code}"
        
        # Try to parse error response
        try:
            error_data = e.response.json()
            if error_data.get("fout"):
                error_message = error_data["fout"][0].get("omschrijving", error_message)
        except:
            pass
            
        frappe.log_error("KVK API Error", error_message)
        return {"error": error_message, "status_code": status_code}
        
    except requests.exceptions.RequestException as e:
        frappe.log_error("KVK API Error", str(e))
        return {"error": str(e)}

def process_kvk_address(address_data, provided_address=None):
    """
    Process address data from KVK API response

    Args:
        address_data: Address data from KVK API
        provided_address: Optional pre-formatted address

    Returns:
        dict: Processed address data with keys:
            - formatted_address: Full formatted address
            - street_address: Street and house number
            - postal_code: Postal code
            - city: City
            - country: Country
    """
    result = {
        "formatted_address": provided_address or "",
        "street_address": "",
        "postal_code": "",
        "city": "",
        "country": "Netherlands"  # Default for Dutch companies
    }

    if not address_data and not provided_address:
        return result

    # If a pre-formatted address is provided, use it
    if provided_address:
        result["formatted_address"] = provided_address
        return result

    # Handle domestic address (binnenlandsAdres)
    if address_data.get("binnenlandsAdres"):
        addr = address_data["binnenlandsAdres"]

        # Process street address
        street_address = addr.get("straatnaam", "")
        if addr.get("huisnummer"):
            street_address += f" {addr['huisnummer']}"
            if addr.get("huisletter"):
                street_address += addr["huisletter"]
        result["street_address"] = street_address.strip() or addr.get("plaats", "Unknown City")

        # Process postal code and city
        result["postal_code"] = addr.get("postcode", "")
        result["city"] = addr.get("plaats", "")

        # Ensure address_line1 fallback
        if not result["street_address"]:
            result["street_address"] = result["city"] or "Unknown City"

        # Build formatted address
        formatted_address = result["street_address"]
        if result["postal_code"] or result["city"]:
            formatted_address += "\n"
            if result["postal_code"]:
                formatted_address += result["postal_code"] + " "
            if result["city"]:
                formatted_address += result["city"]

        formatted_address += "\nNetherlands"
        result["formatted_address"] = formatted_address

    # Handle foreign address (buitenlandsAdres)
    elif address_data.get("buitenlandsAdres"):
        addr = address_data["buitenlandsAdres"]

        # Process street address
        result["street_address"] = addr.get("straatHuisnummer", "")

        # Process postal code and city
        postal_city = addr.get("postcodeWoonplaats", "")
        if postal_city:
            # Try to extract postal code and city
            parts = postal_city.split(" ", 1)
            if len(parts) > 1 and parts[0].strip():
                result["postal_code"] = parts[0].strip()
                result["city"] = parts[1].strip()
            else:
                result["city"] = postal_city

        # Ensure address_line1 fallback
        if not result["street_address"]:
            result["street_address"] = result["city"] or "Unknown City"

        # Process country
        result["country"] = addr.get("land", "Netherlands")

        # Build formatted address
        formatted_address = result["street_address"]
        if postal_city:
            formatted_address += "\n" + postal_city
        if result["country"]:
            formatted_address += "\n" + result["country"]

        result["formatted_address"] = formatted_address

    # Log incomplete address for debugging
    if not result["formatted_address"]:
        frappe.log_error("Incomplete address data", {address_data})

    return result

def process_kvk_addresses(addresses_data):
    """
    Process multiple address entries from KVK API response

    Args:
        addresses_data: List of address data from KVK API

    Returns:
        list: List of processed address data dictionaries
    """
    processed_addresses = []

    for address_data in addresses_data:
        result = {
            "formatted_address": "",
            "street_address": "",
            "postal_code": "",
            "city": "",
            "country": "Netherlands"  # Default for Dutch companies
        }

        # Handle domestic address (binnenlandsAdres)
        if address_data.get("binnenlandsAdres"):
            addr = address_data["binnenlandsAdres"]

            # Process street address
            street_address = ""
            if addr.get("straatnaam"):  
                street_address = addr["straatnaam"]
            if addr.get("straatnaam") and addr.get("huisnummer"):
                street_address = f"{addr['straatnaam']} {addr['huisnummer']}"
                if addr.get("huisletter"):
                    street_address += addr["huisletter"]
            result["street_address"] = street_address or addr.get("plaats", "Unknown City")

            # Process postal code and city
            result["postal_code"] = addr.get("postcode", "")
            result["city"] = addr.get("plaats", "")

            # Build formatted address
            formatted_address = street_address or result["city"]
            if result["postal_code"] or result["city"]:
                formatted_address += "\n"
                if result["postal_code"]:
                    formatted_address += result["postal_code"] + " "
                if result["city"]:
                    formatted_address += result["city"]

            formatted_address += "\nNetherlands"
            result["formatted_address"] = formatted_address

        # Handle foreign address (buitenlandsAdres)
        elif address_data.get("buitenlandsAdres"):
            addr = address_data["buitenlandsAdres"]

            # Process street address
            result["street_address"] = addr.get("straatHuisnummer", "")

            # Process postal code and city
            postal_city = addr.get("postcodeWoonplaats", "")
            if postal_city:
                # Try to extract postal code and city
                parts = postal_city.split(" ", 1)
                if len(parts) > 1 and parts[0].strip():
                    result["postal_code"] = parts[0].strip()
                    result["city"] = parts[1].strip()
                else:
                    result["city"] = postal_city

            # Process country
            result["country"] = addr.get("land", "Netherlands")

            # Build formatted address
            formatted_address = result["street_address"] or result["city"]
            if postal_city:
                formatted_address += "\n" + postal_city
            if result["country"]:
                formatted_address += "\n" + result["country"]

            result["formatted_address"] = formatted_address

        # Log incomplete address for debugging
        if not result["formatted_address"]:
            frappe.log_error("Incomplete address data", {address_data})

        processed_addresses.append(result)

    return processed_addresses

@frappe.whitelist()
def create_relation_from_kvk(kvk_nummer, administration, company_name=None, company_type=None, 
                            is_active=None, rsin_number=None, establishment_number=None, kvk_address=None):
    """
    Create a new Relation from KVK data
    
    Args:
        kvk_nummer: KVK number
        administration: Administration DocType name
        company_name: Optional company name (if not provided, will be fetched from KVK)
        company_type: Optional company type
        is_active: Optional active status
        rsin_number: Optional RSIN number
        establishment_number: Optional establishment number
        kvk_address: Optional pre-formatted KVK address
        
    Returns:
        dict: Result with success status, message, and relation name if successful
    """
    try:
        # Log the incoming parameters for debugging
        frappe.logger().debug(f"create_relation_from_kvk called with: kvk_nummer={kvk_nummer}, administration={administration}")
        
        # Validate required parameters
        if not kvk_nummer:
            return {
                "success": False,
                "message": "KVK number is required"
            }
            
        if not administration:
            return {
                "success": False,
                "message": "Administration is required"
            }
        
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
        
        # Log the response from the KVK server for debugging
        frappe.log_error("KVK API Debug", f"KVK API Response: {kvk_data}")
        
        # Check if relation with this KVK number already exists for the given administration
        # Make sure to use exact field names from the Relation DocType
        filters = {
            "kvk_number": kvk_nummer,
            "administration": administration
        }

        # Log the filters for debugging
        frappe.log_error("Checking for existing relation with filters", {filters})

        # Execute the query and log the SQL for debugging
        frappe.flags.in_test = True  # This will log the SQL query
        existing = frappe.get_all(
            "Relation", 
            filters=filters,
            fields=["name", "administration"]
        )
        frappe.flags.in_test = False
        
        # Log the query results
        frappe.log_error("Existing relation query results", {existing})

        if existing:
            frappe.log_error("Found existing relation", {existing})
            return {
                "success": False,
                "message": f"A relation with KVK number {kvk_nummer} already exists for administration {existing[0].get('administration', 'unknown')}",
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
            relation.is_active = "Ja" if company_data.get("actief", "Nee") == "Ja" else "Nee"
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
        
        # Set administration if provided - CRITICAL for duplicate checking
        relation.administration = administration
        frappe.logger().debug(f"Setting administration to: {administration}")
        
        # Process address information
        address_data = process_kvk_address(company_data.get("adres") if company_data else None, kvk_address)
        
        # Set address fields
        relation.kvk_address = address_data["formatted_address"]
        relation.address1 = address_data["street_address"]
        relation.postal_code = address_data["postal_code"]
        relation.city = address_data["city"]
        relation.country = address_data["country"]
        
        # Insert the relation and handle any potential errors
        try:
            relation.insert()
            frappe.log_error(f"Relation inserted successfully: {relation.name}")
        except Exception as insert_error:
            frappe.log_error(f"Error inserting relation: {str(insert_error)}")
            # Check if it's a duplicate entry error
            if "Duplicate entry" in str(insert_error):
                # Try to find the existing relation again with a more flexible query
                existing_flexible = frappe.db.sql(
                    """
                    SELECT name, administration 
                    FROM `tabRelation` 
                    WHERE kvk_number = %s
                    """,
                    (kvk_nummer,),
                    as_dict=True
                )
                frappe.logger().debug(f"Flexible query results: {existing_flexible}")
                
                if existing_flexible:
                    return {
                        "success": False,
                        "message": f"A relation with KVK number {kvk_nummer} already exists",
                        "relation": existing_flexible[0].get("name")
                    }
            # Re-raise the error if it's not a duplicate issue or we couldn't find the duplicate
            raise
        
        # Filter addresses for the specific company
        filtered_results = [result for result in kvk_data.get("resultaten", []) if result.get("kvkNummer") == kvk_nummer]

        # Process and save addresses for the filtered results
        for result in filtered_results:
            if "adres" in result:
                processed_addresses = process_kvk_addresses([result["adres"]])
                for address in processed_addresses:
                    address_doc = frappe.new_doc("Address")
                    address_doc.address_title = f"{relation.name} Address"
                    address_doc.address_type = "Billing"  # Default type
                    address_doc.address_line1 = address.get("street_address", "")
                    address_doc.city = address.get("city", "")
                    address_doc.country = address.get("country", "Netherlands")
                    address_doc.pincode = address.get("postal_code", "")

                    # Add dynamic link to Relation
                    address_doc.append("links", {
                        "link_doctype": "Relation",
                        "link_name": relation.name
                    })

                    # Insert the Address document
                    address_doc.insert()

        return {
            "success": True,
            "message": "Relation created successfully",
            "relation": relation.name
        }
        
    except Exception as e:
        frappe.log_error("KVK API", frappe.get_traceback())
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def save_addresses_to_relation(relation_name, addresses_data, administration=None):
    """
    Save multiple addresses as Address DocType linked to a Relation

    Args:
        relation_name: Name of the Relation to link addresses to
        addresses_data: List of address data from KVK API

    Returns:
        dict: Result with success status and message
    """
    try:
        # Process the addresses
        processed_addresses = process_kvk_addresses(addresses_data)

        for address in processed_addresses:
            # Create a new Address document
            address_doc = frappe.new_doc("Address")
            address_doc.address_title = f"{relation_name} Address"
            address_doc.address_type = "Billing"  # Default type, can be adjusted
            address_doc.address_line1 = address.get("street_address", "")
            address_doc.city = address.get("city", "")
            address_doc.country = address.get("country", "Netherlands")
            address_doc.pincode = address.get("postal_code", "")

            # Ensure address_line1 is set correctly
            street_address = address.get("street_address", "")
            if not street_address:
                street_address = address.get("city", "Unknown City")
            address_doc.address_line1 = street_address

            # Add dynamic link to Relation
            address_doc.append("links", {
                "link_doctype": "Relation",
                "link_name": relation_name
            }, "administration" if administration else None)

            # Insert the Address document
            address_doc.insert()

        return {
            "success": True,
            "message": f"Addresses successfully linked to Relation {relation_name}"
        }

    except Exception as e:
        frappe.log_error("KVK API", frappe.get_traceback())
        return {
            "success": False,
            "message": f"Failed to save addresses to Relation {relation_name}: {str(e)}"
        }