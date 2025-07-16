import logging
import psycopg2
from datetime import datetime
from setup_connections import connect_to_database

# def insert_video_dimensie(video_data, verbinding):
#     """
#     Insert video dimension data into the database
#
#     Args:
#         video_data (tuple): Tuple containing video metadata (video_id, title, upload_date, views, comments, likes, duration)
#         verbinding: Database connection
#
#     Returns:
#         None
#     """
#     try:
#         video_id, titel, upload_datum, _, _, _, duur_in_seconden = video_data
#         query = """
#             INSERT INTO video (video_id, titel, uploaddatum, categorie, duur_in_seconden)
#             VALUES (%s, %s, %s, %s, %s)
#             ON CONFLICT (video_id) DO UPDATE SET titel = EXCLUDED.titel, uploaddatum = EXCLUDED.uploaddatum, duur_in_seconden = EXCLUDED.duur_in_seconden;
#         """
#         with verbinding.cursor() as cursor:
#             cursor.execute(query, (video_id, titel, upload_datum, 'Unknown', duur_in_seconden))
#             verbinding.commit()
#             logging.info(f"Video dimensie ingevoegd voor video ID {video_id}")
#     except Exception as e:
#         logging.error(f"Fout bij het invoegen van video dimensie: {e}")
#         verbinding.rollback()
#
# def insert_tijd_dimensie(upload_datum, verbinding):
#     """
#     Insert time dimension data into the database
#
#     Args:
#         upload_datum (str): Upload date in format 'YYYY-MM-DD'
#         verbinding: Database connection
#
#     Returns:
#         int: tijd_id of the inserted or existing time dimension
#     """
#     try:
#         upload_datum_gestript = datetime.strptime(upload_datum, '%Y-%m-%d')
#         dag = upload_datum_gestript.strftime('%A')  # Get day name (e.g., 'Monday')
#         maand, jaar = upload_datum_gestript.month, upload_datum_gestript.year
#
#         query = """
#             INSERT INTO tijd (dag, maand, jaar)
#             VALUES (%s, %s, %s)
#             ON CONFLICT (dag, maand, jaar) DO NOTHING
#             RETURNING tijd_id;
#         """
#
#         with verbinding.cursor() as cursor:
#             cursor.execute(query, (dag, maand, jaar))
#             tijd_id = cursor.fetchone()[0] if cursor.rowcount > 0 else krijg_bestaande_tijd_id(cursor, dag, maand, jaar)
#             verbinding.commit()
#             return tijd_id
#
#     except Exception as e:
#         logging.error(f"Fout bij het invoegen van tijd dimensie: {e}")
#         return None
#
# def krijg_bestaande_tijd_id(cursor, dag, maand, jaar):
#     """
#     Get the existing tijd_id for a given day, month, and year
#
#     Args:
#         cursor: Database cursor
#         dag (str): Day name
#         maand (int): Month number
#         jaar (int): Year
#
#     Returns:
#         int: tijd_id of the existing time dimension
#     """
#     query = """
#         SELECT tijd_id FROM tijd WHERE dag = %s AND maand = %s AND jaar = %s;
#         """
#     cursor.execute(query, (dag, maand, jaar))
#
#     return cursor.fetchone()[0]
#
# def insert_transcript(video_id, transcript, verbinding):
#     """
#     Insert or update transcript data in the database
#
#     Args:
#         video_id (str): YouTube video ID
#         transcript (str): Cleaned transcript text
#         verbinding: Database connection
#
#     Returns:
#         None
#     """
#     try:
#         query_check = "SELECT transcript_id FROM public.transcript WHERE video_id = %s;"
#
#         with verbinding.cursor() as cursor:
#             cursor.execute(query_check, (video_id,))
#             result = cursor.fetchone()
#
#             if result:
#                 transcript_id = result[0]
#                 query_update = "UPDATE public.transcript SET transcript = %s WHERE transcript_id = %s;"
#                 cursor.execute(query_update, (transcript, transcript_id))
#                 logging.info(f"Transcript bijgewerkt voor video ID: {video_id}")
#             else:
#                 query_insert = "INSERT INTO public.transcript (video_id, transcript) VALUES (%s, %s) RETURNING transcript_id;"
#                 cursor.execute(query_insert, (video_id, transcript))
#                 new_transcript_id = cursor.fetchone()[0]
#                 logging.info(f"Nieuw transcript toegevoegd voor video ID: {video_id} met transcript ID: {new_transcript_id}")
#
#             verbinding.commit()
#     except Exception as e:
#         logging.error(f"Fout bij het bijwerken of invoegen van transcript voor video ID {video_id}: {e}")
#         verbinding.rollback()
#
# def insert_populariteit(video_data, tijd_id, verbinding):
#     """
#     Insert popularity data into the database
#
#     Args:
#         video_data (tuple): Tuple containing video metadata (video_id, title, upload_date, views, comments, likes, duration)
#         tijd_id (int): tijd_id of the time dimension
#         verbinding: Database connection
#
#     Returns:
#         None
#     """
#     try:
#         video_id, _, _, views, comments, likes, _ = video_data
#         query = """
#             INSERT INTO populariteit (video_id, tijd_id, aantal_views, aantal_reacties, aantal_likes)
#             VALUES (%s, %s, %s, %s, %s);
#         """
#         with verbinding.cursor() as cursor:
#             cursor.execute(query, (video_id, tijd_id, views, comments, likes))
#             verbinding.commit()
#             logging.info(f"Populariteit dimensie ingevoegd voor video ID {video_id}")
#     except Exception as e:
#         logging.error(f"Fout bij het invoegen van populariteit dimensie: {e}")
#         verbinding.rollback()
#
# def update_label_in_db(video_id, label, verbinding=None):
#     """
#     Update the popularity label for a video in the database
#
#     Args:
#         video_id (str): YouTube video ID
#         label (str): Popularity label ('populair' or 'niet populair')
#         verbinding: Database connection (optional, will create a new connection if None)
#
#     Returns:
#         None
#     """
#     close_connection = False
#     try:
#         if verbinding is None:
#             verbinding = connect_to_database()
#             close_connection = True
#
#         if verbinding:
#             with verbinding.cursor() as cursor:
#                 update_query = """
#                 UPDATE video
#                 SET populariteit = %s
#                 WHERE video_id = %s
#                 """
#                 cursor.execute(update_query, (label, video_id))
#                 verbinding.commit()
#                 logging.info(f"Label voor video ID {video_id} bijgewerkt naar: {label}")
#     except Exception as e:
#         logging.error(f"Fout bij het bijwerken van label voor video ID {video_id}: {e}")
#         if verbinding:
#             verbinding.rollback()
#     finally:
#         if close_connection and verbinding:
#             verbinding.close()


def setup_new_database_schema(verbinding=None):
    """
    Set up the new database schema with dimension and fact tables

    Args:
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
                # Create dimension tables
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS Dim_Video (
                    video_key SERIAL PRIMARY KEY,
                    video_id VARCHAR(255) UNIQUE,
                    titel VARCHAR(255),
                    duur_in_seconden INTEGER,
                    transcript TEXT DEFAULT 'Unknown'
                );
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS Dim_Tijd (
                    tijd_key SERIAL PRIMARY KEY,
                    published_at TIMESTAMP,
                    jaar INT,
                    maand INT,
                    dag INT,
                    dag_van_week INT
                );
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS Dim_Categorie (
                    categorie_key SERIAL PRIMARY KEY,
                    category_id INT UNIQUE,
                    category_name VARCHAR(50)
                );
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS Dim_Tags (
                    tag_key SERIAL PRIMARY KEY,
                    video_key INT REFERENCES Dim_Video(video_key),
                    tag VARCHAR(100)
                );
                """)

                # Create fact table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS Feit_VideoPopulariteit (
                    video_key INT REFERENCES Dim_Video(video_key),
                    tijd_key INT REFERENCES Dim_Tijd(tijd_key),
                    categorie_key INT REFERENCES Dim_Categorie(categorie_key),
                    views INT,
                    likes INT,
                    comment_count INT,
                    views_per_day FLOAT,
                    engagement_ratio FLOAT DEFAULT 0.0,
                    is_populair BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (video_key, tijd_key)
                );
                """)

                verbinding.commit()
                logging.info("Nieuwe database schema succesvol opgezet")
    except Exception as e:
        logging.error(f"Fout bij het opzetten van het nieuwe database schema: {e}")
        if verbinding:
            verbinding.rollback()
    finally:
        if close_connection and verbinding:
            verbinding.close()


def insert_video_to_new_schema(video_data, verbinding):
    """
    Insert video data into the Dim_Video table

    Args:
        video_data (tuple): Tuple containing video metadata (video_id, title, upload_date, views, comments, likes, duration)
        verbinding: Database connection

    Returns:
        int: The video_key of the inserted video
    """
    try:
        video_id, titel, _, _, _, _, duur_in_seconden = video_data

        query = """
            INSERT INTO Dim_Video (video_id, titel, duur_in_seconden)
            VALUES (%s, %s, %s)
            ON CONFLICT (video_id) DO UPDATE 
            SET titel = EXCLUDED.titel, 
                duur_in_seconden = EXCLUDED.duur_in_seconden
            RETURNING video_key;
        """

        with verbinding.cursor() as cursor:
            cursor.execute(query, (video_id, titel, duur_in_seconden))
            video_key = cursor.fetchone()[0]
            verbinding.commit()
            logging.info(f"Video data ingevoegd in Dim_Video voor video ID {video_id}")
            return video_key

    except Exception as e:
        logging.error(f"Fout bij het invoegen van video data in Dim_Video: {e}")
        verbinding.rollback()
        return None


def insert_tijd_to_new_schema(upload_datum, verbinding):
    """
    Insert time data into the Dim_Tijd table

    Args:
        upload_datum (str): Upload date in format 'YYYY-MM-DD'
        verbinding: Database connection

    Returns:
        int: The tijd_key of the inserted time dimension
    """
    try:
        upload_datum_gestript = datetime.strptime(upload_datum, '%Y-%m-%d')
        dag = upload_datum_gestript.day
        dag_van_week = upload_datum_gestript.weekday() + 1  # 1 = Monday, 7 = Sunday
        maand = upload_datum_gestript.month
        jaar = upload_datum_gestript.year

        query = """
            INSERT INTO Dim_Tijd (published_at, jaar, maand, dag, dag_van_week)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING tijd_key;
        """

        with verbinding.cursor() as cursor:
            cursor.execute(query, (upload_datum_gestript, jaar, maand, dag, dag_van_week))
            tijd_key = cursor.fetchone()[0]
            verbinding.commit()
            logging.info(f"Tijd data ingevoegd in Dim_Tijd voor datum {upload_datum}")
            return tijd_key

    except Exception as e:
        logging.error(f"Fout bij het invoegen van tijd data in Dim_Tijd: {e}")
        verbinding.rollback()
        return None


def insert_categorie_to_new_schema(category_id, category_name, verbinding):
    """
    Insert category data into the Dim_Categorie table

    Args:
        category_id (int): Category ID
        category_name (str): Category name
        verbinding: Database connection

    Returns:
        int: The categorie_key of the inserted category
    """
    try:
        # First check if the category already exists
        check_query = """
            SELECT categorie_key FROM Dim_Categorie 
            WHERE category_id = %s;
        """

        with verbinding.cursor() as cursor:
            cursor.execute(check_query, (category_id,))
            result = cursor.fetchone()

            if result:
                # Category exists, update it
                update_query = """
                    UPDATE Dim_Categorie 
                    SET category_name = %s 
                    WHERE category_id = %s
                    RETURNING categorie_key;
                """
                cursor.execute(update_query, (category_name, category_id))
                categorie_key = cursor.fetchone()[0]
            else:
                # Category doesn't exist, insert it
                insert_query = """
                    INSERT INTO Dim_Categorie (category_id, category_name)
                    VALUES (%s, %s)
                    RETURNING categorie_key;
                """
                cursor.execute(insert_query, (category_id, category_name))
                categorie_key = cursor.fetchone()[0]

            verbinding.commit()
            logging.info(f"Categorie data ingevoegd/bijgewerkt in Dim_Categorie voor categorie {category_name}")
            return categorie_key

    except Exception as e:
        logging.error(f"Fout bij het invoegen van categorie data in Dim_Categorie: {e}")
        verbinding.rollback()
        return None


def insert_tags_to_new_schema(video_key, tags, verbinding):
    """
    Insert tags into the Dim_Tags table

    Args:
        video_key (int): The video_key from Dim_Video
        tags (list): List of tags for the video
        verbinding: Database connection

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not tags:
            logging.info(f"No tags to insert for video_key {video_key}")
            return True

        with verbinding.cursor() as cursor:
            # First delete any existing tags for this video
            delete_query = """
                DELETE FROM Dim_Tags 
                WHERE video_key = %s;
            """
            cursor.execute(delete_query, (video_key,))

            # Insert each tag
            for tag in tags:
                insert_query = """
                    INSERT INTO Dim_Tags (video_key, tag)
                    VALUES (%s, %s);
                """
                cursor.execute(insert_query, (video_key, tag))

            verbinding.commit()
            logging.info(f"Successfully inserted {len(tags)} tags for video_key {video_key}")
            return True

    except Exception as e:
        logging.error(f"Error inserting tags for video_key {video_key}: {e}")
        verbinding.rollback()
        return False


def insert_populariteit_to_new_schema(video_data, video_key, tijd_key, categorie_key, verbinding):
    """
    Insert popularity data into the Feit_VideoPopulariteit table

    Args:
        video_data (tuple): Tuple containing video metadata (video_id, title, upload_date, views, comments, likes, duration)
        video_key (int): The video_key from Dim_Video
        tijd_key (int): The tijd_key from Dim_Tijd
        categorie_key (int): The categorie_key from Dim_Categorie
        verbinding: Database connection

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Unpack only the elements we need, ignoring category_id and tags at the end
        _, _, upload_datum, views, comments, likes, *_ = video_data

        # Calculate views per day
        upload_date = datetime.strptime(upload_datum, '%Y-%m-%d')
        days_since_upload = (datetime.now() - upload_date).days
        views_per_day = views / max(days_since_upload, 1)  # Avoid division by zero

        # Calculate engagement ratio
        engagement_ratio = (likes + comments) / max(views, 1)  # Avoid division by zero

        # Determine if video is popular (simple threshold, can be adjusted)
        is_populair = views_per_day > 1000 or engagement_ratio > 0.1

        query = """
            INSERT INTO Feit_VideoPopulariteit 
            (video_key, tijd_key, categorie_key, views, likes, comment_count, views_per_day, engagement_ratio, is_populair)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (video_key, tijd_key) DO UPDATE 
            SET views = EXCLUDED.views,
                likes = EXCLUDED.likes,
                comment_count = EXCLUDED.comment_count,
                views_per_day = EXCLUDED.views_per_day,
                engagement_ratio = EXCLUDED.engagement_ratio,
                is_populair = EXCLUDED.is_populair;
        """

        with verbinding.cursor() as cursor:
            cursor.execute(query, (
                video_key, tijd_key, categorie_key, views, likes, comments, 
                views_per_day, engagement_ratio, is_populair
            ))
            verbinding.commit()
            logging.info(f"Populariteit data ingevoegd in Feit_VideoPopulariteit voor video_key {video_key}")
            return True

    except Exception as e:
        logging.error(f"Fout bij het invoegen van populariteit data in Feit_VideoPopulariteit: {e}")
        verbinding.rollback()
        return False
