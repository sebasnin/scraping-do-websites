from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from shapely.geometry import Point, shape
import time
import json
import os
import requests
import csv
import pandas as pd

BASE_URL = "https://apartamentosrd.com.do"
SEARCH_URL = f"{BASE_URL}/propiedades?country=149&currency=RD&listing_type=1&page=1"

# Load environment variables (for GOOGLE_MAPS_API_KEY)
load_dotenv()

# Setup headless Chrome
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def get_traffic_scores(neighborhood_id):
    """Get traffic scores from local CSV file based on neighborhood_id (fid from barrios2.geojson)"""
    try:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scores.csv')
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row in csv_reader:
                if str(row['fid']).strip() == str(neighborhood_id).strip():
                    return {
                        'traffic_score_0830': float(row['08:30']),
                        'traffic_score_1330': float(row['13:30']),
                        'traffic_score_1700': float(row['17:00']),
                        'traffic_score_total': float(row['total'])
                    }
        return None
    except Exception as e:
        print(f"Error reading traffic scores CSV: {e}")
        return None


def get_density_score(neighborhood_id):
    """Get density score from local CSV file based on neighborhood_id"""
    try:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'population_density_results.csv')
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Find the matching row based on neighborhood_id (polygon_id in the CSV)
        matching_row = df[df['polygon_id'] == int(neighborhood_id)]

        if not matching_row.empty:
            return {
                'density': float(matching_row['density'].iloc[0]),
                'score': float(matching_row['score'].iloc[0])
            }
        return None
    except Exception as e:
        print(f"Error reading density CSV: {e}")
        return None


def get_proximity_score(neighborhood_id):
    """Get proximity score from local CSV file based on neighborhood_id"""
    try:
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'proximity_scores.csv')
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        # Find the matching row based on neighborhood_id (ID in the CSV)
        matching_row = df[df['ID'] == int(neighborhood_id)]

        if not matching_row.empty:
            return float(matching_row['Overall_Score'].iloc[0])
        return None
    except Exception as e:
        print(f"Error reading proximity scores CSV: {e}")
        return None


def get_neighborhood_from_coordinates(longitude, latitude):
    """
    Determine neighborhood from coordinates using local barrios2.geojson
    Returns (neighborhood_name, neighborhood_id) tuple
    """
    try:
        point = Point(longitude, latitude)
        
        # Use local GeoJSON file
        geojson_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'barrios2.geojson')
        with open(geojson_path, 'r', encoding='utf-8') as f:
            neighborhoods_data = json.load(f)
            
        for feature in neighborhoods_data['features']:
            if not feature.get('geometry'):
                continue
                
            polygon = shape(feature['geometry'])
            
            if polygon.bounds[0] <= longitude <= polygon.bounds[2] and \
               polygon.bounds[1] <= latitude <= polygon.bounds[3]:
                if polygon.contains(point):
                    return (
                        feature['properties']['TOPONIMIA'],
                        feature['properties']['fid']
                    )
        
        return None, None
    except Exception as e:
        print(f"Error reading neighborhoods GeoJSON: {e}")
        return None, None


def get_city_from_coordinates(longitude, latitude):
    """
    Determine city from coordinates using local provincias.geojson
    Returns (city_name, city_id) tuple
    """
    try:
        point = Point(longitude, latitude)
        
        # Use local GeoJSON file
        geojson_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'provincias.geojson')
        with open(geojson_path, 'r', encoding='utf-8') as f:
            cities_data = json.load(f)
            
        # Check each polygon with bounding box optimization
        for feature in cities_data['features']:
            if not feature.get('geometry'):
                continue
                
            polygon = shape(feature['geometry'])
            
            # Quick check using bounding box
            if polygon.bounds[0] <= longitude <= polygon.bounds[2] and \
               polygon.bounds[1] <= latitude <= polygon.bounds[3]:
                # Only do the expensive contains check if point is in bounding box
                if polygon.contains(point):
                    return (
                        feature['properties']['TOPONIMIA'],  # City name
                        feature['properties']['fid']         # City ID
                    )
        
        return None, None
    except Exception as e:
        print(f"Error reading cities GeoJSON: {e}")
        return None, None


def geocode_address(address: str):
    """Return (latitude, longitude) for a given address using Google Geocoding API.

    Reads the API key from the environment variable `GOOGLE_MAPS_API_KEY` (loaded via load_dotenv).
    Returns (None, None) on failure.
    """
    try:
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            print("GOOGLE_MAPS_API_KEY not found in environment")
            return None, None

        params = {
            "address": address,
            "key": api_key,
            # Bias results to Dominican Republic
            "components": "country:DO",
        }
        resp = requests.get(
            "https://maps.gomaps.pro/maps/api/geocode/json",
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"Geocoding HTTP error: {resp.status_code}")
            return None, None
        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            print(f"Geocoding failed: {data.get('status')} - {data.get('error_message', '')}")
            return None, None
        loc = data["results"][0]["geometry"]["location"]
        return float(loc.get("lat")), float(loc.get("lng"))
    except Exception as e:
        print(f"Error in geocode_address: {e}")
        return None, None

def get_listing_links(listing_type=1):
    """Get all property listing links from all pages for a specific listing type"""
    listing_name = "SALE" if listing_type == 1 else "RENT"
    print(f"Getting {listing_name} property links from all pages...")
    all_links = []
    page = 1
    max_pages = 2 # Safety limit to prevent infinite loops
    
    while page <= max_pages:
        print(f"Scraping {listing_name} page {page}...")
        page_url = f"{BASE_URL}/propiedades?country=149&currency=RD&listing_type={listing_type}&page={page}"
        driver.get(page_url)
        time.sleep(5)  # Wait for JS to load
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_links = []
        
        # Find all property links on this page
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("/propiedad/") and href not in all_links:
                page_links.append(BASE_URL + href)
        
        # If no new links found on this page, we've reached the end
        if not page_links:
            print(f"No new {listing_name} properties found on page {page}. Reached the end.")
            break
        
        all_links.extend(page_links)
        print(f"Found {len(page_links)} new {listing_name} properties on page {page} (Total: {len(all_links)})")
        
        # Check if there's a next page by looking for pagination buttons
        next_page_exists = False
        pagination_buttons = soup.find_all("button", {"name": "page"})
        
        for button in pagination_buttons:
            try:
                button_value = button.get("value", "")
                if button_value.isdigit() and int(button_value) == page + 1:
                    next_page_exists = True
                    break
            except (ValueError, AttributeError):
                continue
        
        # If no next page found, we've reached the end
        if not next_page_exists:
            print(f"No next {listing_name} page found. Reached the end at page {page}.")
            break
        
        page += 1
        
        # Add a small delay between pages to be respectful
        time.sleep(2)
    
    if page > max_pages:
        print(f"Reached maximum page limit ({max_pages}). Stopping {listing_name} pagination.")
    
    print(f"Total {listing_name} property links found across all pages: {len(all_links)}")
    return all_links

def get_all_listing_links():
    """Get all property listing links from both sale and rent listings"""
    print("Getting all property links (SALE + RENT)...")
    
    # First get sale properties (listing_type=1)
    sale_links = get_listing_links(listing_type=1)
    
    # Then get rent properties (listing_type=2)
    rent_links = get_listing_links(listing_type=2)
    
    # Combine all links
    all_links = sale_links + rent_links
    
    print(f"Total property links found (SALE: {len(sale_links)}, RENT: {len(rent_links)}, TOTAL: {len(all_links)})")
    return all_links

def extract_property_details(url):
    """Extract detailed information from a single property page"""
    print(f"Scraping: {url}")
    
    driver.get(url)
    time.sleep(3)  # Wait for content to load
    
    # Get all pricing options
    pricing_options = []
    try:
        # 1) Scoped to the main pricing column in the property header
        price_elements = driver.find_elements(
            By.XPATH,
            "//div[@id='property_content']//div[@id='property-details']//div[contains(@class,'col-md-4')]//ul/li"
        )

        for element in price_elements:
            try:
                # robustly read label and amount regardless of order
                small_el = element.find_element(By.TAG_NAME, "small")
                span_el = element.find_element(By.TAG_NAME, "span")
                small_text = small_el.text.strip()
                span_text = span_el.text.strip()

                # Skip "DESDE" and "HASTA" pricing options
                if small_text.upper() in ["DESDE", "HASTA"]:
                    print(f"Skipping range pricing: {small_text} - {span_text}")
                    continue

                # Map transaction types
                transaction_type = "venta"  # default
                if "ALQUILER" in small_text.upper():
                    transaction_type = "alquiler"
                elif "VENTA" in small_text.upper():
                    transaction_type = "venta"

                pricing_options.append({
                    'transaction_type': transaction_type,
                    'price': span_text,
                    'label': small_text
                })

            except Exception as e:
                print(f"Error parsing price element: {e}")

        # 2) Fallback: pull structured prices from __NEXT_DATA__ if none found in DOM
        if not pricing_options:
            try:
                print("No DOM price elements found; falling back to __NEXT_DATA__ JSON")
                script_element = driver.find_element(By.CSS_SELECTOR, "script#__NEXT_DATA__")
                data = json.loads(script_element.get_attribute("innerHTML"))
                prop = data['props']['pageProps']['property']

                def currency_prefix(code: str) -> str:
                    if not code:
                        return ""
                    c = code.upper()
                    if c in ("USD", "US", "US$"):
                        return "US$"
                    if c in ("DOP", "RD", "RD$"):
                        return "RD$"
                    return f"{c}$"

                def format_amount(value) -> str:
                    try:
                        num = float(value)
                        # keep decimals only when needed
                        if abs(num - int(num)) < 1e-9:
                            return f"{int(num):,}"
                        return f"{num:,.2f}"
                    except Exception:
                        return str(value)

                # Build options from known fields
                sale_price = prop.get('sale_price')
                rent_price = prop.get('rent_price')
                rental_price = prop.get('rental_price')
                furnished_sale_price = prop.get('furnished_sale_price')

                if sale_price:
                    cur = currency_prefix(prop.get('currency_sale'))
                    pricing_options.append({
                        'transaction_type': 'venta',
                        'price': f"{cur} {format_amount(sale_price)}",
                        'label': 'VENTA'
                    })
                if furnished_sale_price:
                    cur = currency_prefix(prop.get('currency_sale_furnished') or prop.get('currency_sale'))
                    pricing_options.append({
                        'transaction_type': 'venta',
                        'price': f"{cur} {format_amount(furnished_sale_price)}",
                        'label': 'VENTA AMUEBLADO'
                    })
                if rent_price:
                    cur = currency_prefix(prop.get('currency_rent'))
                    pricing_options.append({
                        'transaction_type': 'alquiler',
                        'price': f"{cur} {format_amount(rent_price)}",
                        'label': 'ALQUILER'
                    })
                if rental_price:
                    cur = currency_prefix(prop.get('currency_rental') or prop.get('currency_rent'))
                    pricing_options.append({
                        'transaction_type': 'alquiler',
                        'price': f"{cur} {format_amount(rental_price)}",
                        'label': 'ALQUILER'
                    })

            except Exception as e:
                print(f"Fallback to __NEXT_DATA__ failed: {e}")

        print(f"Found {len(pricing_options)} pricing options")
        for option in pricing_options:
            print(f"  {option['label']}: {option['price']} ({option['transaction_type']})")

        # Filter out "Amueblado" options when there are multiple options of the same type
        if len(pricing_options) > 1:
            # Handle rent options
            rent_options = [opt for opt in pricing_options if opt['transaction_type'] == 'alquiler']
            if len(rent_options) > 1:
                # Keep only the base "Alquiler" option, filter out "Amueblado"
                base_rent_options = [opt for opt in rent_options if 'AMUEBLADO' not in opt['label'].upper()]
                furnished_rent_options = [opt for opt in rent_options if 'AMUEBLADO' in opt['label'].upper()]

                if base_rent_options and furnished_rent_options:
                    print(f"Multiple rent options found. Keeping base 'Alquiler' and filtering out 'Amueblado' variants.")
                    # Replace rent options with only base options
                    other_options = [opt for opt in pricing_options if opt['transaction_type'] != 'alquiler']
                    pricing_options = base_rent_options + other_options
                    print(f"After filtering: {len(pricing_options)} pricing options")
                    for option in pricing_options:
                        print(f"  {option['label']}: {option['price']} ({option['transaction_type']})")

            # Handle sale options
            sale_options = [opt for opt in pricing_options if opt['transaction_type'] == 'venta']
            if len(sale_options) > 1:
                # Keep only the base "Venta" option, filter out "Amueblado"
                base_sale_options = [opt for opt in sale_options if 'AMUEBLADO' not in opt['label'].upper()]
                furnished_sale_options = [opt for opt in sale_options if 'AMUEBLADO' in opt['label'].upper()]

                if base_sale_options and furnished_sale_options:
                    print(f"Multiple sale options found. Keeping base 'Venta' and filtering out 'Amueblado' variants.")
                    # Replace sale options with only base options
                    other_options = [opt for opt in pricing_options if opt['transaction_type'] != 'venta']
                    pricing_options = base_sale_options + other_options
                    print(f"After filtering: {len(pricing_options)} pricing options")
                    for option in pricing_options:
                        print(f"  {option['label']}: {option['price']} ({option['transaction_type']})")

    except Exception as e:
        print(f"Error extracting pricing options: {e}")
        pricing_options = [{'transaction_type': 'venta', 'price': 'Not found', 'label': 'Venta'}]
    
    # If no pricing options found, create a default one
    if not pricing_options:
        pricing_options = [{'transaction_type': 'venta', 'price': 'Not found', 'label': 'Venta'}]
    
    # Create separate property data for each pricing option
    property_variants = []
    # Cache geocoding results per ubicacion string within this property
    geocoded_coords_cache = {}
    
    for pricing_option in pricing_options:
        # Parse currency and amount from pricing text
        price_text_raw = (pricing_option.get('price') or '').strip()
        def detect_currency_code(text: str) -> str:
            t = (text or '').upper()
            if 'US$' in t or 'USD' in t:
                return 'USD'
            if 'RD$' in t or 'DOP' in t or 'RD ' in t:
                return 'DOP'
            return None
        def parse_int_amount(text: str):
            s = (text or '').replace('US$', '').replace('RD$', '')
            s = s.replace(',', '').replace(' ', '')
            # keep only digits and dot
            import re
            s = ''.join(re.findall(r"[0-9.]+", s))
            try:
                if s == '':
                    return None
                return int(float(s))
            except Exception:
                return None
        currency_code = detect_currency_code(price_text_raw)
        price_int = parse_int_amount(price_text_raw)
        
        # Initialize data dictionary for this variant
        property_data = {
            'url': url,
            'transaction_type': pricing_option['transaction_type'],
            'price': price_int,
            'currency': currency_code or 'Not found',
            'price_label': pricing_option['label'],
            'codigo': 'Not found',
            'tipo_inmueble': 'Not found',
            'ciudad': 'Not found',
            'sector': 'Not found',
            'habitaciones': None,
            'banos': None,
            'parqueos': None,
            'construccion': None,
            'description': 'Not found',
            'amenities': [],
            'timestamp': 'Not found',
            'images': [],
            'latitude': None,
            'longitude': None,
            'neighborhood_name': None,
            'neighborhood_id': None,
            'city_name': None,
            'city_id': None,
            'traffic_score_0830': None,
            'traffic_score_1330': None,
            'traffic_score_1700': None,
            'traffic_score_total': None,
            'density_score': None,
            'density_value': None,
            'proximity_score': None
        }
        
        print(f"\nProcessing {pricing_option['transaction_type']} variant: {pricing_option['price']}")
    
        # Get property details from the resumen section
        try:
            # Prefer selecting the overview card by ID and then its list items
            detail_items = driver.find_elements(By.CSS_SELECTOR, "div#overview ul li")
            
            property_details = {}
            
            for item in detail_items:
                try:
                    label_element = item.find_element(By.CSS_SELECTOR, "span.d-block")
                except Exception:
                    # If the item doesn't have a label span, skip it
                    continue
                label = label_element.text.strip()
                
                # The LI text contains the value followed by the label. Remove the label to get the value.
                full_text = item.text.strip()
                value = full_text.replace(label, "").strip()
                value = " ".join(value.split())
                
                property_details[label] = value
                print(f"{label}: {value}")
            
            # Extract specific details from parsed labels
            property_data['codigo'] = property_details.get("Código", property_data['codigo'])
            property_data['tipo_inmueble'] = property_details.get("Tipo de Inmueble", property_data['tipo_inmueble'])
            property_data['ciudad'] = property_details.get("Ciudad", property_data['ciudad'])
            property_data['sector'] = property_details.get("Sector", property_data['sector'])
            # numeric casts
            def to_int(val):
                try:
                    if val is None or val == 'Not found':
                        return None
                    s = str(val).strip().replace(',', '.')
                    import re
                    s = ''.join(re.findall(r"[0-9.]+", s))
                    if s == '':
                        return None
                    return int(float(s))
                except Exception:
                    return None
            def to_float(val):
                try:
                    if val is None or val == 'Not found':
                        return None
                    s = str(val).strip().replace(',', '.')
                    import re
                    s = ''.join(re.findall(r"[0-9.]+", s))
                    if s == '':
                        return None
                    return float(s)
                except Exception:
                    return None
            property_data['habitaciones'] = to_int(property_details.get("Habitaciones", property_data['habitaciones']))
            property_data['banos'] = to_int(property_details.get("Baños", property_data['banos']) or property_details.get("Banos", property_data['banos']))
            property_data['parqueos'] = to_int(property_details.get("Parqueos", property_data['parqueos']))
            property_data['construccion'] = to_float(property_details.get("Construcción", property_data['construccion']) or property_details.get("Construccion", property_data['construccion']))
            
        except Exception as e:
            print(f"Error extracting property details: {e}")
        
        # Fallback: fill any missing details from __NEXT_DATA__ JSON
        try:
            script_element = driver.find_element(By.CSS_SELECTOR, "script#__NEXT_DATA__")
            data = json.loads(script_element.get_attribute("innerHTML"))
            prop = data['props']['pageProps']['property']
            
            # Helper for safe value assignment
            def assign_if_missing(key, value):
                if not property_data.get(key) or property_data.get(key) == 'Not found':
                    if value is not None and value != "":
                        property_data[key] = str(value)
            
            assign_if_missing('codigo', prop.get('cid'))
            category = prop.get('category') or {}
            assign_if_missing('tipo_inmueble', category.get('name'))
            assign_if_missing('ciudad', prop.get('city'))
            assign_if_missing('sector', prop.get('sector'))
            assign_if_missing('habitaciones', prop.get('room'))
            assign_if_missing('banos', prop.get('bathroom'))
            assign_if_missing('parqueos', prop.get('parkinglot'))
            
            # Construcción as float (m2)
            if (property_data.get('construccion') is None):
                area = prop.get('property_area')
                if area is not None:
                    try:
                        property_data['construccion'] = float(area)
                    except Exception:
                        pass
            # If currency still missing, derive from JSON currencies
            if (property_data.get('currency') == 'Not found'):
                cur_code = None
                if pricing_option['transaction_type'] == 'venta':
                    cur_code = (prop.get('currency_sale_furnished') or prop.get('currency_sale'))
                else:
                    cur_code = (prop.get('currency_rent') or prop.get('currency_rental'))
                if cur_code:
                    c = cur_code.upper()
                    if c in ('USD', 'US'):
                        property_data['currency'] = 'USD'
                    elif c in ('DOP', 'RD'):
                        property_data['currency'] = 'DOP'
        except Exception as e:
            print(f"Fallback details from __NEXT_DATA__ failed: {e}")
        
        # Get property description
        try:
            description_section = driver.find_element(By.CSS_SELECTOR, "div#description")
            description_paragraphs = description_section.find_elements(By.TAG_NAME, "p")
            
            description_text = ""
            for p in description_paragraphs:
                if p.text.strip():
                    description_text += p.text.strip() + " "
            
            description_text = description_text.strip()
            property_data['description'] = description_text
            print(f"Description: {description_text[:100]}...")
            
        except Exception as e:
            print(f"Error extracting description: {e}")
        
        # Get property amenities
        try:
            amenities_list = []
            
            # Primary: scrape from DOM under the Amenidades card
            amenity_spans = driver.find_elements(By.CSS_SELECTOR, "div#amenities ul li span")
            for span in amenity_spans:
                text = (span.text or "").strip()
                if text:
                    amenities_list.append(text)
            
            # Fallback: use __NEXT_DATA__ amenities if DOM yielded none
            if not amenities_list:
                try:
                    script_element = driver.find_element(By.CSS_SELECTOR, "script#__NEXT_DATA__")
                    data = json.loads(script_element.get_attribute("innerHTML"))
                    prop = data['props']['pageProps']['property']
                    for a in prop.get('amenities', []) or []:
                        if a and isinstance(a, str):
                            amenities_list.append(a.strip())
                except Exception as _e:
                    pass
            
            # Deduplicate while preserving order
            seen = set()
            deduped = []
            for a in amenities_list:
                if a not in seen:
                    seen.add(a)
                    deduped.append(a)
            
            property_data['amenities'] = deduped
            print(f"Amenities: {len(deduped)} found")
            
        except Exception as e:
            print(f"Error extracting amenities: {e}")
        
        # Get publication timestamp
        try:
            script_element = driver.find_element(By.CSS_SELECTOR, "script#__NEXT_DATA__")
            script_content = script_element.get_attribute("innerHTML")
            
            data = json.loads(script_content)
            property_info = data['props']['pageProps']['property']
            timestamp = property_info.get('timestamp', 'Not found')
            
            property_data['timestamp'] = timestamp
            print(f"Publication Date: {timestamp}")
            
        except Exception as e:
            print(f"Error extracting timestamp: {e}")
        
        # Build ubicacion as "<Sector>, <Ciudad>, Dominican Republic"
        try:
            parts = []
            sector_val = property_data.get('sector')
            ciudad_val = property_data.get('ciudad')
            if sector_val and str(sector_val).strip() and str(sector_val) != 'Not found':
                parts.append(str(sector_val).strip())
            if ciudad_val and str(ciudad_val).strip() and str(ciudad_val) != 'Not found':
                parts.append(str(ciudad_val).strip())
            parts.append('Dominican Republic')
            property_data['ubicacion'] = ', '.join(parts)
        except Exception:
            property_data['ubicacion'] = 'Dominican Republic'

        # Geocode latitude/longitude using Google Maps API
        try:
            address = property_data.get('ubicacion')
            if address:
                if address not in geocoded_coords_cache:
                    lat, lng = geocode_address(address)
                    geocoded_coords_cache[address] = (lat, lng)
                else:
                    lat, lng = geocoded_coords_cache[address]
                property_data['latitude'] = lat
                property_data['longitude'] = lng
                if lat is not None and lng is not None:
                    print(f"Geocoded: {lat}, {lng}")
                    
                    # Get neighborhood and city from coordinates
                    try:
                        neighborhood_name, neighborhood_id = get_neighborhood_from_coordinates(lng, lat)
                        city_name, city_id = get_city_from_coordinates(lng, lat)
                        
                        property_data['neighborhood_name'] = neighborhood_name
                        property_data['neighborhood_id'] = neighborhood_id
                        property_data['city_name'] = city_name
                        property_data['city_id'] = city_id
                        
                        if neighborhood_name:
                            print(f"Neighborhood: {neighborhood_name} (ID: {neighborhood_id})")
                        if city_name:
                            print(f"City: {city_name} (ID: {city_id})")
                        
                        # Get scores based on neighborhood_id and city_id
                        try:
                            # Get traffic scores using neighborhood_id (fid from barrios2.geojson)
                            if neighborhood_id:
                                traffic_scores = get_traffic_scores(neighborhood_id)
                                if traffic_scores:
                                    property_data.update(traffic_scores)
                                    print(f"Traffic scores: 08:30={traffic_scores['traffic_score_0830']}, 13:30={traffic_scores['traffic_score_1330']}, 17:00={traffic_scores['traffic_score_1700']}, Total={traffic_scores['traffic_score_total']}")
                            
                            # Get density score using neighborhood_id (fid from barrios2.geojson)
                            if neighborhood_id:
                                density_data = get_density_score(neighborhood_id)
                                if density_data:
                                    property_data['density_score'] = density_data['score']
                                    property_data['density_value'] = density_data['density']
                                    print(f"Density: score={density_data['score']}, value={density_data['density']}")
                            
                            # Get proximity score using neighborhood_id (fid from barrios2.geojson)
                            if neighborhood_id:
                                proximity_score = get_proximity_score(neighborhood_id)
                                if proximity_score is not None:
                                    property_data['proximity_score'] = proximity_score
                                    print(f"Proximity score: {proximity_score}")
                                    
                        except Exception as e:
                            print(f"Error getting scores: {e}")
                            
                    except Exception as e:
                        print(f"Error getting neighborhood/city from coordinates: {e}")
                        property_data['neighborhood_name'] = None
                        property_data['neighborhood_id'] = None
                        property_data['city_name'] = None
                        property_data['city_id'] = None
                else:
                    print("Geocoding returned no coordinates")
                    property_data['neighborhood_name'] = None
                    property_data['neighborhood_id'] = None
                    property_data['city_name'] = None
                    property_data['city_id'] = None
        except Exception as e:
            print(f"Error geocoding ubicacion: {e}")
            property_data['neighborhood_name'] = None
            property_data['neighborhood_id'] = None
            property_data['city_name'] = None
            property_data['city_id'] = None

        # Add this variant to the list
        property_variants.append(property_data)
    
    return property_variants

def scrape_all_properties(max_properties=None):
    """Scrape all properties and return a list of JSON objects"""
    print("Starting comprehensive property scraping...")
    
    # Get all property links (both sale and rent)
    property_links = get_all_listing_links()
    
    if max_properties:
        property_links = property_links[:max_properties]
        print(f"Limiting to {max_properties} properties")
    
    # Scrape each property
    all_properties = []
    
    for i, link in enumerate(property_links, 1):
        print(f"\n{'='*50}")
        print(f"Scraping property {i}/{len(property_links)}")
        print(f"{'='*50}")
        
        try:
            property_variants = extract_property_details(link)
            all_properties.extend(property_variants)
            print(f"✅ Successfully scraped property {i} ({len(property_variants)} variants)")
        except Exception as e:
            print(f"❌ Error scraping property {i}: {e}")
            # Add error entry
            all_properties.append({
                'url': link,
                'error': str(e),
                'transaction_type': 'venta',
                'price': 'Error',
                'price_label': 'Error',
                'codigo': 'Error',
                'tipo_inmueble': 'Error',
                'ciudad': 'Error',
                'sector': 'Error',
                'habitaciones': 'Error',
                'banos': 'Error',
                'parqueos': 'Error',
                'construccion': 'Error',
                'description': 'Error',
                'amenities': [],
                'timestamp': 'Error',
                'images': [],
                'latitude': None,
                'longitude': None,
                'neighborhood_name': None,
                'neighborhood_id': None,
                'city_name': None,
                'city_id': None,
                'traffic_score_0830': None,
                'traffic_score_1330': None,
                'traffic_score_1700': None,
                'traffic_score_total': None,
                'density_score': None,
                'density_value': None,
                'proximity_score': None
            })
    
    return all_properties

if __name__ == "__main__":
    try:
        # Scrape all properties (limit to 5 for testing)
        properties_data = scrape_all_properties(max_properties=30)
        
        # Save to JSON file in jsons folder
        import os
        
        # Create jsons directory if it doesn't exist
        jsons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'jsons')
        os.makedirs(jsons_dir, exist_ok=True)
        
        output_file = os.path.join(jsons_dir, "properties_data.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(properties_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*50}")
        print("SCRAPING COMPLETED!")
        print(f"{'='*50}")
        print(f"Total properties scraped: {len(properties_data)}")
        print(f"Data saved to: {output_file}")
        
        # Print summary
        successful_scrapes = sum(1 for p in properties_data if p.get('price') != 'Error')
        print(f"Successful scrapes: {successful_scrapes}")
        print(f"Failed scrapes: {len(properties_data) - successful_scrapes}")
        
    except Exception as e:
        print(f"Error in main execution: {e}")
    
    finally:
        driver.quit() 