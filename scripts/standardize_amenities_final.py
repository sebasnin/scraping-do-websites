import json
import os
import re
from typing import Dict, List, Set

def create_final_amenity_mapping() -> Dict[str, str]:
    """Create comprehensive mapping from current amenities to standardized categories"""
    
    # Define the standard categories available in your DB
    SERVICE_CHOICES = [
        'Aire acondicionado',
        'Gas común', 
        'Gimnasio',
        'Inversor',
        'Planta eléctrica',
        'Seguridad 24 Horas',
        'Calefacción',
        'Cisterna',
    ]

    GENERAL_CHARACTERISTICS = [
        'Acceso a la playa',
        'Acceso para personas con discapacidad',
        'Amueblado',
        'Ascensor',
        'Intercom',
        'Jacuzzi',
        'Mascotas permitidas',
        'Piscina',
        'Portón eléctrico',
        'Residencial cerrado',
        'Recepción',
    ]

    EXTERIOR_CHOICES = [
        'Balcón',
        'Campo de golf',
        'Cancha de tenis',
        'Chacha de Volleyball',
        'Estacionamiento',
        'Parrilla/BBQ',
        'Patio',
        'Salón de eventos',
        'Terraza común',
        'Terraza privada',
        'Vista al Mar',
        'Canchas deportivas',
        'Roof garden',
    ]

    INTERIOR_SPACES_CHOICES = [
        'Cuarto de servicio',
        'Cuarto familiar',
        'Desayunador',
        'Estudio',
        'Oficina',
        'Penthouse',
        'Pisos en Cerámica',
        'Pisos en Madera',
        'Pisos en Mármol',
        'Pisos en Porcelanato',
        'Sauna',
        'Lavandería',
        'Sala de estar',
        'Área de cine',
    ]
    
    # Create the mapping dictionary
    mapping = {}
    
    # Helper function to add mapping
    def add_mapping(variations: List[str], standard: str):
        for variation in variations:
            mapping[variation] = standard
    
    # IGNORE_LIST - amenities that should be completely removed (empty string means ignore)
    def add_ignore(variations: List[str]):
        for variation in variations:
            mapping[variation] = ""  # Empty string means ignore/remove this amenity
    
    # === ALL MAPPINGS INCLUDING THE FINAL TWO ===
    
    # SERVICE_CHOICES mappings
    add_mapping([
        'Aire acondicionado', 'Aires Acondicionados', 'Aire Central'
    ], 'Aire acondicionado')
    
    add_mapping([
        'Gas común', 'Gas Común con Medidor'
    ], 'Gas común')
    
    add_mapping([
        'Gimnasio'
    ], 'Gimnasio')
    
    add_mapping([
        'Inversor', 'Inversor Áreas Comunes'
    ], 'Inversor')
    
    add_mapping([
        'Planta Eléctrica', 'Planta', 'Planta full'
    ], 'Planta eléctrica')
    
    add_mapping([
        'Vigilancia 24 horas', 'Seguridad 24 horas', 'Seguridad 24/7', 'Seguridad 24 Horas'
    ], 'Seguridad 24 Horas')
    
    add_mapping([
        'Cisterna'
    ], 'Cisterna')
    
    # Map heating features to Calefacción
    add_mapping([
        'Chimenea'  # Fireplace -> heating
    ], 'Calefacción')
    
    # GENERAL_CHARACTERISTICS mappings
    add_mapping([
        'Acceso a Playa', 'Acceso a club de playa', 'Primera linea de playa'
    ], 'Acceso a la playa')
    
    add_mapping([
        'Acceso Discapacitados', 'Acceso para discapacitados'
    ], 'Acceso para personas con discapacidad')
    
    add_mapping([
        'Amueblado', 'Equipado', 'Línea Blanca', 'Sala amueblada'
    ], 'Amueblado')
    
    add_mapping([
        'Ascensor', 'Elevador', '1 Elevador', '2 Elevadores', '3 Elevadores', '4 Elevadores', 
        'Elevador de carga', 'Ascensor de carga'
    ], 'Ascensor')
    
    add_mapping([
        'Intercom'
    ], 'Intercom')
    
    add_mapping([
        'Jacuzzi', 'picuzzi', 'Picuzzy', 'Terraza con jacuzzi y BBQ'
    ], 'Jacuzzi')
    
    add_mapping([
        'Mascotas permitidas'
    ], 'Mascotas permitidas')
    
    add_mapping([
        'Piscina', 'Piscina privada', 'Piscina para niños', 'Club house con infinity pool'
    ], 'Piscina')
    
    add_mapping([
        'Portón Eléctrico'
    ], 'Portón eléctrico')
    
    add_mapping([
        'Residencial Cerrado'
    ], 'Residencial cerrado')
    
    add_mapping([
        'Recepción', 'Portero', 'Lobby', 'Lobby amueblado y climatizado', 'Lobby Climatizado'
    ], 'Recepción')
    
    # EXTERIOR_CHOICES mappings
    add_mapping([
        'Balcón', 'Balcón tipo Terraza', 'Balcón Integrado', 'Hab principal con W/C y balcón'
    ], 'Balcón')
    
    add_mapping([
        'Campo de golf', 'Campo de Golf', 'Vista al Campo de Golf', 'Vista al lago y campo de golf'
    ], 'Campo de golf')
    
    add_mapping([
        'Cancha de Tenis'
    ], 'Cancha de tenis')
    
    add_mapping([
        'Volleybal'
    ], 'Chacha de Volleyball')
    
    add_mapping([
        'Estacionamiento techado', 'Parqueos Paralelos', 'Parqueos', 'parqueo', 'Parqueos techados',
        'Parqueos Lineales', 'Garaje', 'Parqueo para visitas', '2 Car Garage', 'Estacionamiento De Visitas',
        'Parqueo techado para 2 vehículos'
    ], 'Estacionamiento')
    
    add_mapping([
        'BBQ', 'Asador'
    ], 'Parrilla/BBQ')
    
    add_mapping([
        'Patio'
    ], 'Patio')
    
    add_mapping([
        'Área social', 'Salón Multiusos', 'Casa Club', 'Salón de Actividades', 'Salón de reuniones',
        'Sala de reunión'
    ], 'Salón de eventos')
    
    add_mapping([
        'Terraza Común'
    ], 'Terraza común')
    
    add_mapping([
        'Terraza Exclusiva', 'Terraza Techada', 'Terraza Destechada'
    ], 'Terraza privada')
    
    add_mapping([
        'Vista al Mar'
    ], 'Vista al Mar')
    
    add_mapping([
        'Area deportiva', 'Cancha de Basket Ball', 'Area de Juegos Infantiles', 'Area De Juegos Infantiles',
        'Area de Juegos para Niños', 'Mini Golf', 'Mini golf', 'padel', 'Club de raqueta / PICKLEBALL'
    ], 'Canchas deportivas')
    
    add_mapping([
        'Rooftop panorámico'
    ], 'Roof garden')
    
    # Map gallery/covered areas to terraza privada
    add_mapping([
        'Galería'  # Gallery/covered outdoor space
    ], 'Terraza privada')
    
    # INTERIOR_SPACES_CHOICES mappings
    add_mapping([
        'Cuarto de Servicio', 'Habitacion de servicio', 'Cuarto de chofer'
    ], 'Cuarto de servicio')
    
    add_mapping([
        'Family Room'
    ], 'Cuarto familiar')
    
    add_mapping([
        'Cocina con desayunador'
    ], 'Desayunador')
    
    add_mapping([
        'Estudio'
    ], 'Estudio')
    
    add_mapping([
        'Oficinas'
    ], 'Oficina')
    
    add_mapping([
        'Pisos en Mármol', 'Cocina en Marmol'
    ], 'Pisos en Mármol')
    
    add_mapping([
        'Pisos Porcelanato'
    ], 'Pisos en Porcelanato')
    
    add_mapping([
        'Sauna'
    ], 'Sauna')
    
    add_mapping([
        'Area de lavado', 'Area De Lavado', 'zona de lavandería', 'Area de Lavandería'
    ], 'Lavandería')
    
    add_mapping([
        'Sala'
    ], 'Sala de estar')
    
    add_mapping([
        'Cine', 'Salón de Cine'
    ], 'Área de cine')
    
    # === ALL OTHER MAPPINGS ===
    
    # Map to GENERAL_CHARACTERISTICS
    add_mapping([
        'Locker'  # Storage -> can be considered furnished/equipped
    ], 'Amueblado')
    
    add_mapping([
        'No se aceptan mascotas'  # Opposite of pets allowed - ignore as we only have "pets allowed"
    ], '')
    
    # Map to EXTERIOR_CHOICES
    add_mapping([
        'Gazebo', 'Pérgola'  # Outdoor structures
    ], 'Patio')
    
    add_mapping([
        'Jardín', 'Jardinería', 'Jardineria Exterior', 'Sendero ecológico', 'Sendero Ecológico'
    ], 'Patio')
    
    add_mapping([
        'Parque', 'Frente A Parque'  # Park access
    ], 'Patio')
    
    add_mapping([
        'Marquesina'  # Covered parking/outdoor space
    ], 'Estacionamiento')
    
    # Map to INTERIOR_SPACES_CHOICES
    add_mapping([
        'Cocina', 'Cocina Caliente', 'Cocina Fría', 'Cocina con cuartzo', 'Cocina equipada', 'Cocina integral'
    ], 'Desayunador')  # Kitchen features -> breakfast area
    
    add_mapping([
        'Comedor'
    ], 'Desayunador')
    
    add_mapping([
        'Baños', 'Baño de Visitas', 'Baño de visita', '½ Baño', 'Baños Pileta'
    ], 'Sala de estar')  # General living space
    
    add_mapping([
        'Lavadora', 'Secadora'
    ], 'Lavandería')
    
    add_mapping([
        'Walk in closet', 'Closet de ropa blanca', 'Habitación Principal con Walk-in Closet'
    ], 'Cuarto de servicio')  # Storage space
    
    add_mapping([
        'Recibidor'  # Reception area
    ], 'Sala de estar')
    
    add_mapping([
        'Almacén', 'Sótano'  # Storage areas
    ], 'Cuarto de servicio')
    
    # Map to SERVICE_CHOICES
    add_mapping([
        'Cámaras de seguridad', 'Circuito cerrado de seguridad', 'Caseta De Guardia', 'Caseta de Guardián',
        'Garita de Seguridad', 'Garita de entrada y salida', 'Verja perimetral', 'Alarma'
    ], 'Seguridad 24 Horas')
    
    add_mapping([
        'Calentador De Agua', 'Calentador Eléctrico', 'Calentador de Gas', 'Horno Eléctrico'
    ], 'Aire acondicionado')  # Appliances/utilities
    
    add_mapping([
        'Sistema contra incendios', 'Sistema contra Incendio', 'Escalera de emergencia'
    ], 'Seguridad 24 Horas')
    
    # Map to EXTERIOR_CHOICES - Entertainment/Social
    add_mapping([
        'Restaurante', 'Cafetería', 'Cafés', 'Bar Lounge', 'Lounge Bar', 'Sportbar', 'Pool bar'
    ], 'Salón de eventos')
    
    add_mapping([
        'Spa', 'salon de belleza', 'Centro de equitación'
    ], 'Salón de eventos')
    
    add_mapping([
        'Lago de pesca', 'Deportes acuáticos', 'Swin up'
    ], 'Campo de golf')  # Recreational activities
    
    add_mapping([
        'Yoga', 'Area de Yoga'
    ], 'Canchas deportivas')
    
    add_mapping([
        'Anfiteatro'
    ], 'Salón de eventos')
    
    # Map misc outdoor features
    add_mapping([
        'Playa', 'Playa artificial', 'Playa artificial ( agua salada)'
    ], 'Acceso a la playa')
    
    # Map utility/service features
    add_mapping([
        'Agua', 'Luz', 'Cable', 'Teléfono', 'Cableado de Redes'
    ], 'Intercom')  # Communication/utilities
    
    add_mapping([
        'Paneles Solares'
    ], 'Planta eléctrica')
    
    add_mapping([
        'Pozo'
    ], 'Cisterna')
    
    add_mapping([
        'Ducto de basura'
    ], 'Ascensor')  # Building services
    
    # Map appliances/equipment to furnished
    add_mapping([
        'Abanico', 'Shutters', 'Shutters anticlónicos instalados', 'Cortinas', 'Cama'
    ], 'Amueblado')
    
    add_mapping([
        'Sistema de Sonido', 'Malla de Protección'
    ], 'Amueblado')
    
    # Map room/space descriptions to appropriate categories
    add_mapping([
        '3 habitaciones', '4 habitaciones', '3 baños completos'
    ], 'Cuarto familiar')  # Multiple rooms
    
    add_mapping([
        '2 Niveles', '3 Niveles', '4 Niveles', 'Doble altura', 'Escaleras'
    ], 'Penthouse')  # Multi-level properties
    
    add_mapping([
        'Lounge'
    ], 'Sala de estar')
    
    # === AMENITIES TO IGNORE (not relevant for property features) ===
    add_ignore([
        # Location/neighborhood features (not property amenities)
        'Centros Comerciales Cercanos', 'Supermercados', 'Farmacias', 'Hospital(es)', 'Clínicas',
        'Aeropuerto', 'Bancos comerciales', 'Tiendas', 'Centro comercial', 'Zona comercial',
        'Escuelas/Colegios', 'Colegio Bilingue', 'Escuelas Cercanas',
        'Fácil acceso a Centros Médicos de la zona',
        
        # Business/commercial features
        'AirBnB Friendly', 'Alta rentabilidad', 'Vacacional', 'Uso Comercial',
        'Para desarrollo Comercial', 'Para desarrollo de Proyectos Turísticos',
        'En Plaza Comercial', 'Administración de propiedades', 'acceso a hotel Melia',
        
        # Rules/policies
        'Permitido fumar', 'Prohibido fumar', 'Apto para familias y niños',
        
        # Vague/generic terms
        'Amenidades', 'ISLA',
        
        # Very specific hotel-like services
        'Ciclovía'
    ])
    
    return mapping

def standardize_amenities_final():
    """Read properties_data.json, standardize ALL amenities completely, and save to new file"""
    
    # File paths
    input_file = '/home/sebastian/Documents/Scraping/scraping-do-websites/jsons/properties_data.json'
    output_file = '/home/sebastian/Documents/Scraping/properties_data_final_standardized.json'
    
    # Create comprehensive mapping
    mapping = create_final_amenity_mapping()
    
    print("Loading properties data...")
    with open(input_file, 'r', encoding='utf-8') as f:
        properties = json.load(f)
    
    print(f"Loaded {len(properties)} properties")
    
    # Statistics
    mapped_count = 0
    ignored_count = 0
    unmapped_amenities = set()
    total_amenities_processed = 0
    
    # Process each property
    for i, prop in enumerate(properties):
        if 'amenities' in prop and prop['amenities']:
            original_amenities = prop['amenities'] if isinstance(prop['amenities'], list) else [prop['amenities']]
            standardized_amenities = []
            
            for amenity in original_amenities:
                if isinstance(amenity, str):
                    amenity = amenity.strip()
                    total_amenities_processed += 1
                    
                    # Try direct mapping first
                    if amenity in mapping:
                        mapped_value = mapping[amenity]
                        if mapped_value == "":  # Empty string means ignore
                            ignored_count += 1
                        else:
                            standardized_amenities.append(mapped_value)
                            mapped_count += 1
                    else:
                        # Try case-insensitive matching
                        found = False
                        for key, value in mapping.items():
                            if amenity.lower() == key.lower():
                                if value == "":  # Empty string means ignore
                                    ignored_count += 1
                                else:
                                    standardized_amenities.append(value)
                                    mapped_count += 1
                                found = True
                                break
                        
                        if not found:
                            unmapped_amenities.add(amenity)
                            # For completely unmapped, ignore them
                            ignored_count += 1
            
            # Remove duplicates while preserving order
            seen = set()
            unique_amenities = []
            for amenity in standardized_amenities:
                if amenity not in seen:
                    seen.add(amenity)
                    unique_amenities.append(amenity)
            
            prop['amenities'] = unique_amenities
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"Processed {i + 1} properties...")
    
    # Save standardized data
    print(f"\nSaving final standardized data to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(properties, f, ensure_ascii=False, indent=2)
    
    # Print statistics
    print(f"\n" + "="*60)
    print("FINAL STANDARDIZATION COMPLETE!")
    print(f"="*60)
    print(f"Total properties processed: {len(properties)}")
    print(f"Total amenities processed: {total_amenities_processed}")
    print(f"Amenities successfully mapped: {mapped_count}")
    print(f"Amenities ignored/removed: {ignored_count}")
    print(f"Amenities still unmapped: {len(unmapped_amenities)}")
    print(f"Success rate: {((mapped_count + ignored_count)/total_amenities_processed)*100:.1f}%")
    
    if unmapped_amenities:
        print(f"\nStill unmapped amenities ({len(unmapped_amenities)}):")
        print("-" * 40)
        for amenity in sorted(unmapped_amenities):
            print(f"  - {amenity}")
    else:
        print("\n✅ PERFECT! All amenities are now fully standardized!")
    
    print(f"\nFinal standardized data saved to: {output_file}")
    print("\n🎯 Ready for PostgreSQL upload!")

if __name__ == "__main__":
    standardize_amenities_final() 