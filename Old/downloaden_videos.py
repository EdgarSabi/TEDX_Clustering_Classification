import os
import yt_dlp
import logging
from pathlib import Path

# def video_ids_naar_youtube_urls(video_ids):
#     basis_url = 'https://www.youtube.com/watch?v='
#     complete_urls = []
#
#     for video_id in video_ids:
#         complete_url = basis_url + video_id
#         complete_urls.append(complete_url)
#         logging.info(f"De URL voor de video: {complete_url}")
#
#     return complete_urls
#
# def check_captions_aanwezig(video_url):
#     ydl_opts = {'quiet': True}
#     with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#         info_dict = ydl.extract_info(video_url, download=False)
#         captions = info_dict.get('subtitles')
#         if captions:
#             logging.info(f"Beschikbare ondertitels voor {video_url}: {list(captions.keys())}")
#             return True
#         else:
#             logging.warning(f"Geen ondertitels beschikbaar voor {video_url}")
#             return False
#
# def download_videos_met_subs(video_urls):
#     download_locatie = '/s1146363/downloads'
#
#     if not os.path.exists(download_locatie):
#         os.makedirs(download_locatie)
#         logging.info(f"Geen download locatie aanwezig. {download_locatie} gemaakt.")
#
#     ydl_opts = {
#         'format': 'best',
#         'outtmpl': os.path.join(download_locatie, '%(title)s.%(ext)s'),
#         'writesubtitles': True,
#         'subtitlesformat': 'vtt',
#         'skip_download': True,
#     }
#
#     alle_transcripts = {}
#
#     for url in video_urls:
#         video_id = url.split('=')[-1]
#         try:
#             with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#                 ydl.download([url])
#             logging.info(f"Download succesvol voor: {url}")
#
#             transcript = haal_ondertitels_op(download_locatie, video_id)
#             if transcript and transcript != ["Geen transcript beschikbaar"]:
#                 logging.info(f"Ondertitels opgehaald voor {url}: {len(transcript)} bestanden gevonden.")
#             else:
#                 logging.warning(f"Geen ondertitels gevonden voor {url}")
#                 transcript = ["Geen transcript beschikbaar"]
#
#             alle_transcripts[video_id] = transcript
#
#         except Exception as e:
#             logging.error(f"Fout bij downloaden van {url}: {e}")
#             alle_transcripts[url] = ["Fout bij ophalen van ondertitels"]
#
#     return alle_transcripts
#
# def haal_ondertitels_op(download_locatie, video_id):
#     ondertitel_bestanden = list(Path(download_locatie).glob('*.vtt'))
#     tekst_lijst = []
#
#     if not ondertitel_bestanden:
#         logging.warning("Geen ondertitels gevonden in de downloadlocatie.")
#         return ["Geen transcript beschikbaar"]
#
#     for bestand in ondertitel_bestanden:
#         if video_id in str(bestand):
#             with open(bestand, 'r', encoding='utf-8') as f:
#                 inhoud = f.read()
#                 tekst_lijst.append(inhoud)
#
#     if not tekst_lijst:
#         logging.warning(f"Geen ondertitels gevonden voor video_id {video_id}.")
#         return ["Geen transcript beschikbaar"]
#
#     return tekst_lijst


from pytube import YouTube


def Download(link):
    youtubeObject = YouTube(link)
    youtubeObject = youtubeObject.streams.get_lowest_resolution()

    try:
        youtubeObject.download()
    except:
        print("An error has occurred")

    print("Download is completed successfully")


# Voer hier de URL in die je wilt downloaden.
Download('https://www.youtube.com/watch?v=9G0dsV6G4Mc')

