from flask import Flask, send_file, jsonify, abort
from config import Config
from utils import get_room_image

app = Flask(__name__)
cameras = Config.load_cameras()

@app.route('/snapshot/<room>', methods=['GET'])
def snapshot(room):
    image_file = get_room_image(room, cameras)
    if image_file:
        return send_file(image_file, mimetype='image/jpeg')
    abort(404, description="Room not found or image capture failed")

@app.route('/rooms', methods=['GET'])
def list_rooms():
    return jsonify({code: data['name'] for code, data in cameras.items()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)