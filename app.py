from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')

# --- WebRTC Signaling Events ---

@socketio.on('join_room')
def handle_join(data):
    room = data['room']
    join_room(room)
    # Tell others in the room that someone new arrived
    emit('peer_joined', broadcast=True, include_self=False, room=room)

@socketio.on('webrtc_offer')
def handle_offer(data):
    emit('webrtc_offer', data, broadcast=True, include_self=False, room=data['room'])

@socketio.on('webrtc_answer')
def handle_answer(data):
    emit('webrtc_answer', data, broadcast=True, include_self=False, room=data['room'])

@socketio.on('webrtc_ice_candidate')
def handle_candidate(data):
    emit('webrtc_ice_candidate', data, broadcast=True, include_self=False, room=data['room'])

if __name__ == '__main__':
    # Use socketio.run instead of app.run
    socketio.run(app, port=5000, debug=True)