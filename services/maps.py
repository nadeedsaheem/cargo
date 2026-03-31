import random
import requests
import hashlib

# Setup Google Maps Integration
MAPS_API_KEY = "AIzaSyABbZZDGvKFNNy4lACBm0NcyA774cDQuqA"

API_CACHE = {}
GEOCODE_CACHE = {}

def clean_location_input(text):
    if not text: return ""
    clean = text.lower()
    stopwords = ["from", "to", "going", "truck", "load", "empty", "available", "capacity", "space", "ton", "tons", "kg"]
    words = clean.split()
    filtered = [w for w in words if w not in stopwords and not w.isdigit()]
    return " ".join(filtered).title()

def geocode_location(city_name):
    if not city_name or str(city_name).lower() == "unknown":
        return city_name
        
    cleaned_city = clean_location_input(city_name)
    if not cleaned_city:
        return city_name
        
    lower_city = cleaned_city.lower()
    if lower_city in GEOCODE_CACHE:
        return GEOCODE_CACHE[lower_city]
        
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={cleaned_city}&key={MAPS_API_KEY}"
    try:
        response = requests.get(url, timeout=2)
        data = response.json()
        if data.get("status") == "OK" and len(data.get("results", [])) > 0:
            components = data["results"][0].get("address_components", [])
            corrected = None
            
            for comp in components:
                if "locality" in comp.get("types", []):
                    corrected = comp.get("long_name")
                    break
            
            if not corrected:
                for comp in components:
                    if "administrative_area_level_3" in comp.get("types", []) or "administrative_area_level_2" in comp.get("types", []):
                        corrected = comp.get("long_name")
                        break
                        
            if not corrected and components:
                corrected = components[0].get("long_name")
                
            if corrected:
                print(f"DEBUG [maps.py] - Geocode Normalized: '{city_name}' -> '{corrected}'")
                GEOCODE_CACHE[lower_city] = corrected
                return corrected
                
    except Exception as e:
        print(f"DEBUG [maps.py] - Geocoding API Error: {e}")
        
    print(f"DEBUG [maps.py] - API Failed/Missing. Falling back to cleaned fuzzy string: '{cleaned_city}'")
    GEOCODE_CACHE[lower_city] = cleaned_city
    return GEOCODE_CACHE[lower_city]

def deterministic_mock_distance(city1, city2):
    """Generates a stable pseudo-random distance for missing cities so routing math doesn't break."""
    hash_str = "".join(sorted([city1.lower(), city2.lower()]))
    hash_int = int(hashlib.md5(hash_str.encode()).hexdigest(), 16)
    return 50 + (hash_int % 300) 

def get_real_distance(origin, destination):
    key = tuple(sorted([origin.lower(), destination.lower()]))
    if key in API_CACHE:
        return API_CACHE[key]
        
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={destination}&key={MAPS_API_KEY}"
    try:
        response = requests.get(url, timeout=2)
        data = response.json()
        if data.get("status") == "OK" and data["rows"][0]["elements"][0].get("status") == "OK":
            element = data["rows"][0]["elements"][0]
            dist_val = int(element["distance"]["value"] / 1000)
            dur_text = element["duration"]["text"]
            
            result = {"distance": dist_val, "duration_text": dur_text}
            API_CACHE[key] = result
            return result
    except Exception as e:
        print(f"DEBUG [maps.py] - Maps Matrix API Error: {e}")
    return None

def get_distance(city1, city2):
    city1 = city1.lower()
    city2 = city2.lower()
    
    if city1 == city2:
        return 0
        
    cache_key = tuple(sorted([city1, city2]))
    if cache_key in API_CACHE:
        return API_CACHE[cache_key]["distance"]
        
    # 1. Real API is PRIMARY
    real_data = get_real_distance(city1, city2)
    if real_data:
        # Note: get_real_distance caches the response internally
        return real_data["distance"]
        
    # 2. Hardcoded fallback mock logic 
    distances = {
        ("kozhikode", "idukki"): 260,
        ("kozhikode", "kochi"): 190,
        ("kozhikode", "thrissur"): 115,
        ("kochi", "trivandrum"): 200,
        ("thrissur", "kochi"): 80,
        ("palakkad", "kochi"): 140,
        ("kannur", "kozhikode"): 90
    }
    
    res = distances.get((city1, city2))
    if not res:
        res = distances.get((city2, city1))
        
    if not res:
        # Lock random values cryptographically to prevent negative deviation loop bugs
        res = deterministic_mock_distance(city1, city2)
        
    # Standardize cache structure explicitly
    API_CACHE[cache_key] = {"distance": res, "duration_text": fallback_eta_calc(res)}
    return res

def fallback_eta_calc(distance_km):
    hours = distance_km / 40.0
    if hours <= 1:
        minutes = int(hours * 60)
        return f"{minutes} mins"
    
    h = int(hours)
    m = int((hours - h) * 60)
    if m == 0:
        return f"{h} hours"
    return f"{h}h {m}m"

def get_eta(distance_km):
    for val in API_CACHE.values():
        if val.get("distance") == distance_km and "duration_text" in val:
            return val["duration_text"]
            
    return fallback_eta_calc(distance_km)

def calculate_route_efficiency(truck_start, truck_dest, load_start, load_dest):
    if truck_start.lower() == load_start.lower() and truck_dest.lower() == load_dest.lower():
        return 100
        
    if truck_start.lower() != load_start.lower() and truck_dest.lower() == load_dest.lower():
        dist_to_load = get_distance(truck_start, load_start)
        if dist_to_load <= 50: return 85
        return 60
        
    if truck_start.lower() == load_start.lower() and truck_dest.lower() != load_dest.lower():
        dist_from_load = get_distance(truck_dest, load_dest)
        if dist_from_load <= 50: return 80
        return 50
        
    return 30
