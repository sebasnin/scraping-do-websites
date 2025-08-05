from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json

BASE_URL = "https://apartamentosrd.com.do"
SEARCH_URL = f"{BASE_URL}/propiedades?country=149&currency=RD&listing_type=1&page=1"

# Setup headless Chrome
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

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
        price_elements = driver.find_elements(By.XPATH, "//li[.//small]")
        
        for element in price_elements:
            try:
                small_text = element.find_element(By.TAG_NAME, "small").text.strip()
                span_text = element.find_element(By.TAG_NAME, "span").text.strip()
                
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
        
        print(f"Found {len(pricing_options)} pricing options")
        for option in pricing_options:
            print(f"  {option['label']}: {option['price']} ({option['transaction_type']})")
        
        # Filter out "Amueblado" options when there are multiple rent options
        if len(pricing_options) > 1:
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
            
    except Exception as e:
        print(f"Error extracting pricing options: {e}")
        pricing_options = [{'transaction_type': 'venta', 'price': 'Not found', 'label': 'Venta'}]
    
    # If no pricing options found, create a default one
    if not pricing_options:
        pricing_options = [{'transaction_type': 'venta', 'price': 'Not found', 'label': 'Venta'}]
    
    # Create separate property data for each pricing option
    property_variants = []
    
    for pricing_option in pricing_options:
        # Initialize data dictionary for this variant
        property_data = {
            'url': url,
            'transaction_type': pricing_option['transaction_type'],
            'price': pricing_option['price'],
            'price_label': pricing_option['label'],
            'codigo': 'Not found',
            'tipo_inmueble': 'Not found',
            'ciudad': 'Not found',
            'sector': 'Not found',
            'habitaciones': 'Not found',
            'banos': 'Not found',
            'parqueos': 'Not found',
            'construccion': 'Not found',
            'description': 'Not found',
            'amenities': [],
            'timestamp': 'Not found',
            'images': []
        }
        
        print(f"\nProcessing {pricing_option['transaction_type']} variant: {pricing_option['price']}")
    
        # Get property details from the resumen section
        try:
            resumen_section = driver.find_element(By.CSS_SELECTOR, "ul.sc-dMOLTJ.bCulV")
            detail_items = resumen_section.find_elements(By.TAG_NAME, "li")
            
            property_details = {}
            
            for item in detail_items:
                label_element = item.find_element(By.CSS_SELECTOR, "span.d-block")
                label = label_element.text.strip()
                
                full_text = item.text.strip()
                value = full_text.replace(label, "").strip()
                value = " ".join(value.split())
                
                property_details[label] = value
                print(f"{label}: {value}")
            
            # Extract specific details
            property_data['codigo'] = property_details.get("Código", "Not found")
            property_data['tipo_inmueble'] = property_details.get("Tipo de Inmueble", "Not found")
            property_data['ciudad'] = property_details.get("Ciudad", "Not found")
            property_data['sector'] = property_details.get("Sector", "Not found")
            property_data['habitaciones'] = property_details.get("Habitaciones", "Not found")
            property_data['banos'] = property_details.get("Baños", "Not found")
            property_data['parqueos'] = property_details.get("Parqueos", "Not found")
            property_data['construccion'] = property_details.get("Construcción", "Not found")
            
        except Exception as e:
            print(f"Error extracting property details: {e}")
        
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
            amenities_section = driver.find_element(By.CSS_SELECTOR, "div#amenities")
            amenities_items = amenities_section.find_elements(By.CSS_SELECTOR, "ul.sc-cWSHoV.sdWSK li")
            
            amenities_list = []
            for item in amenities_items:
                amenity_text = item.find_element(By.TAG_NAME, "span").text.strip()
                if amenity_text:
                    amenities_list.append(amenity_text)
            
            property_data['amenities'] = amenities_list
            print(f"Amenities: {len(amenities_list)} found")
            
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
        
        # Get property images
        try:
            image_elements = driver.find_elements(By.CSS_SELECTOR, "div.carousel-cell img")
            
            image_urls = []
            for img in image_elements:
                src = img.get_attribute("src")
                if src and src not in image_urls:
                    image_urls.append(src)
            
            property_data['images'] = image_urls
            print(f"Images found: {len(image_urls)}")
            
        except Exception as e:
            print(f"Error extracting images: {e}")
        
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
                'images': []
            })
    
    return all_properties

if __name__ == "__main__":
    try:
        # Scrape all properties (limit to 5 for testing)
        properties_data = scrape_all_properties(max_properties=5)
        
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