import subprocess
import os

def get_room_image(room_code, cameras):
    if room_code.lower() not in cameras:
        return None
        
    camera = cameras[room_code.lower()]
    output_file = f"/tmp/{room_code}-shot.jpg"
    
    command = [
        'ffmpeg',
        '-y',
        '-i', camera['url'],
        '-vframes', '1',
        output_file
    ]
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        return output_file if os.path.exists(output_file) else None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Error capturing image: {e}")
        return None