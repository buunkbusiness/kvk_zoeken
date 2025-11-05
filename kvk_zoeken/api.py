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

@frappe.whitelist()
def get_kvk_basisprofiel(kvk_nummer, geo_data=False):
    """
    Get complete business profile from KVK basisprofiel API
    
    Args:
        kvk_nummer: KVK number (8 digits)
        geo_data: Whether to include geographical data (default: False)
        
    Returns:
        dict: Complete KVK basisprofiel response or error message
    """
    # Get KVK Settings
    try:
        settings = frappe.get_single("KVK Settings")
    except frappe.DoesNotExistError:
        frappe.throw("KVK Settings not found. Please create settings first.")
    
    if not settings.enabled:
        frappe.throw("KVK API integration is not enabled")
    
    # Get basisprofiel API URL
    base_url = getattr(settings, 'basisprofiel_api_url', None) or "https://api.kvk.nl/api/v2/basisprofiel"
    api_key = settings.api_key
    
    if not api_key:
        frappe.throw("KVK API key not configured. Please set it in KVK Settings.")
    
    if not kvk_nummer:
        frappe.throw("KVK number is required")
    
    # Validate KVK number format
    if not kvk_nummer.isdigit() or len(kvk_nummer) != 8:
        frappe.throw("KVK number must be 8 digits")
    
    # Headers for the request
    headers = {
        "apikey": api_key,
        "Accept": "application/json"
    }
    
    # Build query parameters
    params = {
        "kvkNummer": kvk_nummer,
        "geoData": "true" if geo_data else "false"
    }
    
    try:
        # Make the request to the KVK basisprofiel API
        response = requests.get(
            f"{base_url}/{kvk_nummer}?{urlencode(params)}",
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
            
        frappe.log_error("KVK Basisprofiel API Error", error_message)
        return {"error": error_message, "status_code": status_code}
        
    except requests.exceptions.RequestException as e:
        frappe.log_error("KVK Basisprofiel API Error", str(e))
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
        frappe.log_error("Incomplete address data", str(address_data))

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
            frappe.log_error("Incomplete address data", str(address_data))

        processed_addresses.append(result)

    return processed_addresses

def process_basisprofiel_data(basisprofiel_data):
    """
    Process complete basisprofiel data into structured format
    
    Args:
        basisprofiel_data: Complete basisprofiel response from KVK API
        
    Returns:
        dict: Processed business data with all relevant information
    """
    if not basisprofiel_data or "error" in basisprofiel_data:
        return {"error": "Invalid basisprofiel data"}
    
    result = {
        "basic_info": {},
        "addresses": [],
        "establishments": [],
        "sbi_activities": [],
        "websites": [],
        "main_establishment": None,
        "owner_info": {}
    }
    
    # Process basic company information
    result["basic_info"] = {
        "kvk_number": basisprofiel_data.get("kvkNummer", ""),
        "company_name": basisprofiel_data.get("naam", ""),
        "statutory_name": basisprofiel_data.get("statutaireNaam", ""),
        "rsin": basisprofiel_data.get("rsin", ""),
        "registration_date": basisprofiel_data.get("formeleRegistratiedatum", ""),
        "material_registration": basisprofiel_data.get("materieleRegistratie", {}),
        "trade_names": basisprofiel_data.get("handelsnamen", []),
        "non_mailing": basisprofiel_data.get("indNonMailing", "")
    }
    
    # Process SBI activities
    if "sbiActiviteiten" in basisprofiel_data:
        for sbi in basisprofiel_data["sbiActiviteiten"]:
            result["sbi_activities"].append({
                "sbi_code": sbi.get("sbiCode", ""),
                "description": sbi.get("sbiOmschrijving", ""),
                "is_main_activity": sbi.get("indHoofdactiviteit", "") == "Ja"
            })
    
    # Process main establishment (hoofdvestiging)
    if "hoofdvestiging" in basisprofiel_data:
        hv = basisprofiel_data["hoofdvestiging"]
        result["main_establishment"] = {
            "establishment_number": hv.get("vestigingsnummer", ""),
            "kvk_number": hv.get("kvkNummer", ""),
            "rsin": hv.get("rsin", ""),
            "first_trade_name": hv.get("eersteHandelsnaam", ""),
            "is_main_establishment": hv.get("indHoofdvestiging", ""),
            "is_commercial_establishment": hv.get("indCommercieleVestiging", ""),
            "full_time_employees": hv.get("voltijdWerkzamePersonen", 0),
            "part_time_employees": hv.get("deeltijdWerkzamePersonen", 0),
            "total_employees": hv.get("totaalWerkzamePersonen", 0),
            "trade_names": hv.get("handelsnamen", []),
            "websites": hv.get("websites", []),
            "addresses": []
        }
        
        # Process main establishment addresses
        if "adressen" in hv:
            for addr in hv["adressen"]:
                processed_addr = process_basisprofiel_address(addr)
                result["main_establishment"]["addresses"].append(processed_addr)
                result["addresses"].append(processed_addr)
        
        # Process main establishment SBI activities
        if "sbiActiviteiten" in hv:
            result["main_establishment"]["sbi_activities"] = []
            for sbi in hv["sbiActiviteiten"]:
                result["main_establishment"]["sbi_activities"].append({
                    "sbi_code": sbi.get("sbiCode", ""),
                    "description": sbi.get("sbiOmschrijving", ""),
                    "is_main_activity": sbi.get("indHoofdactiviteit", "") == "Ja"
                })
    
    # Process owner information (eigenaar)
    if "eigenaar" in basisprofiel_data:
        eigenaar = basisprofiel_data["eigenaar"]
        result["owner_info"] = {
            "rsin": eigenaar.get("rsin", ""),
            "legal_form": eigenaar.get("rechtsvorm", ""),
            "extended_legal_form": eigenaar.get("uitgebreideRechtsvorm", ""),
            "addresses": [],
            "websites": eigenaar.get("websites", [])
        }
        
        # Process owner addresses
        if "adressen" in eigenaar:
            for addr in eigenaar["adressen"]:
                processed_addr = process_basisprofiel_address(addr)
                result["owner_info"]["addresses"].append(processed_addr)
                if processed_addr not in result["addresses"]:
                    result["addresses"].append(processed_addr)
    
    # Process all establishments (vestigingen)
    if "vestigingen" in basisprofiel_data:
        vestigingen_data = basisprofiel_data["vestigingen"]
        result["establishments_summary"] = {
            "total_establishments": vestigingen_data.get("totaalAantalVestigingen", 0),
            "commercial_establishments": vestigingen_data.get("aantalCommercieleVestigingen", 0),
            "non_commercial_establishments": vestigingen_data.get("aantalNietCommercieleVestigingen", 0)
        }
        
        if "vestigingen" in vestigingen_data:
            for vest in vestigingen_data["vestigingen"]:
                result["establishments"].append({
                    "establishment_number": vest.get("vestigingsnummer", ""),
                    "first_trade_name": vest.get("eersteHandelsnaam", ""),
                    "is_main_establishment": vest.get("indHoofdvestiging", ""),
                    "is_commercial_establishment": vest.get("indCommercieleVestiging", ""),
                    "full_address": vest.get("volledigAdres", "")
                })
    
    return result

def process_basisprofiel_address(address_data):
    """
    Process address data from basisprofiel API response
    
    Args:
        address_data: Address data from basisprofiel API
        
    Returns:
        dict: Processed address data
    """
    result = {
        "type": address_data.get("type", ""),
        "is_protected": address_data.get("IndAfgeschermd", "") == "Ja",
        "full_address": address_data.get("volledigAdres", ""),
        "street_name": address_data.get("straatnaam", ""),
        "house_number": address_data.get("huisnummer", ""),
        "house_number_addition": address_data.get("huisnummerToevoeging", ""),
        "house_letter": address_data.get("huisletter", ""),
        "address_addition": address_data.get("toevoegingAdres", ""),
        "postal_code": address_data.get("postcode", ""),
        "post_box_number": address_data.get("postbusnummer", ""),
        "city": address_data.get("plaats", ""),
        "street_house_number": address_data.get("straatHuisnummer", ""),
        "postal_code_city": address_data.get("postcodeWoonplaats", ""),
        "region": address_data.get("regio", ""),
        "country": address_data.get("land", "Netherlands"),
        "geo_data": address_data.get("geoData", {})
    }
    
    # Build formatted address if not provided
    if not result["full_address"]:
        formatted_address = ""
        
        # Build street address
        if result["street_name"]:
            formatted_address = result["street_name"]
            if result["house_number"]:
                formatted_address += f" {result['house_number']}"
                if result["house_letter"]:
                    formatted_address += result["house_letter"]
                if result["house_number_addition"]:
                    formatted_address += f" {result['house_number_addition']}"
        elif result["street_house_number"]:
            formatted_address = result["street_house_number"]
        
        # Add postal code and city
        if result["postal_code"] and result["city"]:
            formatted_address += f"\n{result['postal_code']} {result['city']}"
        elif result["postal_code_city"]:
            formatted_address += f"\n{result['postal_code_city']}"
        elif result["city"]:
            formatted_address += f"\n{result['city']}"
        
        # Add country
        if result["country"]:
            formatted_address += f"\n{result['country']}"
        
        result["full_address"] = formatted_address.strip()
    
    return result

@frappe.whitelist()
def get_complete_company_data(kvk_nummer, geo_data=False):
    """
    Get complete company data using both search and basisprofiel APIs
    
    Args:
        kvk_nummer: KVK number (8 digits)
        geo_data: Whether to include geographical data (default: False)
        
    Returns:
        dict: Complete company data combining both APIs
    """
    if not kvk_nummer:
        return {"error": "KVK number is required"}
    
    # Validate KVK number format
    if not kvk_nummer.isdigit() or len(kvk_nummer) != 8:
        return {"error": "KVK number must be 8 digits"}
    
    result = {
        "success": True,
        "kvk_number": kvk_nummer,
        "search_data": None,
        "basisprofiel_data": None,
        "processed_data": None,
        "error": None
    }
    
    try:
        # First, get basisprofiel data (most complete)
        basisprofiel_response = get_kvk_basisprofiel(kvk_nummer, geo_data)
        
        if "error" in basisprofiel_response:
            # If basisprofiel fails, fall back to search
            search_response = search_kvk(kvk_nummer=kvk_nummer)
            
            if "error" in search_response or not search_response.get("resultaten"):
                return {
                    "success": False,
                    "error": "No data found for KVK number",
                    "kvk_number": kvk_nummer
                }
            
            result["search_data"] = search_response
            # Process search data into a standardized format
            if search_response["resultaten"]:
                search_item = search_response["resultaten"][0]
                result["processed_data"] = process_search_data_to_standard_format(search_item)
        else:
            # Process the complete basisprofiel data
            result["basisprofiel_data"] = basisprofiel_response
            result["processed_data"] = process_basisprofiel_data(basisprofiel_response)
            
            # Also get search data for additional context if needed
            search_response = search_kvk(kvk_nummer=kvk_nummer)
            if "resultaten" in search_response and search_response["resultaten"]:
                result["search_data"] = search_response
    
    except Exception as e:
        frappe.log_error("Complete Company Data Error", str(e))
        result["success"] = False
        result["error"] = str(e)
    
    return result

def process_search_data_to_standard_format(search_item):
    """
    Convert search API data to standardized format similar to basisprofiel
    
    Args:
        search_item: Single search result item
        
    Returns:
        dict: Standardized company data format
    """
    result = {
        "basic_info": {
            "kvk_number": search_item.get("kvkNummer", ""),
            "company_name": search_item.get("naam", ""),
            "rsin": search_item.get("rsin", ""),
            "establishment_number": search_item.get("vestigingsnummer", ""),
            "company_type": search_item.get("type", ""),
            "is_active": search_item.get("actief", "Nee") == "Ja"
        },
        "addresses": [],
        "main_establishment": None
    }
    
    # Process address from search data
    if "adres" in search_item:
        addr = search_item["adres"]
        processed_addr = {
            "type": "Unknown",
            "full_address": search_item.get("adres", {}).get("volledigAdres", ""),
            "street_name": addr.get("straatnaam", ""),
            "house_number": addr.get("huisnummer", ""),
            "house_letter": addr.get("huisletter", ""),
            "postal_code": addr.get("postcode", ""),
            "city": addr.get("plaats", ""),
            "country": "Netherlands"
        }
        
        # Build formatted address if not available
        if not processed_addr["full_address"]:
            formatted_address = ""
            if processed_addr["street_name"] and processed_addr["house_number"]:
                formatted_address = f"{processed_addr['street_name']} {processed_addr['house_number']}"
                if processed_addr["house_letter"]:
                    formatted_address += processed_addr["house_letter"]
            
            if processed_addr["postal_code"] and processed_addr["city"]:
                if formatted_address:
                    formatted_address += "\n"
                formatted_address += f"{processed_addr['postal_code']} {processed_addr['city']}"
            
            formatted_address += "\nNetherlands"
            processed_addr["full_address"] = formatted_address.strip()
        
        result["addresses"].append(processed_addr)
    
    return result

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
        complete_data = None
        
        # Get complete KVK data if needed
        if fetch_from_kvk:
            complete_data = get_complete_company_data(kvk_nummer)
            
            if not complete_data["success"] or not complete_data.get("processed_data"):
                return {
                    "success": False,
                    "message": complete_data.get("error", f"No data found for KVK number {kvk_nummer}")
                }
            
            company_data = complete_data["processed_data"]
        
        # Log the response from the KVK server for debugging
        frappe.log_error("KVK API Debug", f"Complete KVK API Response: {complete_data}")
        
        # Check if relation with this KVK number already exists for the given administration
        # Make sure to use exact field names from the Relation DocType
        filters = {
            "kvk_number": kvk_nummer,
            "administration": administration
        }

        # Log the filters for debugging
        frappe.log_error("Checking for existing relation with filters", str(filters))

        # Execute the query and log the SQL for debugging
        frappe.flags.in_test = True  # This will log the SQL query
        existing = frappe.get_all(
            "Relation", 
            filters=filters,
            fields=["name", "administration"]
        )
        frappe.flags.in_test = False
        
        # Log the query results
        frappe.log_error("Existing relation query results", str(existing))

        if existing:
            frappe.log_error("Found existing relation", str(existing))
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
        elif company_data and company_data.get("basic_info"):
            relation.company_name = company_data["basic_info"].get("company_name", f"Company {kvk_nummer}")
        else:
            # This should not happen, but just in case
            relation.company_name = f"Company {kvk_nummer}"
            
        if company_type:
            relation.company_type = company_type
        elif company_data and company_data.get("basic_info"):
            relation.company_type = company_data["basic_info"].get("company_type", "")
            
        if is_active is not None:
            relation.is_active = is_active
        elif company_data and company_data.get("basic_info"):
            relation.is_active = "Ja" if company_data["basic_info"].get("is_active", False) else "Nee"
        else:
            relation.is_active = "Ja"  # Default to active
            
        if rsin_number:
            relation.rsin_number = rsin_number
        elif company_data and company_data.get("basic_info"):
            relation.rsin_number = company_data["basic_info"].get("rsin", "")
            
        if establishment_number:
            relation.establishment_number = establishment_number
        elif company_data and company_data.get("basic_info"):
            relation.establishment_number = company_data["basic_info"].get("establishment_number", "")
            
        # Populate enhanced KVK fields from basisprofiel data
        if company_data and company_data.get("basic_info"):
            basic_info = company_data["basic_info"]
            relation.statutory_name = basic_info.get("statutory_name", "")
            relation.kvk_registration_date = basic_info.get("registration_date", "")
            relation.non_mailing_indicator = 1 if basic_info.get("non_mailing", "") == "Ja" else 0
            
        # Set owner/legal form information
        if company_data and company_data.get("owner_info"):
            owner_info = company_data["owner_info"]
            relation.extended_legal_form = owner_info.get("extended_legal_form", "")
            
        # Set main establishment information
        if company_data and company_data.get("main_establishment"):
            main_est = company_data["main_establishment"]
            relation.first_trade_name = main_est.get("first_trade_name", "")
            if not relation.establishment_number:  # Only set if not already set
                relation.establishment_number = main_est.get("establishment_number", "")
            relation.total_employees = main_est.get("total_employees", 0)
            relation.full_time_employees = main_est.get("full_time_employees", 0)
            relation.part_time_employees = main_est.get("part_time_employees", 0)
            relation.is_main_establishment = 1 if main_est.get("is_main_establishment", "") == "Ja" else 0
            relation.is_commercial_establishment = 1 if main_est.get("is_commercial_establishment", "") == "Ja" else 0
            
        relation.relation_type = "Customer"  # Default type, can be changed later
        
        # Set administration if provided - CRITICAL for duplicate checking
        relation.administration = administration
        frappe.logger().debug(f"Setting administration to: {administration}")
        
        # Process address information from the new data structure
        address_data = {"formatted_address": "", "street_address": "", "postal_code": "", "city": "", "country": "Netherlands"}
        
        if kvk_address:
            address_data["formatted_address"] = kvk_address
        elif company_data and company_data.get("addresses") and len(company_data["addresses"]) > 0:
            # Use the first available address
            first_addr = company_data["addresses"][0]
            address_data = {
                "formatted_address": first_addr.get("full_address", ""),
                "street_address": first_addr.get("street_name", "") + " " + str(first_addr.get("house_number", "")).strip(),
                "postal_code": first_addr.get("postal_code", ""),
                "city": first_addr.get("city", ""),
                "country": first_addr.get("country", "Netherlands")
            }
            # Clean up street address
            address_data["street_address"] = address_data["street_address"].strip()
            if first_addr.get("house_letter"):
                address_data["street_address"] += first_addr["house_letter"]
        
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
        
        # Process and save addresses from the complete data
        if company_data and company_data.get("addresses"):
            for address in company_data["addresses"]:
                address_doc = frappe.new_doc("Address")
                address_doc.address_title = f"{relation.name} Address"
                address_doc.address_type = "Office"  # Default type
                
                # Debug: Log the address data we received
                frappe.log_error("Address data being processed", str(address))
                
                # Use the processed address data - build street address carefully
                street_address = ""
                
                # Try multiple sources for street address
                if address.get("street_house_number"):
                    street_address = address["street_house_number"]
                elif address.get("street_name"):
                    street_address = address["street_name"]
                    if address.get("house_number"):
                        street_address += f" {address['house_number']}"
                        if address.get("house_letter"):
                            street_address += address["house_letter"]
                        if address.get("house_number_addition"):
                            street_address += f" {address['house_number_addition']}"
                elif address.get("full_address"):
                    # Use full address and parse first line
                    full_addr_lines = address["full_address"].split('\n')
                    street_address = full_addr_lines[0] if full_addr_lines else ""
                
                # Ensure we have a valid address_line1
                city = address.get("city", "")
                if address.get("postal_code_city") and not city:
                    # Extract city from postal_code_city format like "1234 AB Amsterdam"
                    parts = address["postal_code_city"].split(' ')
                    if len(parts) >= 3:
                        city = ' '.join(parts[2:])
                
                # Set address_line1 with fallbacks
                if street_address.strip():
                    address_doc.address_line1 = street_address.strip()
                elif city:
                    address_doc.address_line1 = city
                else:
                    address_doc.address_line1 = f"KVK {relation.kvk_number}"
                
                # Set city with fallbacks    
                address_doc.city = city or "Unknown"
                address_doc.country = address.get("country", "Netherlands")
                address_doc.pincode = address.get("postal_code", "")
                
                # Set administration field
                address_doc.administration = administration

                # Add dynamic link to Relation
                address_doc.append("links", {
                    "link_doctype": "Relation",
                    "link_name": relation.name
                })

                # Insert the Address document
                address_doc.insert()
        
        # Process and save SBI activities
        if company_data and company_data.get("sbi_activities"):
            save_sbi_activities_to_relation(relation.name, company_data["sbi_activities"], administration)

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
            
            # Debug: Log the address data we received
            frappe.log_error("Address data being processed in save_addresses_to_relation", str(address))
            
            # Build street address carefully using available fields
            street_address = ""
            
            # Try multiple sources for street address
            if address.get("street_house_number"):
                street_address = address["street_house_number"]
            elif address.get("street_name"):
                street_address = address["street_name"]
                if address.get("house_number"):
                    street_address += f" {address['house_number']}"
                    if address.get("house_letter"):
                        street_address += address["house_letter"]
                    if address.get("house_number_addition"):
                        street_address += f" {address['house_number_addition']}"
            elif address.get("full_address"):
                # Use full address and parse first line
                full_addr_lines = address["full_address"].split('\n')
                street_address = full_addr_lines[0] if full_addr_lines else ""
            
            # Ensure we have a valid address_line1
            city = address.get("city", "")
            if address.get("postal_code_city") and not city:
                # Extract city from postal_code_city format like "1234 AB Amsterdam"
                parts = address["postal_code_city"].split(' ')
                if len(parts) >= 3:
                    city = ' '.join(parts[2:])
            
            # Set address_line1 with fallbacks
            if street_address.strip():
                address_doc.address_line1 = street_address.strip()
            elif city:
                address_doc.address_line1 = city
            else:
                address_doc.address_line1 = f"Address for {relation_name}"
            
            # Set city and other fields with fallbacks
            address_doc.city = city or "Unknown"
            address_doc.country = address.get("country", "Netherlands")
            address_doc.pincode = address.get("postal_code", "")
            
            # Set administration field if provided
            if administration:
                address_doc.administration = administration

            # Add dynamic link to Relation
            address_doc.append("links", {
                "link_doctype": "Relation",
                "link_name": relation_name
            })

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

def save_sbi_activities_to_relation(relation_name, sbi_activities, administration=None):
    """
    Save SBI activities and link them to a relation
    
    Args:
        relation_name: Name of the Relation to link SBI activities to
        sbi_activities: List of SBI activity data
        administration: Optional administration context
        
    Returns:
        dict: Result with success status and message
    """
    try:
        created_activities = []
        
        for sbi in sbi_activities:
            sbi_code = sbi.get("sbi_code", "")
            description = sbi.get("description", "")
            is_main_activity = sbi.get("is_main_activity", False)
            
            if not sbi_code or not description:
                continue
            
            # Check if SBI activity already exists
            existing_sbi = frappe.db.exists("Standaard Bedrijfsindeling", sbi_code)
            
            if not existing_sbi:
                # Create new SBI activity
                sbi_doc = frappe.new_doc("Standaard Bedrijfsindeling")
                sbi_doc.sbi_code = sbi_code
                sbi_doc.description = description
                if is_main_activity:
                    sbi_doc.extra = "Main Activity"
                
                try:
                    sbi_doc.insert(ignore_permissions=True)
                    created_activities.append(sbi_code)
                except frappe.DuplicateEntryError:
                    # Another process might have created it, just continue
                    pass
            else:
                # Update existing SBI if it's a main activity and not already marked
                if is_main_activity:
                    sbi_doc = frappe.get_doc("Standaard Bedrijfsindeling", sbi_code)
                    if not sbi_doc.extra or "Main Activity" not in sbi_doc.extra:
                        sbi_doc.extra = "Main Activity"
                        sbi_doc.save()
        
        frappe.logger().info(f"Created/processed SBI activities: {created_activities} for relation {relation_name}")
        
        return {
            "success": True,
            "message": f"SBI activities processed successfully for Relation {relation_name}",
            "created_activities": created_activities
        }

    except Exception as e:
        frappe.log_error("SBI Activities Error", str(e))
        return {
            "success": False,
            "message": f"Failed to save SBI activities to Relation {relation_name}: {str(e)}"
        }

def bulk_sync_kvk_relations():
    """
    Weekly scheduled task to sync existing KVK relations with latest data
    This function is called by the scheduler
    """
    try:
        # Get KVK Settings to check if sync is enabled
        settings = frappe.get_single("KVK Settings")
        if not settings.enabled:
            frappe.logger().info("KVK sync skipped - integration not enabled")
            return
        
        # Get all relations with KVK numbers that haven't been synced recently
        one_week_ago = frappe.utils.add_days(frappe.utils.now(), -7)
        
        relations = frappe.get_all(
            "Relation",
            filters={
                "kvk_number": ["!=", ""],
                "kvk_number": ["is", "set"]
            },
            fields=["name", "kvk_number", "modified", "company_name"],
            limit=50  # Process in batches to avoid timeouts
        )
        
        synced_count = 0
        error_count = 0
        
        for relation in relations:
            try:
                # Get complete company data
                complete_data = get_complete_company_data(relation.kvk_number)
                
                if complete_data["success"] and complete_data.get("processed_data"):
                    # Update relation with latest data
                    update_relation_with_kvk_data(relation.name, complete_data["processed_data"])
                    synced_count += 1
                else:
                    frappe.logger().warning(f"Could not sync relation {relation.name}: {complete_data.get('error', 'Unknown error')}")
                    error_count += 1
                    
            except Exception as e:
                frappe.log_error("KVK Bulk Sync Error", f"Error syncing relation {relation.name}: {str(e)}")
                error_count += 1
        
        frappe.logger().info(f"KVK bulk sync completed: {synced_count} synced, {error_count} errors")
        
    except Exception as e:
        frappe.log_error("KVK Bulk Sync Error", str(e))

def update_relation_with_kvk_data(relation_name, processed_data):
    """
    Update an existing relation with processed KVK data
    
    Args:
        relation_name: Name of the Relation document to update
        processed_data: Processed company data from basisprofiel
    """
    try:
        relation = frappe.get_doc("Relation", relation_name)
        basic_info = processed_data.get("basic_info", {})
        
        # Update basic information if missing or changed
        if basic_info.get("company_name") and not relation.company_name:
            relation.company_name = basic_info["company_name"]
        
        if basic_info.get("rsin") and not relation.rsin_number:
            relation.rsin_number = basic_info["rsin"]
        
        if basic_info.get("establishment_number") and not relation.establishment_number:
            relation.establishment_number = basic_info["establishment_number"]
        
        # Update address information if missing
        if processed_data.get("addresses") and not relation.address1:
            first_addr = processed_data["addresses"][0]
            
            street_address = first_addr.get("street_name", "")
            if first_addr.get("house_number"):
                street_address += f" {first_addr['house_number']}"
                if first_addr.get("house_letter"):
                    street_address += first_addr["house_letter"]
            
            relation.address1 = street_address
            relation.postal_code = first_addr.get("postal_code", "")
            relation.city = first_addr.get("city", "")
            relation.country = first_addr.get("country", "Netherlands")
            relation.kvk_address = first_addr.get("full_address", "")
        
        # Save the updated relation
        relation.save()
        
        # Update SBI activities
        if processed_data.get("sbi_activities"):
            save_sbi_activities_to_relation(relation_name, processed_data["sbi_activities"])
        
        frappe.logger().info(f"Successfully updated relation {relation_name} with KVK data")
        
    except Exception as e:
        frappe.log_error("KVK Relation Update Error", f"Error updating relation {relation_name}: {str(e)}")

@frappe.whitelist()
def test_kvk_connection():
    """
    Test the KVK API connection using both search and basisprofiel endpoints
    
    Returns:
        dict: Test results for both APIs
    """
    try:
        # Get KVK Settings
        settings = frappe.get_single("KVK Settings")
        
        if not settings.enabled:
            return {
                "success": False,
                "message": "KVK API integration is not enabled"
            }
        
        if not settings.api_key:
            return {
                "success": False,
                "message": "KVK API key not configured"
            }
        
        # Test search API with a known KVK number (test number)
        test_kvk_number = "69599084"  # This is a commonly used test KVK number
        
        results = {
            "search_api": {"success": False, "message": ""},
            "basisprofiel_api": {"success": False, "message": ""},
            "overall_success": False
        }
        
        # Test search API
        try:
            search_result = search_kvk(kvk_nummer=test_kvk_number)
            if "error" not in search_result and search_result.get("resultaten"):
                results["search_api"]["success"] = True
                results["search_api"]["message"] = f"Successfully found {len(search_result['resultaten'])} results"
            else:
                results["search_api"]["message"] = search_result.get("error", "No results found")
        except Exception as e:
            results["search_api"]["message"] = f"Search API error: {str(e)}"
        
        # Test basisprofiel API
        try:
            basisprofiel_result = get_kvk_basisprofiel(test_kvk_number)
            if "error" not in basisprofiel_result and basisprofiel_result.get("kvkNummer"):
                results["basisprofiel_api"]["success"] = True
                results["basisprofiel_api"]["message"] = f"Successfully retrieved basisprofiel for {basisprofiel_result['kvkNummer']}"
            else:
                results["basisprofiel_api"]["message"] = basisprofiel_result.get("error", "No basisprofiel data found")
        except Exception as e:
            results["basisprofiel_api"]["message"] = f"Basisprofiel API error: {str(e)}"
        
        # Overall success if at least one API works
        results["overall_success"] = results["search_api"]["success"] or results["basisprofiel_api"]["success"]
        
        return results
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}"
        }