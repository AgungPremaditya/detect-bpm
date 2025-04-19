import os
import uuid

import librosa
import numpy as np
from fastapi import FastAPI, HTTPException
from librosa.beat import tempo
from pydantic import BaseModel
import yt_dlp
from scipy.stats import mode
from starlette.responses import JSONResponse

app = FastAPI()

class YouTubeLink(BaseModel):
    url: str

# Krumhansl-Schmuckler key profiles for major and minor
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(exc: Exception):
    # Global exception
    status_code = 500
    detail = "Internal Server Error"

    # Handle specific exceptions
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
    else:
        error_message = str(exc)
        if error_message:
            detail = f"Error: {error_message}"

    return JSONResponse(status_code=status_code, content={"detail": detail})

# Function to get the key of the song
def estimate_key(audio_path):
    y, sr = librosa.load(audio_path)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    # Major
    major_corrs = [np.corrcoef(np.roll(chroma_mean, -i), MAJOR_PROFILE)[0, 1] for i in range(12)]
    # Minor
    minor_corrs = [np.corrcoef(np.roll(chroma_mean, -i), MINOR_PROFILE)[0, 1] for i in range(12)]
    major_key = np.argmax(major_corrs)
    minor_key = np.argmax(minor_corrs)
    if max(major_corrs) >= max(minor_corrs):
        return KEYS[major_key] + " Major"
    else:
        return KEYS[minor_key] + " Minor"

# Function to check if the link is a music link
def check_music(link):
    info_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            info = ydl.extract_info(link, download=False)

            # Check categories if available
            if 'categories' in info and isinstance(info['categories'], list):
                if any('music' in category.lower() for category in info['categories']):
                    return True

            # Check single category if available
            if 'category' in info and isinstance(info['category'], str):
                if 'music' in info['category'].lower():
                    return True

            # Check title and description for music-related keywords
            music_keywords = ['music', 'song', 'audio', 'track', 'remix', 'album', 'official audio', 'EP']
            title = info.get('title', '').lower()
            description = info.get('description', '').lower()

            if any(keyword in title for keyword in music_keywords) or \
                    any(keyword in description for keyword in music_keywords):
                return True

            # If we reach here, it's not identified as music
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False

# Function to download the audio file
def download_audio(link, output):
    # check if the link is a music link
    if not check_music(link):
        print("WARNING: This is not a music link")
        raise HTTPException(status_code=400, detail="Cannot process: this is not a music link")
    else:
        # download the audio file
        ytdl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
        }

    try:
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            ydl.download([link])
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading audio: {str(e)}")

    print("FINISHED DOWNLOADING")

# Function to calculate the BPM
def calc_bpm(audio_path):
    print("STARTING DETECTING BPM")
    # Load the audio file
    y, sr = librosa.load(audio_path, sr=44100)

    # Get song_tempo and beat frames
    song_tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')

    # Convert beat frames to timestamps
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    # Calculate inter-beat intervals (IBI)
    ibis = np.diff(beat_times)
    if len(ibis) == 0:
        return {"bpm": None, "note": "No beats detected"}

    # Calculate BPMs from IBIs
    ibis_bpm = 60.0 / ibis

    # Find the most common BPM (mode)
    bpm_mode = float(mode(np.round(ibis_bpm), keepdims=True).mode[0])

    # Compare with global song_tempo
    global_bpm = float(song_tempo)

    print("FINISHED DETECTING BPM :"+ str(global_bpm))

    # Check for doubling/halving
    if abs(bpm_mode - global_bpm) > 2:
        if abs(bpm_mode - 2 * global_bpm) < 2:
            bpm = round(global_bpm)
            note = "Detected possible tempo doubling"
        elif abs(bpm_mode - 0.5 * global_bpm) < 2:
            bpm = round(global_bpm)
            note = "Detected possible tempo halving"
        else:
            bpm = round(global_bpm)
            note = "OK"
    else:
        bpm = round(global_bpm)
        note = "OK"

    # Key detection
    key = estimate_key(audio_path)
    return {"bpm": bpm, "note": note, "key": key}

# Get title of the youtube video
def get_title(link):
    ytdl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ytdl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            return info['title']
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.post("/detect-bpm")
def detect_bpm(link: YouTubeLink):
    temp_id = str(uuid.uuid4())
    audio_file = f"./tmp/{temp_id}"
    try:
        download_audio(link.url, audio_file)
        bpm = calc_bpm(audio_file+".wav")
        title = get_title(link.url)
        
        return {
            "title": title,
            "result": bpm
        }
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        import glob
        for file in glob.glob(f"./tmp/{temp_id}*"):
            if os.path.exists(file):
                os.remove(file)