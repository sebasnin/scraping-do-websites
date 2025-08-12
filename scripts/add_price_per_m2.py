import json
import os
from typing import Optional

def calculate_price_per_m2(price: Optional[float], area: Optional[float]) -> Optional[float]:
    """
    Calculate price per square meter
    Returns None if price or area is invalid
    """
    if not price or not area or area <= 0:
        return None
    
    try:
        price_per_m2 = price / area
        return round(price_per_m2, 2)
    except (TypeError, ZeroDivisionError):
        return None

def add_price_per_m2_fields():
    """Add price_per_m2_usd and price_per_m2_dop fields to properties"""
    
    # File paths
    input_file = '/home/sebastian/Documents/Scraping/scraping-do-websites/jsons/properties_data_with_prices.json'
    output_file = '/home/sebastian/Documents/Scraping/scraping-do-websites/jsons/properties_data_complete.json'
    
    print("Loading properties data...")
    with open(input_file, 'r', encoding='utf-8') as f:
        properties = json.load(f)
    
    print(f"Loaded {len(properties)} properties")
    
    # Statistics
    valid_calculations = 0
    missing_area = 0
    missing_price = 0
    invalid_area = 0
    
    # Process each property
    for i, prop in enumerate(properties):
        area = prop.get('construccion')
        price_usd = prop.get('price_usd')
        price_dop = prop.get('price_dop')
        
        # Check if we have valid area data
        if not area or area <= 0:
            if not area:
                missing_area += 1
            else:
                invalid_area += 1
            prop['price_per_m2_usd'] = None
            prop['price_per_m2_dop'] = None
        # Check if we have valid price data
        elif not price_usd or not price_dop:
            missing_price += 1
            prop['price_per_m2_usd'] = None
            prop['price_per_m2_dop'] = None
        else:
            # Calculate price per m² for both currencies
            prop['price_per_m2_usd'] = calculate_price_per_m2(price_usd, area)
            prop['price_per_m2_dop'] = calculate_price_per_m2(price_dop, area)
            
            if prop['price_per_m2_usd'] is not None:
                valid_calculations += 1
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} properties...")
    
    # Save updated data
    print(f"\nSaving updated data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(properties, f, ensure_ascii=False, indent=2)
    
    # Print statistics
    print(f"\n" + "="*60)
    print("PRICE PER M² CALCULATION COMPLETE!")
    print(f"="*60)
    print(f"Total properties processed: {len(properties)}")
    print(f"Properties with valid price/m² calculations: {valid_calculations}")
    print(f"Properties missing area data: {missing_area}")
    print(f"Properties with invalid area (≤ 0): {invalid_area}")
    print(f"Properties missing price data: {missing_price}")
    
    success_rate = (valid_calculations / len(properties)) * 100
    print(f"Success rate: {success_rate:.1f}%")
    
    print(f"\nUpdated data saved to: {output_file}")
    print("\n🎯 Properties now have price_per_m2_usd and price_per_m2_dop fields!")
    
    # Show some examples
    print("\n📋 Sample price/m² calculations:")
    print("-" * 60)
    examples_shown = 0
    
    for prop in properties:
        if (prop.get('price_per_m2_usd') is not None and 
            prop.get('price_per_m2_dop') is not None and 
            prop.get('construccion')):
            
            print(f"Property: {prop.get('codigo', 'N/A')}")
            print(f"  Area: {prop['construccion']:.2f} m²")
            print(f"  Total Price USD: ${prop.get('price_usd', 0):,.2f}")
            print(f"  Total Price DOP: RD${prop.get('price_dop', 0):,.2f}")
            print(f"  → Price/m² USD: ${prop['price_per_m2_usd']:,.2f}")
            print(f"  → Price/m² DOP: RD${prop['price_per_m2_dop']:,.2f}")
            print()
            
            examples_shown += 1
            if examples_shown >= 5:  # Show 5 examples
                break
    
    print("✅ Ready for final database upload!")

if __name__ == "__main__":
    add_price_per_m2_fields() 