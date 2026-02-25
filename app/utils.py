import subprocess
import os
import logging

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                               capture_output=True, 
                               text=True, 
                               check=True)
        logger.info("FFmpeg is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"FFmpeg check failed: {e}")
        return False

def get_room_image(room_code, cameras):
    """Get a snapshot from the room camera"""
    if room_code.lower() not in cameras:
        logger.warning(f"Room {room_code} not found")
        return None
        
    camera = cameras[room_code.lower()]
    output_file = f"/tmp/{room_code}-shot.jpg"
    
    # Remove old file if it exists
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
        except OSError as e:
            logger.error(f"Error removing old file: {e}")
    
    command = [
        'ffmpeg',
        '-y',
        '-i', camera['url'],
        '-vframes', '1',
        '-q:v', '2',
        '-timeout', '5000000',
        output_file
    ]
    
    try:
        logger.info(f"Capturing image from {room_code}")
        result = subprocess.run(
            command, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            timeout=15
        )
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Successfully captured image for {room_code}")
            return output_file
        else:
            logger.error(f"Image file is empty or missing for {room_code}")
            return None
            
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error for {room_code}: {e.stderr.decode() if e.stderr else 'Unknown error'}")
        return None
    except subprocess.TimeoutExpired as e:
        logger.error(f"Timeout expired for {room_code}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error for {room_code}: {str(e)}")
        return None