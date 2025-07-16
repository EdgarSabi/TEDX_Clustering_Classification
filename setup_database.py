import logging
import psycopg2
from datetime import datetime
from setup_connections import connect_to_database

def insert_video_dimensie(video_data, verbinding):
    """
    Insert video dimension data into the database

    Args:
        video_data (tuple): Tuple containing video metadata (video_id, title, upload_date, views, comments, likes, duration)
        verbinding: Database connection

    Returns:
        None
    """
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
    """
    Insert time dimension data into the database

    Args:
        upload_datum (str): Upload date in format 'YYYY-MM-DD'
        verbinding: Database connection

    Returns:
        int: tijd_id of the inserted or existing time dimension
    """
    try:
        upload_datum_gestript = datetime.strptime(upload_datum, '%Y-%m-%d')
        dag = upload_datum_gestript.strftime('%A')  # Get day name (e.g., 'Monday')
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
    """
    Get the existing tijd_id for a given day, month, and year

    Args:
        cursor: Database cursor
        dag (str): Day name
        maand (int): Month number
        jaar (int): Year

    Returns:
        int: tijd_id of the existing time dimension
    """
    query = """
        SELECT tijd_id FROM tijd WHERE dag = %s AND maand = %s AND jaar = %s;
        """
    cursor.execute(query, (dag, maand, jaar))

    return cursor.fetchone()[0]

def insert_transcript(video_id, transcript, verbinding):
    """
    Insert or update transcript data in the database

    Args:
        video_id (str): YouTube video ID
        transcript (str): Cleaned transcript text
        verbinding: Database connection

    Returns:
        None
    """
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
    """
    Insert popularity data into the database

    Args:
        video_data (tuple): Tuple containing video metadata (video_id, title, upload_date, views, comments, likes, duration)
        tijd_id (int): tijd_id of the time dimension
        verbinding: Database connection

    Returns:
        None
    """
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

def update_label_in_db(video_id, label, verbinding=None):
    """
    Update the popularity label for a video in the database

    Args:
        video_id (str): YouTube video ID
        label (str): Popularity label ('populair' or 'niet populair')
        verbinding: Database connection (optional, will create a new connection if None)

    Returns:
        None
    """
    close_connection = False
    try:
        if verbinding is None:
            verbinding = connect_to_database()
            close_connection = True

        if verbinding:
            with verbinding.cursor() as cursor:
                update_query = """
                UPDATE video
                SET populariteit = %s
                WHERE video_id = %s
                """
                cursor.execute(update_query, (label, video_id))
                verbinding.commit()
                logging.info(f"Label voor video ID {video_id} bijgewerkt naar: {label}")
    except Exception as e:
        logging.error(f"Fout bij het bijwerken van label voor video ID {video_id}: {e}")
        if verbinding:
            verbinding.rollback()
    finally:
        if close_connection and verbinding:
            verbinding.close()
