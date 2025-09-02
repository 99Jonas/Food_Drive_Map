import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import psycopg2
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Store houses in memory for now: {house_id: visited (bool)}
houses = {}

def save_houses():
    """Save the current in-memory houses dict to PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Create table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS houses (
                house_id TEXT PRIMARY KEY,
                lat DOUBLE PRECISION NOT NULL,
                lng DOUBLE PRECISION NOT NULL
            )
        """)

        # Delete rows that are no longer in the in-memory dict
        if houses:
            cur.execute(
                "DELETE FROM houses WHERE house_id NOT IN %s",
                (tuple(houses.keys()),)
            )
        else:
            # If no houses, clear the table
            cur.execute("DELETE FROM houses")

        # Insert or update each house
        for h_id, data in houses.items():
            cur.execute("""
                INSERT INTO houses (house_id, lat, lng)
                VALUES (%s, %s, %s)
                ON CONFLICT (house_id)
                DO UPDATE SET lat = EXCLUDED.lat, lng = EXCLUDED.lng
            """, (h_id, data['lat'], data['lng']))

        conn.commit()
        cur.close()
        conn.close()
        print("Houses saved to database.")
    except Exception as e:
        print("Error saving houses:", e)

def load_houses():
    """Load houses from PostgreSQL into the in-memory dictionary."""
    global houses
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Make sure table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS houses (
                house_id TEXT PRIMARY KEY,
                lat DOUBLE PRECISION NOT NULL,
                lng DOUBLE PRECISION NOT NULL
            )
        """)

        cur.execute("SELECT house_id, lat, lng FROM houses")
        rows = cur.fetchall()
        houses = {row[0]: {"house_id": row[0], "lat": row[1], "lng": row[2]} for row in rows}

        cur.close()
        conn.close()
        print(f"Loaded {len(houses)} houses from database.")
    except Exception as e:
        print("Error loading houses:", e)

# Load houses at server start
load_houses()

# Serve frontend
@app.route("/")
def index():
    return render_template("index.html")  # ✅ this loads your HTML

@socketio.on("connect")
def on_connect():
    print("Client connected")
    emit("update_houses", houses)

@socketio.on("add_house")
def add_house(data):
    """Toggle a house's visited state"""
    house_id = data.get("house_id")
    lat = data.get("lat")
    lng = data.get("lng")
    if house_id is None:
        return

    houses[house_id] = {"house_id": house_id, "lat": lat, "lng": lng}

    # Broadcast updated houses to all clients
    socketio.emit("update_houses", houses)
    save_houses()

@socketio.on("remove_house")
def remove_house(data):
    house_id = data.get("house_id")
    if house_id is None:
        return

    if house_id in houses:
        del houses[house_id]

    socketio.emit("update_houses", houses)
    save_houses()

@socketio.on("reset_houses")
def reset_all():
    """Optional: reset all houses to unvisited"""
    houses.clear()
    socketio.emit("update_houses", houses)
    save_houses()

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)


