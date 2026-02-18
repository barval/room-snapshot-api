from flask import Flask, send_file, jsonify, abort, request
from flask_cors import CORS
from config import Config
from utils import get_room_image, check_ffmpeg
import subprocess
import time

app = Flask(__name__)
CORS(app)  # Разрешить CORS для всех маршрутов
cameras = Config.load_cameras()

@app.route('/snapshot/<room>', methods=['GET'])
def snapshot(room):
    """Получить снимок комнаты"""
    image_file = get_room_image(room, cameras)
    if image_file:
        return send_file(image_file, mimetype='image/jpeg')
    abort(404, description="Room not found or image capture failed")

@app.route('/rooms', methods=['GET'])
def list_rooms():
    """Список всех доступных комнат"""
    return jsonify({code: data['name'] for code, data in cameras.items()})

@app.route('/rooms/<room>', methods=['GET'])
def room_info(room):
    """Информация о конкретной комнате"""
    room_code = room.lower()
    if room_code not in cameras:
        abort(404, description="Room not found")
    
    camera = cameras[room_code]
    return jsonify({
        'code': room_code,
        'name': camera['name'],
        'ip': camera['ip'],
        'stream': camera['stream'],
        'url': camera['url'].replace(Config.RTSP_AUTH, '***:***')  # Скрываем пароль
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'cameras_loaded': len(cameras),
        'ffmpeg_available': check_ffmpeg(),
        'cameras': list(cameras.keys())
    })

@app.route('/info', methods=['GET'])
def api_info():
    """Информация об API"""
    return jsonify({
        'name': Config.API_TITLE,
        'version': Config.API_VERSION,
        'description': 'API для получения снимков с камер видеонаблюдения',
        'endpoints': {
            'rooms': {
                'method': 'GET',
                'path': '/rooms',
                'description': 'Список всех комнат'
            },
            'room_info': {
                'method': 'GET',
                'path': '/rooms/<room>',
                'description': 'Информация о конкретной комнате'
            },
            'snapshot': {
                'method': 'GET',
                'path': '/snapshot/<room>',
                'description': 'Получить снимок комнаты'
            },
            'health': {
                'method': 'GET',
                'path': '/health',
                'description': 'Проверка работоспособности'
            },
            'info': {
                'method': 'GET',
                'path': '/info',
                'description': 'Информация об API'
            }
        }
    })

# Обработчики ошибок
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
