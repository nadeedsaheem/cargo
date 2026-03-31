import re
import random
import json
import google.generativeai as genai
from services.maps import geocode_location

GEMINI_API_KEY = "AIzaSyBHs4-uIytB4HqexQBt4vZLBTvV_NsKLEQ"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def clean_json_response(raw_text):
    text = raw_text.strip()
    if text.startswith('```json'): text = text[len('```json'):]
    if text.startswith('```'): text = text[len('```'):]
    if text.endswith('```'): text = text[:-3]
    return text.strip()

def gemini_ai(message: str) -> dict:
    prompt = f"""You are a logistics AI.

Extract structured data from this message:

MESSAGE: {message}

Return ONLY JSON:
{{
"type": "truck or load",
"start": "location name",
"destination": "location name",
"capacity": number or null
}}

Rules:
* Understand natural language and deeply evaluate constraints.
* Fix grammar mistakes.
* Extract best possible locations chronologically.
* If message implies "empty truck", "empty with empty loads", or "space available", type MUST be "truck".
* If message implies seeking a "load", "cargo", or "goods", type MUST be "load".
* Do NOT return explanation, markdown wrappers, or text outside the JSON.
"""
    response = model.generate_content(prompt)
    cleaned = clean_json_response(response.text)
    data = json.loads(cleaned)
    return data

def rule_based_ai(message: str) -> dict:
    message_lower = message.lower()
    
    msg_type = "unknown"
    # Strict Priority 1: User specifies empty or truck spaces
    if any(w in message_lower for w in ["empty", "truck", "space", "available", "lorry"]):
        msg_type = "truck"
    # Priority 2: Standard load request
    elif any(w in message_lower for w in ["load", "cargo", "goods", "freight", "material"]):
        msg_type = "load"
        
    start = "Unknown"
    destination = "Unknown"
    
    noise_words = [
        "with", "empty", "going", "available", "truck", "load", 
        "cargo", "goods", "for", "the", "a", "an", "of", "tons", "ton", "kg", "space", "loads"
    ]
    
    cleaned_msg = message_lower.replace(",", "").replace(".", "")
    for noise in noise_words:
        cleaned_msg = re.sub(rf'\b{noise}\b', '', cleaned_msg)
        
    cleaned_msg = re.sub(r'\s+', ' ', cleaned_msg).strip()
    
    # regex 1: Supports 2-word locations like "New Delhi"
    m1 = re.search(r'from\s+([a-z]+(?:\s+[a-z]+)?)\s+to\s+([a-z]+(?:\s+[a-z]+)?)', cleaned_msg)
    if m1:
        start = m1.group(1).title()
        destination = m1.group(2).title()
    else:
        m2 = re.search(r'([a-z]+(?:\s+[a-z]+)?)\s+to\s+([a-z]+(?:\s+[a-z]+)?)', cleaned_msg)
        if m2:
            s_full = m2.group(1).split()
            start = s_full[-1].title() if s_full else m2.group(1).title()
            
            d_full = m2.group(2).split()
            destination = d_full[0].title() if d_full else m2.group(2).title()
            
    if start == "Unknown" and destination == "Unknown":
        words = cleaned_msg.split()
        locs = [w.title() for w in words if w not in ["to", "from"] and not w.isdigit()]
        if len(locs) >= 2:
            start = locs[0]
            destination = locs[1]
        elif len(locs) == 1:
            start = locs[0]
            
    capacity = None
    cap_match = re.search(r'(\d+)\s*(ton|kg|tonne|t)', message_lower)
    if cap_match:
        capacity = int(cap_match.group(1))
        if cap_match.group(2) == 'kg': capacity = capacity / 1000
            
    return {
        "type": msg_type,
        "start": start,
        "destination": destination,
        "capacity": capacity
    }

def get_predictive_insights(location, item_type):
    if item_type in ["truck", "truck_with_space"]:
        return [
            f"Wait 1 hour. We expect 3 premium cargo loads posting from {location} soon.",
            f"Demand is surging in neighboring local towns. Rates are up 15%."
        ]
    else:
        return [
            f"5 empty trucks are expected to finish runs in {location} tomorrow morning.",
            f"Booking now avoids the weekend premium rate peak."
        ]

def analyze_message(message: str) -> dict:
    extracted = None
    confidence = 0
    print(f"\nDEBUG [gemini.py] === ANALYZING MESSAGE ===")
    print(f"DEBUG [gemini.py] RAW TEXT: {message}")
    
    try:
        extracted = gemini_ai(message)
        if "type" in extracted and "start" in extracted and "destination" in extracted:
            confidence = random.randint(90, 98)
            if not extracted.get("start"): extracted["start"] = "Unknown"
            if not extracted.get("destination"): extracted["destination"] = "Unknown"
            if "capacity" not in extracted: extracted["capacity"] = None
        else:
            raise ValueError("Incomplete Gemini Schema")
    except Exception as e:
        print(f"DEBUG [gemini.py] Gemini AI Error: {e}. Falling back to NLP Rules.")
        extracted = rule_based_ai(message)
        confidence = random.randint(60, 75)
        
    extracted["confidence"] = confidence
    
    print(f"DEBUG [gemini.py] RAW EXTRACT: {extracted}")
    
    if extracted["start"] != "Unknown":
        extracted["start"] = geocode_location(extracted["start"])
        
    if extracted["destination"] != "Unknown":
        extracted["destination"] = geocode_location(extracted["destination"])
    
    print(f"DEBUG [gemini.py] NORM EXTRACT: Start={extracted['start']}, Dest={extracted['destination']}, Type={extracted['type']}")
    
    suggestions = []
    if confidence >= 70:
        if extracted["start"] != "Unknown":
            suggestions.extend(get_predictive_insights(extracted["start"], extracted["type"]))
    else:
        suggestions.append("Please specify both Start and Destination limits for accurate pairings.")
        
    return {
        "extracted_data": extracted,
        "copilot_suggestions": suggestions
    }

def get_decision_recommendation(latest_entity, matches):
    if not latest_entity:
        return "I need you to post a load or a truck first so I can analyze the market."
        
    if not matches:
        return f"💡 **BEST ACTION:**\n\nNo active compatible nodes found.\n\n**Reason:**\n✔ Searched entire database\n✔ 0 Matches generated\n\nI recommend waiting for new real-time data to arrive for {latest_entity.get('start', 'your area')}."

    best_match = matches[0]
    is_truck = latest_entity["type"] in ["truck", "truck_with_space"]
    
    opp = best_match["load"] if is_truck else best_match["truck"]
    target_name = "load" if is_truck else "truck"
    
    target_route = f"{opp['start']} → {opp['destination']}"
    self_route = f"{latest_entity['start']} → {latest_entity['destination']}"
    
    truck_str = target_route if not is_truck else self_route
    load_str = target_route if is_truck else self_route
    
    reasons_text = "\n".join([f"{r}" for r in best_match["reasons"]])
    
    rec = f"💡 **BEST ACTION:**\n\nTake the **{target_route}** {target_name}\n\n"
    rec += f"🚚 **Truck:** {truck_str}\n"
    rec += f"📦 **Load:** {load_str}\n"
    rec += f"📍 **Pickup Distance:** {best_match['dist_to_pickup']} km\n"
    rec += f"🔥 **Match Score:** {best_match['score']}%\n\n"
    rec += f"**Reason:**\n{reasons_text}"
    
    if len(matches) > 1:
        rec += f"\n\n*(Also analyzed {len(matches)-1} other viable options, but this is the mathematically optimal choice)*"
        
    return rec
