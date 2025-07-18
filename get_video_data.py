import os
import logging
import isodate
import requests
import warnings
import re
import whisper
from dotenv import load_dotenv
from yt_dlp import YoutubeDL

from classification import preprocess_text
from logger import setup_logging
from setup_connections import connect_to_server

setup_logging()

load_dotenv()

warnings.filterwarnings("ignore", category=DeprecationWarning)

def get_video_ids():
    try:
        path = '/data/video'

        ssh_client = connect_to_server()
        if not ssh_client:
            logging.error("Failed to connect to the server")
            return None

        logging.info("Successfully connected to the server")

        sftp_client = ssh_client.open_sftp()
        logging.info("SFTP connection established")

        folders = sftp_client.listdir(path)

        logging.info(f"Found {len(folders)} folders in {path}")

        sftp_client.close()
        ssh_client.close()
        logging.info("SSH and SFTP connections closed")

        return folders
    except Exception as e:
        logging.error(f"Error getting video IDs: {e}")
        return None

def get_meta_data(video_id, skip_captions=False):
    try:
        API_KEY = os.getenv('API_KEY')
        if not API_KEY:
            logging.error("API_KEY not found in environment variables")
            return None

        url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={video_id}&key={API_KEY}'
        logging.info(f"Fetching metadata for video ID: {video_id}")

        response = requests.get(url)

        if response.status_code == 200:
            video_data = response.json()
            if 'items' in video_data and len(video_data['items']) > 0:
                video_info = video_data['items'][0]
                title = video_info['snippet']['title']
                upload_date = video_info['snippet']['publishedAt'].split("T")[0]
                views = int(video_info['statistics'].get('viewCount', 0))
                comments = int(video_info['statistics'].get('commentCount', 0))
                likes = int(video_info['statistics'].get('likeCount', 0))
                duur = video_info['contentDetails']['duration']
                duur_in_seconden = duur_naar_seconden_transformeren(duur)

                category_id = int(video_info['snippet'].get('categoryId', 0))

                # tags = video_info['snippet'].get('tags', [])
                
                # Get transcriptions (skip if requested)
                if skip_captions:
                    logging.info(f"Skipping caption retrieval for video ID: {video_id} as it already exists in the database")
                    transcription = "CAPTION_SKIPPED"  # Placeholder, will be ignored during insert/update
                else:
                    transcription = get_and_clean_captions(video_id)

                logging.info(f"Successfully retrieved metadata for video ID: {video_id}")
                return video_id, title, upload_date, views, comments, likes, duur_in_seconden, category_id, transcription
            else:
                logging.error(f"No items found in API response for video ID: {video_id}")
        else:
            logging.error(f"API request failed with status code: {response.status_code}")

        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error when fetching metadata for video ID {video_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error when fetching metadata for video ID {video_id}: {e}")
        return None

def duur_naar_seconden_transformeren(duur):
    try:
        if not duur:
            logging.warning("Empty duration string provided")
            return 0

        parsed_duration = isodate.parse_duration(duur)

        if parsed_duration and hasattr(parsed_duration, 'total_seconds'):
            duur_in_seconden = int(parsed_duration.total_seconds())
            return duur_in_seconden
        else:
            logging.warning(f"Could not convert duration '{duur}' to seconds")
            return 0
    except isodate.isoerror.ISO8601Error as e:
        logging.warning(f"Invalid ISO 8601 duration format: {duur}, error: {e}")
        return 0
    except Exception as e:
        logging.warning(f"Unexpected error converting duration '{duur}' to seconds: {e}")
        return 0

# def video_ids_naar_youtube_urls(video_ids):
#     try:
#         if not video_ids:
#             logging.warning("Empty list of video IDs provided")
#             return []
#
#         basis_url = 'https://www.youtube.com/watch?v='
#         complete_urls = []
#
#         for video_id in video_ids:
#             if not video_id:
#                 logging.warning("Empty video ID encountered, skipping")
#                 continue
#
#             try:
#                 complete_url = basis_url + str(video_id)
#                 complete_urls.append(complete_url)
#                 logging.info(f"URL for video: {complete_url}")
#             except Exception as e:
#                 logging.warning(f"Error creating URL for video ID {video_id}: {e}")
#
#         logging.info(f"Created {len(complete_urls)} YouTube URLs")
#         return complete_urls
#     except Exception as e:
#         logging.error(f"Unexpected error converting video IDs to URLs: {e}")
#         return []

def clean_text(text):
    """
    Clean up text by removing unwanted characters and formatting
    
    Specifically handles:
    - WebVTT headers (like "WEBVTT" or "kind: captions language: en")
    - Noise indicators in square brackets (like "[thud]" or "[music]")
    - Random 'c' characters that appear as suffixes to words (like "yourecc", "wonderingcc")
    - Other formatting and special characters

    Args:
        text (str): Text to clean

    Returns:
        str: Cleaned text
    """
    try:
        if not text:
            logging.warning("Empty text provided for cleaning")
            return "No text to clean"

        # Remove WebVTT headers (typically at the beginning of the file)
        text = re.sub(r'^WEBVTT.*?\n\n', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove timestamp lines (format: 00:00:00.000 --> 00:00:00.000)
        text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*?\n', '', text)
        
        # Remove text within square brackets (noise indicators like [thud])
        text = re.sub(r'\[[^\]]*\]', ' ', text)
        
        # Remove text within parentheses
        text = re.sub(r'\([^)]*\)', ' ', text)

        # Convert to lowercase
        text = text.lower()

        # Replace multiple newlines with a single space
        text = re.sub(r'\n+', ' ', text)
        
        # Remove random 'c' characters that appear throughout the text
        
        # First, handle the repetition of text with and without 'c' characters
        # This is a common pattern in the captions where the same text appears multiple times
        # with and without random 'c' characters
        words = text.split()
        cleaned_text = []
        i = 0
        while i < len(words):
            # Skip words that are just 'c'
            if words[i] == 'c':
                i += 1
                continue
                
            # Add the current word
            cleaned_text.append(words[i])
            
            # Check if this word appears again soon (possibly with 'c's)
            j = i + 1
            while j < len(words) and j < i + 10:  # Look ahead up to 10 words
                # If words are similar except for 'c's, skip the later occurrence
                if words[i].replace('c', '') == words[j].replace('c', ''):
                    j += 1
                else:
                    break
            i = j
        
        # Rejoin the cleaned words
        text = ' '.join(cleaned_text)
        
        # Now handle the remaining 'c' characters
        
        # Handle multiple consecutive 'c's (like "cc")
        text = re.sub(r'c{2,}', '', text)
        
        # Handle 'c' at the end of words (like "stopc")
        text = re.sub(r'c(?=\s|$)', '', text)
        
        # Handle 'c' at the beginning of words (like "cclimate")
        # Split into words, process each word, then rejoin
        words = text.split()
        for i in range(len(words)):
            if words[i].startswith('c') and len(words[i]) > 1:
                words[i] = words[i][1:]  # Remove the leading 'c'
        text = ' '.join(words)
        
        # Handle 'c' in the middle of words that are likely noise
        # We'll use a whitelist approach to preserve 'c' in common English words
        # and remove it in other contexts
        common_c_words = ['climate', 'change', 'can', 'cause', 'because', 'science', 
                         'direction', 'companies', 'governments', 'incentivize']
        
        words = text.split()
        for i in range(len(words)):
            # Skip words that are in our whitelist
            if any(c_word in words[i] for c_word in common_c_words):
                continue
                
            # For other words, remove any remaining 'c's
            words[i] = words[i].replace('c', '')
        
        text = ' '.join(words)

        # Remove all characters except lowercase letters and spaces
        text = re.sub(r'[^a-z\s]', '', text)

        # Strip leading and trailing whitespace
        text = text.strip()

        return text
    except AttributeError as e:
        error_msg = f"AttributeError cleaning text: {e}"
        logging.warning(error_msg)
        return f"Error cleaning text: {error_msg}"
    except Exception as e:
        error_msg = f"Unexpected error cleaning text: {e}"
        logging.warning(error_msg)
        return f"Error cleaning text: {error_msg}"

def download_captions(video_url):
    os.makedirs('downloads', exist_ok=True)

    # Extract video_id from the URL
    video_id = video_url.split('v=')[-1]
    if '&' in video_id:
        video_id = video_id.split('&')[0]

    # Check if captions file already exists
    caption_path = f"downloads/{video_id}.en.vtt"
    if os.path.exists(caption_path):
        logging.info(f"Captions file already exists at {caption_path}, skipping download")
        return True

    # Define progress hook to track download progress
    def progress_hook(d):
        if d['status'] == 'downloading':
            logging.debug(f"Downloading captions: {d.get('_percent_str', 'unknown progress')}")
        elif d['status'] == 'finished':
            logging.info(f"Captions download finished for video ID: {video_id}")
        elif d['status'] == 'error':
            logging.error(f"Error during captions download: {d.get('error', 'Unknown error')}")

    options = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'progress_hooks': [progress_hook],
        'verbose': False,  # Set to True for more detailed output
        'no_warnings': False,  # Show warnings
        'ignoreerrors': False,  # Don't ignore errors
        'geo_bypass': True,  # Try to bypass geo-restrictions
        'socket_timeout': 30,  # Increase timeout for slow connections
        'retries': 10,  # Number of retries for HTTP requests
        'fragment_retries': 10,  # Number of retries for fragments
        'skip_unavailable_fragments': True,  # Skip unavailable fragments
    }

    try:
        logging.info(f"Starting captions download for video ID: {video_id} using yt-dlp")
        with YoutubeDL(options) as ydl:
            ydl.download([video_url])

            if os.path.exists(caption_path):
                file_size = os.path.getsize(caption_path)
                logging.info(f"Successfully downloaded captions for {video_url}, size: {file_size} bytes")
                return True
            else:
                possible_extensions = ['.en.vtt', '.en.srv1', '.en.srv2', '.en.srv3', '.en.ttml', '.en.srt']
                for ext in possible_extensions:
                    alt_path = f"downloads/{video_id}{ext}"
                    if os.path.exists(alt_path):
                        logging.info(f"Found captions in alternative format: {alt_path}")
                        return True
                
                logging.warning(f"Captions file not found after download attempt for {video_url}")
                return False
    except Exception as e:
        error_msg = f"Error downloading captions for {video_url}: {e}"
        logging.error(error_msg)
        print(error_msg)
        
        if "subtitles" in str(e).lower():
            logging.error("Subtitle extraction error. The video might not have any subtitles available.")
            print("Subtitle extraction error. The video might not have any subtitles available.")
        
        return False

def read_captions(video_id):
    filepath = f"downloads/{video_id}.en.vtt"

    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as file:
                caption_text = file.read()
                logging.info(f"Successfully read captions from file for video ID: {video_id}")
                return caption_text

        logging.info(f"Captions file not found locally for {video_id}, attempting to download captions")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        if download_captions(video_url):
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as file:
                    caption_text = file.read()
                    logging.info(f"Successfully downloaded and read captions for video ID: {video_id}")
                    return caption_text
            else:
                logging.warning(f"Captions download reported success but file not found for {video_id}")

        logging.info(f"Captions not available for {video_id}, falling back to Whisper for transcription")
        print("Captions not available, using Whisper...")

        audio_path = download_audio(video_id)
        if not audio_path:
            error_msg = f"Failed to download audio for video ID: {video_id}"
            logging.error(error_msg)
            return f"Error: {error_msg}"

        # Try to transcribe the audio using Whisper
        transcript = generate_transcript(audio_path)
        if transcript and not transcript.startswith("Error:"):
            logging.info(f"Successfully generated transcript for video ID: {video_id}")
            # Delete the audio file after successful transcription
            if delete_audio_file(audio_path):
                logging.info(f"Deleted audio file for video ID: {video_id} after transcription")
            else:
                logging.warning(f"Failed to delete audio file for video ID: {video_id}")
            return transcript
        else:
            # If transcript is None or starts with "Error:", return the error message or a generic one
            error_msg = transcript if transcript and transcript.startswith("Error:") else f"Failed to generate transcript for video ID: {video_id}"
            logging.error(f"Transcription failed: {error_msg}")
            # Try to delete the audio file even if transcription failed
            delete_audio_file(audio_path)
            return error_msg if error_msg.startswith("Error:") else f"Error: {error_msg}"

    except Exception as e:
        error_msg = f"Unexpected error reading captions for video ID {video_id}: {e}"
        logging.error(error_msg)
        print(error_msg)

        # Try to clean up audio file if it exists
        try:
            # Check if audio_path is defined in this scope
            if 'audio_path' in locals() and audio_path:
                delete_audio_file(audio_path)
                logging.info(f"Attempted to delete audio file after exception for video ID: {video_id}")
        except Exception as cleanup_error:
            logging.warning(f"Error during cleanup after exception for video ID {video_id}: {cleanup_error}")

        return f"Error: {error_msg}"


def download_audio(video_id):
    os.makedirs('downloads', exist_ok=True)

    webm_path = f"downloads/{video_id}.webm"
    if os.path.exists(webm_path):
        file_size = os.path.getsize(webm_path)
        logging.info(f"WebM audio file already exists at {webm_path}, size: {file_size} bytes, skipping download")
        return webm_path

    other_extensions = ['m4a', 'mp3', 'opus']
    for ext in other_extensions:
        existing_path = f"downloads/{video_id}.{ext}"
        if os.path.exists(existing_path):
            logging.info(f"Audio file already exists at {existing_path}, will use as is")
            return existing_path

    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = f"downloads/{video_id}.%(ext)s"

    # Define progress hook to track download progress
    def progress_hook(d):
        if d['status'] == 'downloading':
            if 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes'] > 0:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                logging.debug(f"Download progress: {percent:.1f}% of {d['total_bytes'] / 1024 / 1024:.1f} MB")
        elif d['status'] == 'finished':
            logging.info(f"Download finished")
        elif d['status'] == 'error':
            logging.error(f"Error during download: {d.get('error', 'Unknown error')}")

    ydl_opts = {
        'format': 'bestaudio[ext=webm]/bestaudio/best[ext=webm]/best',
        'outtmpl': output_path,
        'quiet': True,
        'progress_hooks': [progress_hook],
        'verbose': False,  # Set to True for more detailed output
        'no_warnings': False,  # Show warnings
        'ignoreerrors': False,  # Don't ignore errors
        'geo_bypass': True,  # Try to bypass geo-restrictions
        'socket_timeout': 30,  # Increase timeout for slow connections
        'retries': 10,  # Number of retries for HTTP requests
        'fragment_retries': 10,  # Number of retries for fragments
        'skip_unavailable_fragments': True,  # Skip unavailable fragments
        # No postprocessors to keep the original webm format
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            logging.info(f"Starting download for video ID: {video_id} using yt-dlp")
            info = ydl.extract_info(url, download=True)
            
            # Get the actual extension from the downloaded file
            ext = info.get('ext', 'webm')
            audio_path = f"downloads/{video_id}.{ext}"

            # Verify the file was actually downloaded
            if not os.path.exists(audio_path):
                # Try with webm as fallback
                fallback_path = f"downloads/{video_id}.webm"
                if os.path.exists(fallback_path):
                    audio_path = fallback_path
                else:
                    error_msg = f"Audio file was not created at expected path: {audio_path}"
                    logging.error(error_msg)
                    print(error_msg)
                    return None
            
            # Log file size
            file_size = os.path.getsize(audio_path)
            logging.info(f"Successfully downloaded audio file: {audio_path}, size: {file_size} bytes, format: {ext}")

            return audio_path
    except Exception as e:
        error_msg = f"Download error: {e}"
        logging.error(error_msg)
        print(error_msg)
        
        # Try to provide more specific error information
        if "format" in str(e).lower() or "codec" in str(e).lower():
            logging.error("Format error detected. The requested webm format might not be available.")
            print("Format error detected. The requested webm format might not be available.")
        
        return None

def generate_transcript(audio_path):
    try:
        if not os.path.exists(audio_path):
            logging.error(f"Audio file not found: {audio_path}")
            return f"Error: Audio file not found at {audio_path}"

        file_size = os.path.getsize(audio_path)
        file_ext = os.path.splitext(audio_path)[1]
        logging.info(f"Audio file details - Path: {audio_path}, Size: {file_size} bytes, Format: {file_ext}")
        
        # Check if file has valid size
        if file_size < 1024:  # Less than 1KB is suspicious
            logging.warning(f"Audio file is suspiciously small ({file_size} bytes), may be corrupted or empty")
            if file_size == 0:
                logging.error("Audio file is empty (0 bytes), cannot transcribe")
                return f"Error: Audio file is empty (0 bytes)"

        logging.info(f"Using path for transcription: {audio_path}")
        
        try:
            with open(audio_path, 'rb') as f:
                # Just read a small portion to verify file access
                f.read(1024)
            logging.info(f"Successfully verified file access to: {audio_path}")
        except Exception as e:
            logging.error(f"Failed to access audio file: {audio_path}, Error: {e}")
            return f"Error: Failed to access audio file: {e}"

        # Load model and transcribe
        logging.info("Loading Whisper model...")
        model = whisper.load_model("base")
        logging.info(f"Starting transcription of file: {audio_path}")
        result = model.transcribe(audio_path)
        logging.info(f"Transcription completed successfully, text length: {len(result['text'])}")
        return result['text']
    except Exception as e:
        error_msg = f"Whisper error: {e}"
        logging.error(error_msg)
        print(error_msg)
        return f"Error: {error_msg}"

def delete_audio_file(audio_path):

    try:
        if not audio_path or not os.path.exists(audio_path):
            logging.warning(f"Audio file not found for deletion: {audio_path}")
            return False

        os.remove(audio_path)
        logging.info(f"Successfully deleted audio file: {audio_path}")
        return True
    except Exception as e:
        logging.error(f"Error deleting audio file {audio_path}: {e}")
        return False


def delete_caption_file(video_id):
    """
    Delete a caption file after it has been processed and inserted into the database.

    Args:
        video_id (str): YouTube video ID

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        filepath = f"downloads/{video_id}.en.vtt"
        if not os.path.exists(filepath):
            logging.warning(f"Caption file not found for deletion: {filepath}")
            return False

        os.remove(filepath)
        logging.info(f"Successfully deleted caption file: {filepath}")
        return True
    except Exception as e:
        logging.error(f"Error deleting caption file for video ID {video_id}: {e}")
        return False


def get_and_clean_captions(video_id):
    """
    Get and clean captions for a YouTube video.

    This function retrieves captions for a given video ID using read_captions,
    then cleans the text using clean_text to remove unwanted characters and formatting.
    After successful processing, the caption file is deleted to save disk space.

    Args:
        video_id (str): YouTube video ID

    Returns:
        str: Cleaned captions text, or empty string if captions could not be retrieved
    """
    try:
        logging.info(f"Getting and cleaning captions for video ID: {video_id}")

        # Get raw captions
        raw_captions = read_captions(video_id)

        # Check if captions were retrieved successfully
        if not raw_captions:
            logging.warning(f"Failed to retrieve captions for video ID: {video_id}")
            return "No captions available"
        elif raw_captions.startswith("Error:"):
            logging.warning(f"Error retrieving captions for video ID: {video_id}: {raw_captions}")
            return raw_captions  # Return the error message as the transcript

        # Clean the captions
        cleaned_captions = preprocess_text(raw_captions)

        logging.info(f"Successfully cleaned captions for video ID: {video_id}")
        
        # Note: We don't delete the caption file here because it will be deleted
        # after the transcription is successfully inserted into the database

        
        return cleaned_captions
    except Exception as e:
        error_msg = f"Error in get_and_clean_captions for video ID {video_id}: {e}"
        logging.error(error_msg)
        return f"Error: {error_msg}"


# if __name__ == '__main__':
#
#     video_ids = get_video_ids()
#     if video_ids:
#         for video_id in video_ids:
#             metadata = get_meta_data(video_id)
#             if metadata:
#                 print(f"Metadata for {video_id}: {metadata}")
#
#             captions = read_captions(video_id)
#             if captions:
#                 print(f"Captions for {video_id} (first 100 chars): {captions[:100]}...")
#             else:
#                 print(f"No captions available for {video_id}")
