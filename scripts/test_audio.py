import requests
import os
import wave
import math
import struct

BASE_URL = "http://localhost:8001"

def generate_wav(filepath, duration_seconds=5, sample_rate=44100):
    print(f"Generating a {duration_seconds}-second sine wave WAV file at {filepath}...")
    num_samples = duration_seconds * sample_rate
    wave_file = wave.open(filepath, 'wb')
    wave_file.setnchannels(1) # mono
    wave_file.setsampwidth(2) # 16-bit
    wave_file.setframerate(sample_rate)
    
    for i in range(num_samples):
        # 440Hz sine wave (A4 note)
        value = int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate))
        data = struct.pack('<h', value)
        wave_file.writeframesraw(data)
        
    wave_file.close()
    print("Generation complete.")

def test_upload():
    print("1. Logging in to acquire access token...")
    login_data = {
        "identifier": "testuser_refresh",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        response.raise_for_status()
        res_json = response.json()
        
        if not res_json.get("success"):
            print("Login failed:", res_json)
            return
            
        token = res_json["data"]["access_token"]
        print("Login successful! Token acquired.")
        
        # Generate 5-second WAV audio file
        wav_filename = "test_voice.wav"
        generate_wav(wav_filename, duration_seconds=5)
        
        print("\n2. Uploading the recorded/generated audio file...")
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        with open(wav_filename, "rb") as f:
            files = {
                "file": (wav_filename, f.read(), "audio/wav")
            }
        
        # Clean up local temp file
        if os.path.exists(wav_filename):
            os.remove(wav_filename)
            
        data = {
            "duration_seconds": 5
        }
        
        upload_response = requests.post(
            f"{BASE_URL}/messages/upload-audio",
            headers=headers,
            files=files,
            data=data
        )
        
        print(f"Status Code: {upload_response.status_code}")
        print("Response Content:")
        import json
        print(json.dumps(upload_response.json(), indent=2))
        
        # Verify if the upload succeeded
        if upload_response.status_code == 200:
            audio_url = upload_response.json()["data"]["audio_url"]
            print(f"\n[SUCCESS] Audio uploaded successfully! Public URL is: {audio_url}")
            
            # Check if it was saved locally (since OCI won't be initialized on local localhost)
            # Find the filename from the URL path
            filename = audio_url.split("/")[-1]
            local_path = os.path.join("static", "uploads", "avatars", "audio", filename)
            if os.path.exists(local_path):
                print(f"[SUCCESS] Verified: Local file exists at: {local_path} ({os.path.getsize(local_path)} bytes)")
            else:
                print(f"[INFO] Local file not found at {local_path} (could be stored on OCI Object Storage if client is initialized)")
                
    except Exception as e:
        print("Error occurred during verification:", str(e))

if __name__ == "__main__":
    test_upload()
