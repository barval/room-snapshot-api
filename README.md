# Room Snapshot API v1.2

API for retrieving snapshots from surveillance cameras in various rooms. The service provides current images from RTSP cameras through a simple REST API.

## 📋 Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Monitoring and Diagnostics](#monitoring-and-diagnostics)
- [Docker](#docker)
- [Troubleshooting](#troubleshooting)
- [Notes](#notes)
- [Security](#security)
- [Roadmap](#roadmap)
- [License](#license)
- [Support](#support)

## 🚀 Features

- 📸 Retrieve snapshots from RTSP cameras
- 🏠 Support for multiple rooms/cameras
- 🔒 Secure storage of credentials
- 🐳 Ready-to-use Docker build
- 📊 Monitoring endpoints
- 🔍 Detailed camera information
- ⚡ Caching and optimization
- 🌐 CORS support for web applications

## 📋 Requirements

- Docker and Docker Compose (recommended)
- Python 3.9+ (for local run)
- Access to RTSP cameras
- FFmpeg (included in Docker image)

## ✅ Testing

- The application has been tested with cameras: TP-LINK TAPO C100, C200, C500.

## 🏁 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/barval/room-snapshot-api.git
cd room-snapshot-api
```

### 2. Configure environment

Create a .env file based on the example:
```bash
cp .env.example .env
```

Edit .env and provide the camera login/password and other parameters:
```env
RTSP_AUTH="username:password"
FLASK_DEBUG=false
SECRET_KEY="Your-secret-key-here"
```

### 3. Configure cameras

Create a config/cameras.conf file with the list of cameras:
```conf
# Format: code=ip:port:name
bed=192.168.1.101:554:Bedroom
liv=192.168.1.102:554:Living Room
stu=192.168.1.103:554:Study
hal=192.168.1.104:554:Hallway
kit=192.168.1.105:554:Kitchen
chi=192.168.1.106:554:Children's Room
ves=192.168.1.107:554:Vestibule
cor=192.168.1.108:554:Corridor
bal=192.168.1.109:554:Balcony
```

### 4. Run with Docker

```bash
docker-compose up -d
```

The service will be available at: `http://localhost:5005`

## 🔧 Configuration

### `.env` file
| Parameter | Description | Example |
|-----------|-------------|---------|
| `RTSP_AUTH` | Username and password for camera access | `admin:password123` |
| `FLASK_DEBUG` | Enable Flask debug mode (false in production) | `false` |
| `SECRET_KEY` | Secret key for Flask sessions (set a strong value) | `generated string` |
| `HOST` | Bind address (default 0.0.0.0) | `0.0.0.0` |
| `PORT` | Port (default 5000) | `5000` |

### `cameras.conf` file
Line format: `code=ip:port:name`
- `code` - unique room identifier (lowercase Latin)
- `ip` - camera IP address
- `port` - RTSP port (usually 554)
- `name` - display name of the room

## 📡 API Endpoints

### Base URL
```
http://your-server:5005
```

### 1. API Information
```
GET /info
```

**Response:**
```json
{
    "name": "Room Snapshot API",
    "version": "1.2.0",
    "description": "API for retrieving snapshots from surveillance cameras",
    "endpoints": {
        "rooms": {
            "method": "GET",
            "path": "/rooms",
            "description": "List all rooms"
        },
        "room_info": {
            "method": "GET",
            "path": "/rooms/<room>",
            "description": "Information about a specific room"
        },
        "snapshot": {
            "method": "GET",
            "path": "/snapshot/<room>",
            "description": "Get a snapshot of the room"
        },
        "health": {
            "method": "GET",
            "path": "/health",
            "description": "Health check"
        },
        "info": {
            "method": "GET",
            "path": "/info",
            "description": "API information"
        }
    }
}
```

### 2. List Rooms
```
GET /rooms
```

**Response:**
```json
{
    "bed": "Bedroom",
    "liv": "Living Room",
    "stu": "Study",
    "hal": "Hallway",
    "kit": "Kitchen",
    "chi": "Children's Room",
    "ves": "Vestibule",
    "cor": "Corridor",
    "bal": "Balcony"
}
```

### 3. Room Information
```
GET /rooms/{room_code}
```

**Parameters:**
- `room_code` - room code (e.g., `liv`)

**ОтвResponseет:**
```json
{
    "code": "liv",
    "name": "Living Room",
    "ip": "192.168.1.102",
    "stream": "554",
    "url": "rtsp://***:***@192.168.1.102:554"
}
```

### 4. Get Snapshot
```
GET /snapshot/{room_code}
```

**Parameters:**
- `room_code` - room code (e.g., `liv`)

**Example:**
```bash
curl http://localhost:5005/snapshot/liv -o liv.jpg
```

### 5. Health Check
```
GET /health
```

**Response:**
```json
{
    "status": "healthy",
    "timestamp": 1700000000.123,
    "cameras_loaded": 9,
    "ffmpeg_available": true,
    "cameras": ["bed", "liv", "stu", "hal", "kit", "chi", "ves", "cor", "bal"]
}
```

## 📝 Usage Examples

### cURL
```bash
# Get list of rooms
curl http://localhost:5005/rooms

# Get room information
curl http://localhost:5005/rooms/liv

# Save a snapshot
curl http://localhost:5005/snapshot/liv -o liv.jpg

# Check service health
curl http://localhost:5005/health
```

### Python
```python
import requests

BASE_URL = "http://localhost:5005"

# Get list of rooms
rooms = requests.get(f"{BASE_URL}/rooms").json()
print(f"Available rooms: {rooms}")

# Get a snapshot
response = requests.get(f"{BASE_URL}/snapshot/liv")
with open("liv.jpg", "wb") as f:
    f.write(response.content)

# Check service health
health = requests.get(f"{BASE_URL}/health").json()
print(f"Status: {health['status']}")
print(f"Cameras loaded: {health['cameras_loaded']}")
```

### JavaScript
```javascript
// Get a snapshot
fetch('http://localhost:5005/snapshot/liv')
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const img = document.createElement('img');
        img.src = url;
        document.body.appendChild(img);
    });

// Check status
fetch('http://localhost:5005/health')
    .then(response => response.json())
    .then(data => console.log('Status:', data));
```

## 📊 Monitoring and Diagnostics

### Check camera availability
```bash
curl http://localhost:5005/health | jq '.cameras'
```

### Service logs
```bash
# View Docker container logs
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```
### Docker health check
The container includes a health check that verifies the status every 30 seconds. You can check the health status with:
```bash
docker inspect --format='{{json .State.Health}}' room-snapshot-api-api-1
```

## 🐳 Docker

### Build image
```bash
docker-compose build
```

### Start container
```bash
docker-compose up -d
```

### Stop container
```bash
docker-compose down
```

### Restart
```bash
docker-compose restart
```

### Check status
```bash
docker-compose ps
```

## 🚀 Production Deployment
For production use, the application is run with Gunicorn (as specified in the Dockerfile). Key production considerations:
- Set `FLASK_DEBUG=false` and provide a strong `SECRET_KEY` in the `.env` file.
- The Docker container includes a health check for orchestration tools.
- Logging is configured to output JSON-formatted logs to stdout, suitable for collection by Docker logging drivers.
- Security headers are added via Flask-Talisman (CSP is disabled by default; configure as needed).
- For further hardening, place the API behind a reverse proxy (e.g., nginx) that handles SSL termination and rate limiting.

## 🔍 Troubleshooting

### Issue: Cannot get snapshot
**Solution:**
1. Check camera reachability: `ping CAMERA_IP`
2. Check logs: `docker-compose logs`
3. Verify credentials in `.env`
4. Check `cameras.conf` format

### Issue: Camera not listed
**Solution:**
1. Check `cameras.conf` syntax
2. Restart container: `docker-compose restart`
3. Check logs for parsing errors

### Issue: Timeout when getting snapshot
**Solution:**
- Increase timeout in `utils.py` (`timeout parameter`)
- Check network quality
- Ensure RTSP port is open

### Issue: FFmpeg not found
**Solution:**
```bash
# FFmpeg is already installed in the Docker container
# For local run:
sudo apt-get update && sudo apt-get install ffmpeg
```

## 📝 Notes

- All endpoints support CORS for web application integration
- Snapshots are temporarily stored in `/tmp` and are removed on restart
- For production, it is recommended to use a reverse proxy (nginx) and HTTPS
- For high request rates, consider setting up caching

## 🔒 Security

- Credentials are stored in `.env` and not committed to the repository
- Currently, a single username/password is used for all cameras
- Passwords are masked in API responses
- Security headers (HSTS, X-Frame-Options, etc.) are enabled via Flask-Talisman
- It is recommended to use network policies to restrict API access
- For production, use HTTPS and request authentication


## 📈 Roadmap


- [ ] Add individual credentials per camera
- [ ] Add API key authentication
- [ ] Implement snapshot caching
- [ ] Add WebSocket for live streams
- [ ] Create a web interface for viewing
- [ ] Add ONVIF camera support
- [ ] Implement archive recording

## 📄 License

MIT

## 📞 Support

If you encounter any issues, please create an issue in the project repository.
```