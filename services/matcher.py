import random
from services.maps import get_distance, get_eta

def calculate_match_score(entity1, entity2) -> dict:
    if entity1["type"] == "unknown" or entity2["type"] == "unknown":
        return None
        
    is_e1_truck = entity1["type"] in ["truck", "truck_with_space"]
    is_e2_truck = entity2["type"] in ["truck", "truck_with_space"]
    
    if is_e1_truck == is_e2_truck:
        return None
        
    truck = entity1 if is_e1_truck else entity2
    load = entity2 if is_e1_truck else entity1
    
    t_start = truck.get("start", "Unknown")
    t_dest = truck.get("destination", "Unknown")
    l_start = load.get("start", "Unknown")
    l_dest = load.get("destination", "Unknown")
    
    if t_start == "Unknown" or l_start == "Unknown":
        return None
        
    dist_to_pickup = get_distance(t_start, l_start)
    
    score = 0
    reasons = []
    
    exact_match = (t_start == l_start and t_dest == l_dest and t_dest != "Unknown")
    
    if exact_match:
        score = 100
        reasons.append("✔ Exact route match (100% efficient)")
    else:
        if t_start == l_start:
            score += 40
            reasons.append("✔ Zero pickup distance (Same origin)")
        elif dist_to_pickup > 0 and dist_to_pickup <= 50:
            score += 20
            reasons.append(f"✔ Nearby pickup ({dist_to_pickup}km away)")
            
        if t_dest == l_dest and t_dest != "Unknown":
            score += 30
            reasons.append("✔ Exact destination alignment")
            
    t_cap = truck.get("capacity")
    l_cap = load.get("capacity")
    if t_cap is not None and l_cap is not None:
        if t_cap >= l_cap:
            score += 20
            reasons.append("✔ Optimal capacity fit")
        else:
            return None 
    else:
        score += 20 
        reasons.append("✔ Capacity constraints unrestrictive")
        
    deviation = 0
    if not exact_match and t_dest != "Unknown" and l_dest != "Unknown":
        dist_A_C = dist_to_pickup
        dist_C_D = get_distance(l_start, l_dest)
        dist_D_B = get_distance(l_dest, t_dest)
        dist_A_B = get_distance(t_start, t_dest)
        
        # Guard against triangle inequality bugs triggered by deterministic fake math routing
        deviation = max(0, (dist_A_C + dist_C_D + dist_D_B) - dist_A_B)
        
        if deviation <= 40:
            reasons.append("✔ High route alignment (Low deviation)")
        elif deviation > 100:
            score -= 30
            reasons.append("⚠️ Long detour required penalty")
            
    if score <= 0:
        return None
        
    score = min(score, 99) if not exact_match else 100
    
    truck_full_trip = get_distance(t_start, t_dest) if t_dest != "Unknown" else dist_to_pickup + get_distance(l_start, l_dest)
    
    profit_gain = int(truck_full_trip * 40 * (score/100))
    fuel_saved = round(truck_full_trip * 0.12 * (score/100), 1)
    co2_reduction = round(fuel_saved * 2.68, 1)

    print(f"DEBUG [matcher.py] - SCORED {{Truck: {t_start}->{t_dest}}} vs {{Load: {l_start}->{l_dest}}}")
    print(f"DEBUG [matcher.py] -   Pickup Dist: {dist_to_pickup}km | Deviation: {deviation}km")
    print(f"DEBUG [matcher.py] -   Final Score: {score}")

    return {
        "score": score,
        "truck": truck,
        "load": load,
        "dist_to_pickup": dist_to_pickup,
        "deviation": deviation,
        "reasons": reasons,
        "insights": {
            "profit_gain_formatted": f"₹{profit_gain}",
            "profit_gain": profit_gain,
            "co2_reduction": co2_reduction,
            "eta": get_eta(truck_full_trip),
            "distance": f"{truck_full_trip} km",
            "pickup_eta": get_eta(dist_to_pickup) if dist_to_pickup > 0 else "Ready exactly at origin!",
            "route_efficiency": f"{100 if exact_match else max(10, 100 - deviation)}%"
        },
        "copilot": f"System recommends taking this option."
    }

def get_top_matches(entity, db, limit=3):
    matches = []
    is_truck = entity["type"] in ["truck", "truck_with_space"]
    target_list = db["loads"] if is_truck else db["trucks"]
    
    for target in target_list:
        match_result = calculate_match_score(entity, target)
        if match_result:
            matches.append(match_result)
            
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:limit]
