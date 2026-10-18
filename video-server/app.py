import eventlet
eventlet.monkey_patch()

"""Tidewell video visit server: Socket.IO signaling for WebRTC.

The browsers talk to each other directly (peer to peer). This server only passes the setup messages
(offer, answer, network candidates) between the two people in a room. The Tidewell backend creates an
unguessable room name per appointment and links to this server's page: {WEBRTC_BASE_URL}/?room=<name>

Local:       pip install -r requirements.txt   then   python app.py          (port 5000, or $PORT)
Production:  gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT app:app
One worker only: the rooms below live in this process's memory, and Socket.IO needs every message
from a browser to reach the same process.
"""
import logging
import os

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

log = logging.getLogger("tidewell.video")

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

MAX_PEOPLE = 2  # a visit is one patient and one provider
_rooms: dict[str, set[str]] = {}  # room -> socket ids
_sid_room: dict[str, str] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return {"ok": True}


# Apple Health data goes to the main backend (POST /wearables/apple-health), not here.


# --- WebRTC signaling events ---

@socketio.on("join_room")
def handle_join(data):
    room = str(data.get("room", ""))[:80]
    if not room:
        return
    members = _rooms.setdefault(room, set())
    if len(members) >= MAX_PEOPLE and request.sid not in members:
        emit("room_full")
        return
    members.add(request.sid)
    _sid_room[request.sid] = room
    join_room(room)
    # Tell the person already waiting that someone arrived, so they start the call.
    emit("peer_joined", room=room, include_self=False)


@socketio.on("webrtc_offer")
def handle_offer(data):
    emit("webrtc_offer", data, room=data["room"], include_self=False)


@socketio.on("webrtc_answer")
def handle_answer(data):
    emit("webrtc_answer", data, room=data["room"], include_self=False)


@socketio.on("webrtc_ice_candidate")
def handle_candidate(data):
    emit("webrtc_ice_candidate", data, room=data["room"], include_self=False)


@socketio.on("leave_room")
@socketio.on("disconnect")
def handle_leave(*_):
    room = _sid_room.pop(request.sid, None)
    if not room:
        return
    _rooms.get(room, set()).discard(request.sid)
    if not _rooms.get(room):
        _rooms.pop(room, None)
    leave_room(room)
    emit("peer_left", room=room, include_self=False)


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
