import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'  # replace with env var in production
socketio = SocketIO(app, cors_allowed_origins="*")

# Store houses in memory for now: {house_id: visited (bool)}
houses = {}

# Serve frontend
@app.route("/")
def index():
    return render_template("index.html")  # ✅ this loads your HTML

@socketio.on("connect")
def on_connect():
    print("Client connected")
    emit("update_houses", houses)

@socketio.on("toggle_house")
def toggle_house(data):
    """Toggle a house's visited state"""
    house_id = data.get("house_id")
    if house_id is None:
        return

    # Toggle visited state
    houses[house_id] = not houses.get(house_id, False)

    # Broadcast updated houses to all clients
    socketio.emit("update_houses", houses)

@socketio.on("reset_all")
def reset_all():
    """Optional: reset all houses to unvisited"""
    houses.clear()
    socketio.emit("update_houses", houses)

if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
