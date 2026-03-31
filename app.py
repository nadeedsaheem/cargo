from flask import Flask, render_template, request, jsonify
from services.gemini import analyze_message, get_decision_recommendation
from services.matcher import get_top_matches
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

db = {
    "messages": [],
    "trucks": [],
    "loads": [],
    "latest_entity": None
}

stats = {
    "total_matches": 0,
    "total_profit": 0,
    "total_co2_saved": 0.0
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("text", "")
    sender_type = data.get("sender", "user") 
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
        
    db["messages"].append({
        "sender": sender_type,
        "text": message,
        "timestamp": datetime.now().isoformat()
    })
        
    ai_response = analyze_message(message)
    extracted = ai_response["extracted_data"]
    
    if extracted["type"] == "unknown":
        extracted["type"] = "truck" if sender_type == "driver" else "load"

    new_entity = extracted.copy()
    new_entity["original_message"] = message
    
    if extracted["confidence"] > 30:
        db["latest_entity"] = new_entity
        if new_entity["type"] in ["truck", "truck_with_space"]:
            db["trucks"].append(new_entity)
        else:
            db["loads"].append(new_entity)
        
    top_matches = get_top_matches(new_entity, db, limit=3)
    
    response_payload = {
        "status": "success",
        "extracted_data": extracted,
        "copilot_suggestions": ai_response["copilot_suggestions"],
        "matches": top_matches,
        "global_stats": stats
    }
    
    return jsonify(response_payload)

@app.route("/api/accept_match", methods=["POST"])
def accept_match():
    data = request.json
    
    stats["total_matches"] += 1
    stats["total_profit"] += data.get("profit", 0)
    stats["total_co2_saved"] += data.get("co2", 0.0)
    stats["total_co2_saved"] = round(stats["total_co2_saved"], 1)
    
    return jsonify({"status": "success", "global_stats": stats})

def seed_database():
    dummy_load_1 = {"type": "load", "start": "Thrissur", "destination": "Kozhikode", "capacity": 10}
    dummy_load_2 = {"type": "load", "start": "Thrissur", "destination": "Palakkad", "capacity": 5}
    db["loads"].extend([dummy_load_1, dummy_load_2])
    
    dummy_truck = {"type": "truck", "start": "Kochi", "destination": "Kozhikode", "capacity": 15}
    db["trucks"].append(dummy_truck)
    db["latest_entity"] = dummy_truck

def reset_system():
    db["messages"].clear()
    db["trucks"].clear()
    db["loads"].clear()
    db["latest_entity"] = None
    stats["total_matches"] = 0
    stats["total_profit"] = 0
    stats["total_co2_saved"] = 0.0
    
    seed_database()
    
    return {"status": "system cleared", "global_stats": stats}

@app.route("/api/reset", methods=["POST"])
def reset_api():
    return jsonify(reset_system())

@app.route("/api/decision", methods=["GET"])
def decision():
    latest_entity = db.get("latest_entity")
        
    if not latest_entity:
        return jsonify({"recommendation": "I need you to post a load or a truck first so I can analyze the network."})
        
    # Inject Top Matches safely into the analytical engine format
    top_matches = get_top_matches(latest_entity, db, limit=3)
    rec = get_decision_recommendation(latest_entity, top_matches)
    
    return jsonify({"recommendation": rec})

if __name__ == "__main__":
    seed_database()
    app.run(debug=True, port=5000)
