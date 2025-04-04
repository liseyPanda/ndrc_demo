from flask import Flask, jsonify, request, render_template
from datetime import datetime
import requests
import psycopg2
import time
from flask_cors import CORS 

app = Flask(__name__)
CORS(app)

# Elasticsearch
ELASTICSEARCH_URL = 'http://elasticsearch:9200'
KIBANA_URL = "http://localhost:5601/app/dashboards#/view/cbc70cdf-a9fe-4ecd-87fc-2d95b208c5eb?_g=(refreshInterval:(pause:!t,value:60000),time:(from:'2023-12-01T12:00:00.000Z',to:'2023-12-01T12:02:00.000Z'))&_a=()"

print("✅ hq is running and db is up")

# Database connection
def db_connection():
    return psycopg2.connect(
    dbname="hq_db",
    user="hq_user",
    password="hq_pass",
    host="hq-db",
    port=5432
)
# Enable auto-reload in development mode
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# updating data to db
@app.route('/update', methods=['POST'])
def update_data():
    data = request.json
    index = data.get("index", "hq-index")

    # ✅ Set last_updated only once
    data["last_updated"] = datetime.utcnow().isoformat() + "Z"

    conn = None  # Ensure conn is accessible in `finally`
    
    try:
        print(f"📥 Received data: {data}")

        # ✅ Step 1: Store in HQ PostgreSQL
        conn = db_connection()
        cur = conn.cursor()
        print("✅ Connected to HQ Database")

        cur.execute("""
            INSERT INTO trucks (truck_id, status, location, event, last_updated)
            VALUES (%s, %s, %s, %s, %s)
        """, (data.get("truck_id"), data.get("status"), data.get("location"), data.get("event"), data.get("last_updated")))

        conn.commit()
        print(f"✅ Truck data saved to HQ DB: {data['truck_id']} at {data['last_updated']}")

        # ✅ Step 2: Send data to Elasticsearch
        es_response = requests.post(f"{ELASTICSEARCH_URL}/trucks/_doc", json=data)

        if es_response.status_code == 201:
            print("✅ Data successfully sent to Elasticsearch!")
        else:
            print(f"❌ Failed to sync with Elasticsearch: {es_response.text}")

        return jsonify({"message": "Data stored in HQ DB & Elasticsearch"}), 201

    except Exception as e:
        print(f"❌ Database insert error: {str(e)}")
        return jsonify({"error": "Database or Elasticsearch error"}), 500

    finally:
        if conn:
            conn.close()
            print("🔌 Database connection closed.")

# Fetch truck data from PostgreSQL
def fetch_truck_data():
    try:
        # Create a new connection for each request
        conn = psycopg2.connect(
            dbname="hq_db",
            user="hq_user",
            password="hq_pass",
            host="hq-db",
            port=5432
        )
        with conn.cursor() as cur:
            cur.execute("SELECT truck_id, status, location, event, last_updated FROM trucks;")
            rows = cur.fetchall()
            truck_data = [
                {
                    "truck_id": row[0],
                    "status": row[1],
                    "location": row[2],
                    "event": row[3],
                    "last_updated": row[4].isoformat()
                }
                for row in rows
            ]
        print(f"grabbed truck data {rows}")
        return truck_data
    except Exception as e:
        print(f"Database error ⚙️❌: {e}")
        return []
    finally:
        conn.close()

# API to push truck data to Elasticsearch
@app.route("/push_to_elastic", methods=["POST"])
def push_to_elasticsearch():
    truck_data = fetch_truck_data()
    
    for truck in truck_data:
        response = requests.post(
            f"{ELASTICSEARCH_URL}/trucks/_doc",
            json=truck
        )
    
    return jsonify({"message": "Truck data updated to Elasticsearch!", "data": truck_data})

# dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', kibana_url=KIBANA_URL)


# @app.route('/get-events', methods=['GET'])
# def get_events():
#     try:
#         response = requests.get(HQ_URL, timeout=2)
#         if response.status_code == 200:
#             return jsonify(response.json())
#     except requests.exceptions.RequestException:
#         print("HQ is down, switching to Cloud...")

#     # Fallback to Cloud
#     try:
#         response = requests.get(CLOUD_URL, timeout=2)
#         if response.status_code == 200:
#             return jsonify(response.json())
#     except requests.exceptions.RequestException:
#         print("Both HQ and Cloud are unavailable.")

#     return jsonify({"error": "No data available"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)