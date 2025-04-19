# YouTube Music BPM & Key Detection API

This project provides a REST API to detect the BPM (beats per minute) and musical key of a song from a YouTube link. It downloads the audio, analyzes it, and returns the BPM, key, and notes about tempo doubling/halving.

## Features

- **Input:** YouTube video link
- **Output:** JSON with BPM, musical key, and tempo doubling/halving note
- **Tech stack:** FastAPI, yt-dlp, librosa, ffmpeg

## Requirements

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) installed and in your PATH

## Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/youtube-bpm-key-api.git
    cd youtube-bpm-key-api
    ```

2. **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Install ffmpeg:**

    - **Ubuntu/Debian:**
        ```bash
        sudo apt-get update
        ```
        ```bash
        sudo apt-get install ffmpeg
        ```
    - **macOS (Homebrew):**
        ```bash
        brew install ffmpeg
        ```
    - **Windows:**  
      Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add to your PATH.

## Usage

1. **Start the API server:**

    ```bash
    uvicorn app.main:app --reload
    ```

2. **Send a POST request to `/bpm`:**

    - **Request body:**
        ```json
        {
          "url": "https://www.youtube.com/watch?v=EXAMPLE"
        }
        ```

    - **Example using `curl`:**
        ```bash
        curl -X POST "http://127.0.0.1:8000/detect-bpm" -H "Content-Type: application/json" -d '{"url": "https://www.youtube.com/watch?v=EXAMPLE"}'
        ```

3. **Response:**
    ```json
    {
      "bpm": {integer},
      "note": {string},
      "key": {string}
    }
    ```

## Project Structure

```
app/
  main.py
requirements.txt
README.md
```

## Notes

- The API may take several seconds to process long YouTube videos.
- Only public YouTube videos are supported.
- For best results, use music tracks with clear beats.

---

**Contributions welcome!**
