import os
import logging
import isodate
import requests
import warnings
import re
import whisper
from dotenv import load_dotenv
from yt_dlp import YoutubeDL

from logger import setup_logging
from setup_connections import connect_to_server

setup_logging()

load_dotenv()

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Create downloads directory if it doesn't exist
os.makedirs('downloads', exist_ok=True)

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

def get_meta_data(video_id):
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

                logging.info(f"Successfully retrieved metadata for video ID: {video_id}")
                return video_id, title, upload_date, views, comments, likes, duur_in_seconden
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

def video_ids_naar_youtube_urls(video_ids):
    try:
        if not video_ids:
            logging.warning("Empty list of video IDs provided")
            return []

        basis_url = 'https://www.youtube.com/watch?v='
        complete_urls = []

        for video_id in video_ids:
            if not video_id:
                logging.warning("Empty video ID encountered, skipping")
                continue

            try:
                complete_url = basis_url + str(video_id)
                complete_urls.append(complete_url)
                logging.info(f"URL for video: {complete_url}")
            except Exception as e:
                logging.warning(f"Error creating URL for video ID {video_id}: {e}")

        logging.info(f"Created {len(complete_urls)} YouTube URLs")
        return complete_urls
    except Exception as e:
        logging.error(f"Unexpected error converting video IDs to URLs: {e}")
        return []



def clean_text(text):
    """
    Clean up text by removing unwanted characters and formatting

    Args:
        text (str): Text to clean

    Returns:
        str: Cleaned text
    """
    try:
        if not text:
            logging.warning("Empty text provided for cleaning")
            return ""

        # Remove text within parentheses
        text = re.sub(r'\([^)]*\)', '', text)

        # Convert to lowercase
        text = text.lower()

        # Replace multiple newlines with a single space
        text = re.sub(r'\n+', ' ', text)

        # Remove all characters except lowercase letters and spaces
        text = re.sub(r'[^a-z\s]', '', text)

        # Strip leading and trailing whitespace
        text = text.strip()

        return text
    except AttributeError as e:
        logging.warning(f"AttributeError cleaning text: {e}")
        return ""
    except Exception as e:
        logging.warning(f"Unexpected error cleaning text: {e}")
        return ""


def download_captions(video_url):
    # Ensure downloads directory exists
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

    options = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,
        'outtmpl': 'downloads/%(id)s.%(ext)s'
    }

    try:
        with YoutubeDL(options) as ydl:
            ydl.download([video_url])
            logging.info(f"Successfully downloaded captions for {video_url}")
            return True
    except Exception as e:
        error_msg = f"Error downloading captions for {video_url}: {e}"
        logging.error(error_msg)
        print(error_msg)
        return False

def read_captions(video_id):
    """
    Read captions for a YouTube video or generate a transcript if captions are not available.

    This function first tries to find existing caption files (.vtt) for the video.
    If captions aren't found, it downloads the audio and uses Whisper to generate a transcript.
    After successful transcription, the audio file is automatically deleted to save disk space.

    Args:
        video_id (str): YouTube video ID

    Returns:
        str: Caption text or transcript, or error message if retrieval failed
    """
    # Ensure downloads directory exists
    os.makedirs('downloads', exist_ok=True)

    filepath = f"downloads/{video_id}.en.vtt"

    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as file:
                caption_text = file.read()
                logging.info(f"Successfully read captions from file for video ID: {video_id}")
                return caption_text

        logging.info(f"Captions file not found for {video_id}, attempting to use Whisper for transcription")
        print("Captions not found, using Whisper...")

        # Try to download the video's audio
        audio_path = download_audio(video_id)
        if not audio_path:
            error_msg = f"Failed to download audio for video ID: {video_id}"
            logging.error(error_msg)
            return f"Error: {error_msg}"

        # Try to transcribe the audio using Whisper
        transcript = generate_transcript(audio_path)
        if transcript:
            logging.info(f"Successfully generated transcript for video ID: {video_id}")
            # Delete the audio file after successful transcription
            if delete_audio_file(audio_path):
                logging.info(f"Deleted audio file for video ID: {video_id} after transcription")
            else:
                logging.warning(f"Failed to delete audio file for video ID: {video_id}")
            return transcript
        else:
            error_msg = f"Failed to generate transcript for video ID: {video_id}"
            logging.error(error_msg)
            # Try to delete the audio file even if transcription failed
            delete_audio_file(audio_path)
            return f"Error: {error_msg}"

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
    # Ensure downloads directory exists
    os.makedirs('downloads', exist_ok=True)

    # Check if audio file already exists
    common_extensions = ['mp3', 'm4a', 'webm', 'opus']
    for ext in common_extensions:
        existing_path = f"downloads/{video_id}.{ext}"
        if os.path.exists(existing_path):
            logging.info(f"Audio file already exists at {existing_path}, skipping download")
            return existing_path

    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = f"downloads/{video_id}.%(ext)s"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info['ext']
            audio_path = f"downloads/{video_id}.{ext}"

            # Verify the file was actually downloaded
            if not os.path.exists(audio_path):
                error_msg = f"Audio file was not created at expected path: {audio_path}"
                logging.error(error_msg)
                print(error_msg)
                return None

            return audio_path
    except Exception as e:
        error_msg = f"Download error: {e}"
        logging.error(error_msg)
        print(error_msg)
        return None

def generate_transcript(audio_path):
    try:
        if not os.path.exists(audio_path):
            logging.error(f"Audio file not found: {audio_path}")
            return f"Error: Audio file not found at {audio_path}"

        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result['text']
    except Exception as e:
        error_msg = f"Whisper error: {e}"
        logging.error(error_msg)
        print(error_msg)
        return None

def delete_audio_file(audio_path):
    """
    Delete an audio file after it has been transcribed.

    Args:
        audio_path (str): Path to the audio file to delete

    Returns:
        bool: True if deletion was successful, False otherwise
    """
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


def get_and_clean_captions(video_id):
    """
    Get and clean captions for a YouTube video.

    This function retrieves captions for a given video ID using read_captions,
    then cleans the text using clean_text to remove unwanted characters and formatting.

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
        if not raw_captions or raw_captions.startswith("Error:"):
            logging.warning(f"Failed to retrieve captions for video ID: {video_id}")
            return ""

        # Clean the captions
        cleaned_captions = clean_text(raw_captions)

        logging.info(f"Successfully cleaned captions for video ID: {video_id}")
        return cleaned_captions
    except Exception as e:
        logging.error(f"Error in get_and_clean_captions for video ID {video_id}: {e}")
        return ""


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
