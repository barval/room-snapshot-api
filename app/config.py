import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    RTSP_AUTH = os.getenv('RTSP_AUTH', '')
    API_VERSION = '1.1.0'
    API_TITLE = 'Room Snapshot API'
    
    @staticmethod
    def load_cameras():
        cameras = {}
        config_path = '/app/config/cameras.conf'
        
        if not os.path.exists(config_path):
            print(f"Warning: Config file {config_path} not found")
            return cameras
            
        try:
            with open(config_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    try:
                        code, params = line.split('=', 1)
                        ip, stream, name = params.split(':', 2)
                        cameras[code.lower().strip()] = {
                            'ip': ip.strip(),
                            'stream': stream.strip(),
                            'name': name.strip(),
                            'url': f"rtsp://{Config.RTSP_AUTH}@{ip.strip()}:{stream.strip()}"
                        }
                    except ValueError as e:
                        print(f"Error parsing line {line_num}: {line}")
                        print(f"Error: {e}")
        except Exception as e:
            print(f"Error reading config file: {e}")
                    
        return cameras