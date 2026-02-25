from flask import Flask, send_file, jsonify, abort, request
from flask_cors import CORS
import subprocess
import time
import os
import sys

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from utils import get_room_image, check_ffmpeg

app = Flask(__name__)
CORS(app)
cameras = Config.load_cameras()

@app.route('/snapshot/<room>', methods=['GET'])
def snapshot(room):
    """Get a snapshot of the room"""
    image_file = get_room_image(room, cameras)
    if image_file:
        return send_file(image_file, mimetype='image/jpeg')
    abort(404, description="Room not found or image capture failed")

@app.route('/rooms', methods=['GET'])
def list_rooms():
    """List all available rooms"""
    return jsonify({code: data['name'] for code, data in cameras.items()})

@app.route('/rooms/<room>', methods=['GET'])
def room_info(room):
    """Information about a specific room"""
    room_code = room.lower()
    if room_code not in cameras:
        abort(404, description="Room not found")
    
    camera = cameras[room_code]
    # Hide password in URL
    url_parts = camera['url'].split('@')
    hidden_url = f"rtsp://***:***@{url_parts[1]}" if len(url_parts) > 1 else camera['url']
    
    return jsonify({
        'code': room_code,
        'name': camera['name'],
        'ip': camera['ip'],
        'stream': camera['stream'],
        'url': hidden_url
    })

@app.route('/health', methods=['GET'])
def health_check():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'cameras_loaded': len(cameras),
        'ffmpeg_available': check_ffmpeg(),
        'cameras': list(cameras.keys())
    })

@app.route('/info', methods=['GET'])
def api_info():
    """API information"""
    return jsonify({
        'name': Config.API_TITLE,
        'version': Config.API_VERSION,
        'description': 'API for retrieving snapshots from surveillance cameras',
        'endpoints': {
            'rooms': {
                'method': 'GET',
                'path': '/rooms',
                'description': 'List all rooms'
            },
            'room_info': {
                'method': 'GET',
                'path': '/rooms/<room>',
                'description': 'Information about a specific room'
            },
            'snapshot': {
                'method': 'GET',
                'path': '/snapshot/<room>',
                'description': 'Get a snapshot of the room'
            },
            'health': {
                'method': 'GET',
                'path': '/health',
                'description': 'Health check'
            },
            'info': {
                'method': 'GET',
                'path': '/info',
                'description': 'API information'
            }
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)