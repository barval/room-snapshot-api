import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    RTSP_AUTH = os.getenv('RTSP_AUTH')
    
    @staticmethod
    def load_cameras():
        cameras = {}
        with open('/app/config/cameras.conf', 'r') as f:
            for line in f:
                if line.strip():
                    code, params = line.strip().split('=', 1)
                    ip, stream, name = params.split(':', 2)
                    cameras[code.lower()] = {
                        'ip': ip,
                        'stream': stream,
                        'name': name,
                        'url': f"rtsp://{Config.RTSP_AUTH}@{ip}:{stream}"
                    }
        return cameras