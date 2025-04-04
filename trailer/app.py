from flask import Flask, jsonify, render_template
import requests
from flask_apscheduler import APScheduler

app = Flask(__name__)

HQ_URL = "http://hq:5001/get-trailer-events"

# trailer specific kibana dashboard url
KIBANA_URL = "http://localhost:5601/app/dashboards#/view/99fc8f59-f28c-4607-b2b5-8edd5c01153f?_g=(refreshInterval:(pause:!t,value:60000),time:(from:now-15m,to:now))&_a=()"
ELASTICSEARCH_URL = "http://elasticsearch:9200"
# Enable auto-reload in development mode
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Auto Sync data
scheduler = APScheduler()
latest_events = []

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/')
def home():
    return "✅ Trailer is running. Go to /dashboard to view the trailer Kibana dashboard."

# Fetch trailer events from HQ
def get_trailer_events():
    global latest_events
    elastic_query = {
        "query": {
            "wildcard": { "truck_id.keyword": "Trailer-*" }
        }
    }
    response = requests.get(f"{ELASTICSEARCH_URL}/trucks/_search", json=elastic_query)

    if response.status_code == 200:
        data = response.json()
        if "hits" in data and "hits" in data["hits"]:
            latest_events = [
                {
                    "truck_id": hit["_source"]["truck_id"],
                    "status": hit["_source"]["status"],
                    "location": hit["_source"]["location"],
                    "event": hit["_source"]["event"],
                    "last_updated": hit["_source"]["last_updated"]
                }
                for hit in data["hits"]["hits"]
            ]
            print("Trailer events have been updated 👍")
        else: 
            latest_events = []

    else:
        print("Failed to sync trailer data from ES ⛔")

# trailer events
@app.route("/trailer-events", methods=["GET"])
def get_latest_events():
    return jsonify(latest_events)

# trailer dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', kibana_url=KIBANA_URL)

# schedule
scheduler.add_job(id="sync_trailer_data", func=get_trailer_events, trigger="interval", seconds=30)
scheduler.init_app(app)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
