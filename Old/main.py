import requests
import isodate
import os
import logging
from logger import setup_logging
from datetime import datetime
from setup_connections import connect_to_database
from clustering import clusteren_van_data, verkrijg_clustering_metadata
from downloaden_videos import video_ids_naar_youtube_urls, download_videos_met_subs, haal_ondertitels_op
from classificatie import classificeer_transcript, bewerk_tekst

def verkrijg_video_ids_via_server(locatie_videos):
    logging.info(f"Locatie videos: {locatie_videos}")
    try:
        video_ids = os.listdir(locatie_videos)
        logging.info(f"Video ids: {video_ids}")
        return video_ids
    except Exception as e:
        logging.error(f"Fout bij het lezen van de map: {e}")
        return []

def verkrijg_metadata(video_id):
    API_KEY = os.getenv('API_KEY')

    url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id={video_id}&key={API_KEY}'
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

            return video_id, title, upload_date, views, comments, likes, duur_in_seconden
    logging.error("Fout bij het verbinden met de API.")
    return None

def duur_naar_seconden_transformeren(duur):
    try:
        parsed_duration = isodate.parse_duration(duur)

        if parsed_duration and hasattr(parsed_duration, 'total_seconds'):
            duur_in_seconden = int(parsed_duration.total_seconds())
            logging.info(f"Geparste duur in seconden: {duur_in_seconden}")
            return duur_in_seconden
        else:
            logging.error(f"Duur kon niet geparsed worden: {parsed_duration}")
            return 0
    except Exception as e:
        logging.error(f"Fout bij het converteren van de duur: {e}")
        return 0

# def metadata_naar_db_inserten(video_data, transcript):
#     connection = maak_verbinding()
#     if not connection:
#         logging.error("Kan niet verbinden met de database.")
#         return
#
#     cursor = None
#     try:
#         cursor = connection.cursor()
#
#         video_id, titel, upload_datum, views, comments, likes, duur_in_seconden = video_data
#
#         # Dimensietabel VIDEO
#         dim_video_query = """
#             INSERT INTO video (video_id, titel, uploaddatum, categorie, duur_in_seconden)
#             VALUES (%s, %s, %s, %s, %s)
#             ON CONFLICT (video_id) DO UPDATE SET titel = EXCLUDED.titel, uploaddatum = EXCLUDED.uploaddatum, duur_in_seconden = EXCLUDED.duur_in_seconden;
#         """
#         cursor.execute(dim_video_query, (video_id, titel, upload_datum, 'Unknown', duur_in_seconden))
#         logging.info(f"Video query insert voor: {video_id}")
#
#         # Dimensietabel TIJD
#         upload_datum_gestript = datetime.strptime(upload_datum, '%Y-%m-%d')
#         dag, maand, jaar = upload_datum_gestript.day, upload_datum_gestript.month, upload_datum_gestript.year
#         dim_tijd_query = """
#             INSERT INTO tijd (dag, maand, jaar)
#             VALUES (%s, %s, %s)
#             RETURNING tijd_id
#             ON CONFLICT (dag, maand, jaar) DO NOTHING;
#         """
#         cursor.execute(dim_tijd_query, (dag, maand, jaar))
#
#         if cursor.rowcount > 0:
#             tijd_id = cursor.fetchone()[0]
#         else:
#             tijd_id = krijg_bestaande_tijd_id(cursor, dag, maand, jaar)
#
#         # Dimensietabel transcript
#         transcript_query = """
#             INSERT INTO transcript (video_id, transcript)
#             VALUES (%s, %s)
#             ON CONFLICT (video_id) DO UPDATE SET transcript = EXCLUDED.transcript
#             WHERE transcript.transcript <> EXCLUDED.transcript;
#         """
#         cursor.execute(transcript_query, (video_id, transcript))
#         logging.info(f"Transcript voor video ID {video_id} opgeslagen in de database.")
#
#         # Feitentabel video_populariteit
#         fact_video_pop_query = """
#             INSERT INTO populariteit (video_id, tijd_id, aantal_views, aantal_reacties, aantal_likes)
#             VALUES (%s, %s, %s, %s, %s)
#             ON CONFLICT (video_id, tijd_id) DO NOTHING;
#         """
#         cursor.execute(fact_video_pop_query, (video_id, tijd_id, views, comments, likes))
#
#         connection.commit()
#         logging.info(f"Video {titel} ingevoegd of bijgewerkt.")
#     except (Exception, psycopg2.DatabaseError) as error:
#         logging.error(f"Fout bij het opslaan van metadata: {error}")
#         if connection:
#             connection.rollback()  # Rol terug als er een fout is opgetreden
#     finally:
#         if cursor:
#             cursor.close()
#         if connection:
#             connection.close()

def insert_video_dimensie(video_data, verbinding):
    try:
        video_id, titel, upload_datum, _, _, _, duur_in_seconden = video_data
        query = """
            INSERT INTO video (video_id, titel, uploaddatum, categorie, duur_in_seconden)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (video_id) DO UPDATE SET titel = EXCLUDED.titel, uploaddatum = EXCLUDED.uploaddatum, duur_in_seconden = EXCLUDED.duur_in_seconden;
        """
        with verbinding.cursor() as cursor:
            cursor.execute(query, (video_id, titel, upload_datum, 'Unknown', duur_in_seconden))
            verbinding.commit()
            logging.info(f"Video dimensie ingevoegd voor video ID {video_id}")
    except Exception as e:
        logging.error(f"Fout bij het invoegen van video dimensie: {e}")
        verbinding.rollback()

def insert_tijd_dimensie(upload_datum, verbinding):
    try:
        upload_datum_gestript = datetime.strptime(upload_datum, '%Y-%m-%d')
        dag = upload_datum_gestript.strftime('%A')  # Verkrijg de naam van de dag (bijv. 'maandag')
        maand, jaar = upload_datum_gestript.month, upload_datum_gestript.year

        query = """
            INSERT INTO tijd (dag, maand, jaar)
            VALUES (%s, %s, %s)
            ON CONFLICT (dag, maand, jaar) DO NOTHING
            RETURNING tijd_id;
        """

        with verbinding.cursor() as cursor:
            cursor.execute(query, (dag, maand, jaar))
            tijd_id = cursor.fetchone()[0] if cursor.rowcount > 0 else krijg_bestaande_tijd_id(cursor, dag, maand, jaar)
            verbinding.commit()
            return tijd_id

    except Exception as e:
        logging.error(f"Fout bij het invoegen van tijd dimensie: {e}")
        return None

def krijg_bestaande_tijd_id(cursor, dag, maand, jaar):
    query = """
        SELECT tijd_id FROM tijd WHERE dag = %s AND maand = %s AND jaar = %s;
        """
    cursor.execute(query, (dag, maand, jaar))

    return cursor.fetchone()[0]

def vergelijk_populariteit(video_id, transcript_schoon):
    popularity_cluster = cluster_data()
    populaire_clusters = [0]
    popularity_cluster['cluster_populariteit'] = popularity_cluster['cluster_label'].apply(
        lambda x: 1 if x in populaire_clusters else 0)

    label = classificeer_transcript(transcript_schoon, "classificatie_model.pkl", "nlp_model.pkl")
    logging.info(f"Video ID {video_id} geclassificeerd als: {label}")

    cluster_waarde = popularity_cluster.loc[popularity_cluster['video_id'] == video_id, 'cluster_populariteit'].values
    is_populair_cluster = cluster_waarde[0] if len(cluster_waarde) > 0 else 0

    if is_populair_cluster == 1 or label == 'populair':
        return 'populair'
    else:
        return 'niet populair'

def insert_transcript(video_id, transcript, verbinding):
    try:
        query_check = "SELECT transcript_id FROM public.transcript WHERE video_id = %s;"

        with verbinding.cursor() as cursor:
            cursor.execute(query_check, (video_id,))
            result = cursor.fetchone()

            if result:
                transcript_id = result[0]
                query_update = "UPDATE public.transcript SET transcript = %s WHERE transcript_id = %s;"
                cursor.execute(query_update, (transcript, transcript_id))
                logging.info(f"Transcript bijgewerkt voor video ID: {video_id}")
            else:
                query_insert = "INSERT INTO public.transcript (video_id, transcript) VALUES (%s, %s) RETURNING transcript_id;"
                cursor.execute(query_insert, (video_id, transcript))
                new_transcript_id = cursor.fetchone()[0]
                logging.info(f"Nieuw transcript toegevoegd voor video ID: {video_id} met transcript ID: {new_transcript_id}")

            verbinding.commit()
    except Exception as e:
        logging.error(f"Fout bij het bijwerken of invoegen van transcript voor video ID {video_id}: {e}")
        verbinding.rollback()

def insert_populariteit(video_data, tijd_id, verbinding):
    try:
        video_id, _, _, views, comments, likes, _ = video_data
        query = """
            INSERT INTO populariteit (video_id, tijd_id, aantal_views, aantal_reacties, aantal_likes)
            VALUES (%s, %s, %s, %s, %s);
        """
        with verbinding.cursor() as cursor:
            cursor.execute(query, (video_id, tijd_id, views, comments, likes))
            verbinding.commit()
            logging.info(f"Populariteit dimensie ingevoegd voor video ID {video_id}")
    except Exception as e:
        logging.error(f"Fout bij het invoegen van populariteit dimensie: {e}")
        verbinding.rollback()


def vul_de_database():
    verbinding = connect_to_database()
    if not verbinding:
        logging.error("Geen geldige databaseverbinding.")
        return
    logging.info("Databaseverbinding succesvol.")

    locatie_videos = 'data/video'
    logging.info("Vul de database wordt aangeroepen...")
    video_ids = verkrijg_video_ids_via_server(locatie_videos)

    try:
        for video_id in video_ids:
            video_data = verkrijg_metadata(video_id)

            if video_data:
                insert_video_dimensie(video_data, verbinding)
                tijd_id = insert_tijd_dimensie(video_data[2], verbinding)

                video_urls = video_ids_naar_youtube_urls([video_id])
                alle_transcripts = download_videos_met_subs(video_urls)
                transcript = alle_transcripts.get(video_urls[0], ["Geen informatie gevonden"])
                transcript_schoon = " ".join([bewerk_tekst(tekst) for tekst in transcript]) if transcript != [
                    "Geen informatie gevonden"] else None

                if transcript_schoon:
                    insert_transcript(video_id, transcript_schoon, verbinding)

                insert_populariteit(video_data, tijd_id, verbinding)

                label = vergelijk_populariteit(video_id, transcript_schoon)
                update_label_in_db(video_id, label)

            else:
                logging.error(f"Geen metadata gevonden voor video ID {video_id}. Deze wordt overgeslagen.")
                continue

    except Exception as e:
        logging.error(f"Fout bij het vullen van de database: {e}")
    finally:
        verbinding.close()

def cluster_data():
    clust_metadata = verkrijg_clustering_metadata()
    populariteit_clus = clusteren_van_data(clust_metadata)
    return populariteit_clus

def update_label_in_db(video_id, label):
    try:
        with connect_to_database() as verbinding:
            with verbinding.cursor() as cursor:
                update_query = """
                UPDATE videos
                SET populariteit = %s
                WHERE video_id = %s
                """
                cursor.execute(update_query, (label, video_id))
                verbinding.commit()
                logging.info(f"Label voor video ID {video_id} bijgewerkt naar: {label}")
    except Exception as e:
        logging.error(f"Fout bij het bijwerken van label voor video ID {video_id}: {e}")


if __name__ == '__main__':
    setup_logging()
    print("Start programma")
    vul_de_database()

