import json
import requests
import re
import os
from typing import Dict, Tuple, Optional

def get_exchange_rate() -> float:
    """Get current USD to DOP exchange rate from API"""
    try:
        url = "https://v6.exchangerate-api.com/v6/c2cc9ccec8b882682142d13f/latest/USD"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get("result") == "success":
            dop_rate = data["conversion_rates"]["DOP"]
            print(f"✅ Current exchange rate: 1 USD = {dop_rate} DOP")
            return dop_rate
        else:
            raise Exception(f"API error: {data}")
            
    except Exception as e:
        print(f"❌ Error fetching exchange rate: {e}")
        print("📌 Using fallback rate: 1 USD = 60 DOP")
        return 60.0  # Fallback rate

def convert_currency(amount: float, from_currency: str, to_currency: str, usd_to_dop_rate: float) -> float:
    """Convert amount between USD and DOP"""
    if from_currency == to_currency:
        return amount
    
    if from_currency == "USD" and to_currency == "DOP":
        return amount * usd_to_dop_rate
    elif from_currency == "DOP" and to_currency == "USD":
        return amount / usd_to_dop_rate
    else:
        raise ValueError(f"Unsupported currency conversion: {from_currency} to {to_currency}")

def normalize_currency(currency_str: str) -> str:
    """Normalize currency string to USD or DOP"""
    if not currency_str:
        return "USD"  # Default to USD if no currency specified
    
    currency_clean = currency_str.strip().upper()
    
    # USD variations
    if currency_clean in ["USD", "US$", "$", "DOLLAR", "DOLLARS", "DOLARES", "DOLAR"]:
        return "USD"
    
    # DOP variations  
    if currency_clean in ["DOP", "RD$", "RD", "PESO", "PESOS", "DOMINICAN PESO"]:
        return "DOP"
    
    # Default to USD if unknown
    return "USD"

def process_properties_with_price_conversion():
    """Process properties JSON to add price_usd and price_dop fields"""
    
    # File paths
    input_file = '/home/sebastian/Documents/Scraping/scraping-do-websites/jsons/properties_data_final_standardized.json'
    output_file = '/home/sebastian/Documents/Scraping/scraping-do-websites/jsons/properties_data_with_prices.json'
    
    # Get current exchange rate
    usd_to_dop_rate = get_exchange_rate()
    
    print("\nLoading properties data...")
    with open(input_file, 'r', encoding='utf-8') as f:
        properties = json.load(f)
    
    print(f"Loaded {len(properties)} properties")
    
    # Statistics
    processed_count = 0
    usd_count = 0
    dop_count = 0
    no_price_count = 0
    invalid_price_count = 0
    
    # Process each property
    for i, prop in enumerate(properties):
        if 'price' in prop and prop['price'] is not None:
            try:
                # Get price amount
                price_amount = float(prop['price'])
                
                # Get currency (default to USD if not specified)
                currency = normalize_currency(prop.get('currency', 'USD'))
                
                # Create original_price field (combine amount and currency)
                if currency == "USD":
                    prop['original_price'] = f"${price_amount:,.2f}"
                else:
                    prop['original_price'] = f"RD${price_amount:,.2f}"
                
                # Convert prices
                if currency == "USD":
                    usd_count += 1
                    prop['price_usd'] = round(price_amount, 2)
                    prop['price_dop'] = round(convert_currency(price_amount, "USD", "DOP", usd_to_dop_rate), 2)
                elif currency == "DOP":
                    dop_count += 1
                    prop['price_dop'] = round(price_amount, 2)
                    prop['price_usd'] = round(convert_currency(price_amount, "DOP", "USD", usd_to_dop_rate), 2)
                
                processed_count += 1
                
            except (ValueError, TypeError) as e:
                invalid_price_count += 1
                # Set original price and null values for invalid prices
                prop['original_price'] = str(prop['price']) if prop['price'] else "N/A"
                prop['price_usd'] = None
                prop['price_dop'] = None
        else:
            no_price_count += 1
            # Set null values for missing prices
            prop['original_price'] = "N/A"
            prop['price_usd'] = None
            prop['price_dop'] = None
        
        # Remove the old price and currency fields
        if 'price' in prop:
            del prop['price']
        if 'currency' in prop:
            del prop['currency']
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} properties...")
    
    # Save updated data
    print(f"\nSaving updated data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(properties, f, ensure_ascii=False, indent=2)
    
    # Print statistics
    print(f"\n" + "="*60)
    print("PRICE CONVERSION COMPLETE!")
    print(f"="*60)
    print(f"Total properties processed: {len(properties)}")
    print(f"Properties with valid prices: {processed_count}")
    print(f"  - Originally in USD: {usd_count}")
    print(f"  - Originally in DOP: {dop_count}")
    print(f"Properties with no price: {no_price_count}")
    print(f"Properties with invalid price: {invalid_price_count}")
    print(f"Exchange rate used: 1 USD = {usd_to_dop_rate} DOP")
    
    print(f"\nUpdated data saved to: {output_file}")
    print("\n🎯 Properties now have original_price, price_usd, and price_dop fields!")
    
    # Show some examples
    print("\n📋 Sample conversions:")
    print("-" * 50)
    examples_shown = 0
    for prop in properties:
        if prop.get('price_usd') is not None and prop.get('price_dop') is not None:
            print(f"Original: {prop['original_price']}")
            print(f"  → USD: ${prop['price_usd']:,.2f}")
            print(f"  → DOP: RD${prop['price_dop']:,.2f}")
            print()
            examples_shown += 1
            if examples_shown >= 5:  # Show 5 examples
                break

if __name__ == "__main__":
    process_properties_with_price_conversion() 