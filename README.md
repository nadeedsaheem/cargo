# AI Logistics Chat Copilot

## Problem Statement
The local logistics sector suffers from severe fragmentation, empty return trips, and inefficient manual communication. Truck operators and cargo loaders struggle to find compatible, profitable pairings in real-time, relying on slow, unstructured chat groups that lack geographical context, capacity matching, and route optimization.

## Project Description
**AI Logistics Chat Copilot** is a smart, real-time brokerage engine that instantly connects regional truck drivers with cargo owners. Users interact with the platform using purely natural language (e.g. *"empty truck from Kozhikode to Kochi"*). The system uses advanced NLP to extract routing variables, strictly standardizes them using Google Maps Geocoding, and feeds them into a custom Matcher Engine. The Copilot evaluates triangular routing combinations, scoring connections based on route deviation, pickup distances, and capacity constraints, ultimately yielding actionable, mathematically optimal recommendations instantly.

## Tools / Models Used
* **Frontend:** HTML5, CSS3 (Glassmorphism UX), Vanilla JavaScript
* **Backend:** Python, Flask server
* **AI Engine:** Google Gemini 1.5-Flash (Generative NLP Extraction)
* **Geospatial APIs:** Google Maps Geocoding API, Google Maps Distance Matrix API

## How Google AI Was Used
Our platform natively leverages **Google Gemini 1.5-Flash** as the central nervous system for payload interception. Instead of using rigid web forms, Gemini intercepts conversational logistics queries written with poor grammar or local colloquialisms. Gemini analyzes the string contextually, maps the variables against rigid schema requirements, calculates an extraction confidence score, and returns completely parameterized JSON endpoints (`type`, `origin`, `destination`, `payload capacity`) directly into our backend routing framework.

## Proof of Google AI Usage
See the `/proof` folder for console trace executions of Gemini seamlessly intercepting edge-case natural language logistics strings.

![AI Proof](proof/ai_proof.png)

## Screenshots
*(Add project screenshots here)*

![Dashboard GUI](proof/screenshot1.png)
![Decision Engine Map](proof/screenshot2.png)


## Installation Steps
```bash
# Clone the repository
git clone https://github.com/nadeedsaheem/cargo.git

# Go to project folder
cd cargo

# Install dependencies
pip install flask google-generativeai requests

# Run the project
python app.py
```
