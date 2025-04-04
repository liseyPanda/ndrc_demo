import requests
import psycopg2
import json
from datetime import datetime
# API KEY
FLIGHT_API_KEY = "7bb69e303da89ab7a4273e71e68c3eee"

AVIATION_API_URL = "http://api.aviationstack.com/v1/flights"

ELASTICSEARCH_URL = "http://elasticsesarch:9200/hq-index/_bulk"

DB_CONFIG = {
    "dbname": "hq_db",
    "user": "hq_user",
    "password": "hq_pass",
    "host": "hq-db",
    "port": 5432
}

def fetch_live_flights():

    """Fetches live flight data from AviationStack."""
    params = {
        "access_key": FLIGHT_API_KEY,
        "limit": 5,
    }

    response = requests.get(AVIATION_API_URL, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get("data", [])
    else:
        print(f"Error fetching flight data: {response.status_code}")
        return []
    
def save_flights_to_hq_db(flights):
    """Saves fetched flight data to HQ DB""" 
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        for flight in flights:
            flight_id = flight.get("flight", {}).get("iata", "Unknown")
            airline = flight.get("airline", {}).get("name", "Unknown Airline")
            origin = flight.get("departure", {}).get("airport", "Unknown Airport")
            destination = flight.get("arrival", {}).get("airport", "Unknown Airport")
            status = flight.get("flight_status", "Unknown")
            timestamp = datetime.utcnow().isoformat()   

            query = """
                INSERT INTO flight_events (flight_id, airline, origin, destination, status, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s);
            """
            cur.execute(query, (flight_id, airline, origin, destination, status, timestamp))
        conn.commit()
        cur.close()
        conn.close()
        print(f"Saved  {len(flights)} flights to HQ Database.")
    except Exception as e:
        print(f"Error saving flight data: {e}")

def fetch_flights_from_db():
    """Fetches the latest 10 flights from PostgreSQL HQ DB."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("SELECT flight_id, airline, origin, destination, status, timestamp FROM flight_events ORDER BY timestamp DESC LIMIT 10;")
        data = cur.fetchall()
        cur.close()
        conn.close()

        flight_list = [
            
            {"flight_id": row[0], "airline": row[1], "origin": row[2], "destination": row[3], "status": row[4], "timestamp": row[5].isoformat()}
            for row in data 
        ]
        return flight_list
    except Exception as e:
        print(f"Error fetching flights from DB: {e}")
        return []

# flights updated to elasticsearch
def send_to_elastic():
    flights = fetch_flights_from_db()

    if not flights:
        print("No data to send over. ❌")
        return
    
    bulk_data = ""
    for flight in flights:
        bulk_data += json.dumps({"index": {"_index": "hq-index"}}) + "\n"
        bulk_data += json.dumps({
            "server": "HQ",
            "type": "flight",
            "flight_id": flight["flight_id"],
            "airline": flight["airline"],
            "origin": flight["origin"],
            "destination": flight["destination"],
            "status": flight["status"],
            "timestamp": flight["timestamp"]
        }) + "\n"

    headers = {"Content-Type": "application/json"}
    response = requests.post(ELASTICSEARCH_URL, headers=headers, data=bulk_data)

    if response.status_code == 200:
        print("Sent data to ES successful push ✅✈️")
    else:
        print(f"Error sending to ES: {response.status_code}, {response.text}")
if __name__ == "__main__":
    # uncomment the below functions for the live data pull
    #flights = fetch_live_flights()
    #save_flights_to_hq_db(flights)
    #print(json.dumps(flights, indent=2))
    send_to_elastic()