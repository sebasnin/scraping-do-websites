import json
import os
from typing import Any, List, Dict

def is_valid_value(value: Any) -> bool:
    """
    Check if a value is valid (not null, not empty string, not zero for numeric fields)
    """
    if value is None:
        return False
    
    if isinstance(value, str):
        return value.strip() != ""
    
    if isinstance(value, (int, float)):
        return value > 0
    
    return True

def validate_property(prop: Dict) -> tuple[bool, List[str]]:
    """
    Validate a property has all required fields with valid values
    Returns: (is_valid, list_of_missing_fields)
    """
    required_fields = [
        'price_dop',
        'price_usd', 
        'construccion',
        'parqueos',
        'banos',
        'habitaciones',
        'ubicacion'
    ]
    
    missing_fields = []
    
    for field in required_fields:
        value = prop.get(field)
        
        if not is_valid_value(value):
            missing_fields.append(field)
    
    is_valid = len(missing_fields) == 0
    return is_valid, missing_fields

def filter_complete_properties():
    """Filter properties to keep only those with all required fields complete"""
    
    # File paths
    input_file = '/home/sebastian/Documents/Scraping/scraping-do-websites/jsons/properties_data_complete.json'
    output_file = '/home/sebastian/Documents/Scraping/scraping-do-websites/jsons/properties_data_final.json'
    
    print("Loading properties data...")
    with open(input_file, 'r', encoding='utf-8') as f:
        properties = json.load(f)
    
    print(f"Loaded {len(properties)} properties")
    
    # Statistics
    valid_properties = []
    invalid_properties = []
    field_stats = {
        'price_dop': 0,
        'price_usd': 0,
        'construccion': 0,
        'parqueos': 0,
        'banos': 0,
        'habitaciones': 0,
        'ubicacion': 0
    }
    
    # Process each property
    for i, prop in enumerate(properties):
        is_valid, missing_fields = validate_property(prop)
        
        if is_valid:
            valid_properties.append(prop)
        else:
            invalid_properties.append({
                'codigo': prop.get('codigo', 'N/A'),
                'missing_fields': missing_fields
            })
            
            # Count missing fields for statistics
            for field in missing_fields:
                field_stats[field] += 1
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} properties...")
    
    # Save filtered data
    print(f"\nSaving filtered data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(valid_properties, f, ensure_ascii=False, indent=2)
    
    # Print statistics
    print(f"\n" + "="*60)
    print("PROPERTY FILTERING COMPLETE!")
    print(f"="*60)
    print(f"Total properties loaded: {len(properties)}")
    print(f"Valid properties (kept): {len(valid_properties)}")
    print(f"Invalid properties (dropped): {len(invalid_properties)}")
    print(f"Data quality: {(len(valid_properties)/len(properties))*100:.1f}%")
    
    print(f"\nMissing field breakdown:")
    print("-" * 30)
    for field, count in field_stats.items():
        if count > 0:
            print(f"  {field}: {count} properties missing")
    
    print(f"\nFinal clean data saved to: {output_file}")
    print(f"\n🎯 {len(valid_properties)} complete properties ready for database!")
    
    # Show examples of dropped properties (first 10)
    if invalid_properties:
        print(f"\n📋 Sample dropped properties (first 10):")
        print("-" * 50)
        for i, invalid_prop in enumerate(invalid_properties[:10]):
            print(f"Property {invalid_prop['codigo']}: Missing {', '.join(invalid_prop['missing_fields'])}")
    
    # Show final dataset characteristics
    print(f"\n📊 Final dataset characteristics:")
    print("-" * 40)
    
    if valid_properties:
        # Sample some statistics from valid properties
        prices_usd = [p['price_usd'] for p in valid_properties if p.get('price_usd')]
        areas = [p['construccion'] for p in valid_properties if p.get('construccion')]
        
        if prices_usd:
            avg_price_usd = sum(prices_usd) / len(prices_usd)
            min_price_usd = min(prices_usd)
            max_price_usd = max(prices_usd)
            print(f"Price USD - Avg: ${avg_price_usd:,.2f}, Min: ${min_price_usd:,.2f}, Max: ${max_price_usd:,.2f}")
        
        if areas:
            avg_area = sum(areas) / len(areas)
            min_area = min(areas)
            max_area = max(areas)
            print(f"Area (m²) - Avg: {avg_area:.2f}, Min: {min_area:.2f}, Max: {max_area:.2f}")
    
    print("\n✅ Dataset is now clean and ready for production use!")

if __name__ == "__main__":
    filter_complete_properties() 