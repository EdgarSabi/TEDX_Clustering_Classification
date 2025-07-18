import logging
import psycopg2
from datetime import datetime

from clusteranalysis import predict_cluster_label
from classification import predict_transcript_popularity
from setup_connections import connect_to_database


def update_column_names(verbinding=None):
    close_connection = False
    try:
        if verbinding is None:
            verbinding = connect_to_database()
            close_connection = True

        if verbinding:
            with verbinding.cursor() as cursor:
                # Check if transcript_positive column exists in Dim_Video
                cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'dim_video' AND column_name = 'transcript_positive';
                """)
                
                if cursor.fetchone():
                    # Rename transcript_positive to sentiment
                    cursor.execute("""
                    ALTER TABLE Dim_Video 
                    RENAME COLUMN transcript_positive TO sentiment;
                    """)
                    logging.info("Column 'transcript_positive' renamed to 'sentiment' in Dim_Video")
                else:
                    # Check if sentiment column exists
                    cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'dim_video' AND column_name = 'sentiment';
                    """)
                    
                    if not cursor.fetchone():
                        # Add sentiment column if it doesn't exist
                        cursor.execute("""
                        ALTER TABLE Dim_Video 
                        ADD COLUMN sentiment BOOLEAN;
                        """)
                        logging.info("Column 'sentiment' added to Dim_Video")

                # Check if is_populair column exists in Feit_VideoPopulariteit
                cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'feit_videopopulariteit' AND column_name = 'is_populair';
                """)
                
                if cursor.fetchone():
                    # Rename is_populair to rating
                    cursor.execute("""
                    ALTER TABLE Feit_VideoPopulariteit 
                    RENAME COLUMN is_populair TO rating;
                    """)
                    logging.info("Column 'is_populair' renamed to 'rating' in Feit_VideoPopulariteit")
                else:
                    # Check if rating column exists
                    cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'feit_videopopulariteit' AND column_name = 'rating';
                    """)
                    
                    if not cursor.fetchone():
                        # Add rating column if it doesn't exist
                        cursor.execute("""
                        ALTER TABLE Feit_VideoPopulariteit 
                        ADD COLUMN rating BOOLEAN;
                        """)
                        logging.info("Column 'rating' added to Feit_VideoPopulariteit")

                verbinding.commit()
                logging.info("Database schema updated successfully")
    except Exception as e:
        logging.error(f"Error updating database schema: {e}")
        if verbinding:
            verbinding.rollback()
    finally:
        if close_connection and verbinding:
            verbinding.close()

def setup_new_database_schema(verbinding=None):
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
                    transcript TEXT,
                    sentiment BOOLEAN
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
                    views_relative_to_category FLOAT,
                    comment_like_ratio FLOAT,
                    rating BOOLEAN,
                    PRIMARY KEY (video_key, tijd_key)
                );
                """)

                verbinding.commit()
                logging.info("Nieuwe database schema succesvol opgezet")
                
            # Update column names in existing tables
            update_column_names(verbinding)
    except Exception as e:
        logging.error(f"Fout bij het opzetten van het nieuwe database schema: {e}")
        if verbinding:
            verbinding.rollback()
    finally:
        if close_connection and verbinding:
            verbinding.close()


def insert_video_to_new_schema(video_data, verbinding):
    """
    Insert video data into the Dim_Video table or update existing record
    
    For existing records, only title and duration are updated, transcript is kept unchanged.

    Args:
        video_data (tuple): Tuple containing video metadata (video_id, title, upload_date, views, comments, likes, duration, category_id, tags, transcription)
        verbinding: Database connection

    Returns:
        int: The video_key of the inserted or updated video
    """
    try:
        video_id, titel, _, _, _, _, duur_in_seconden, _, _, transcription = video_data

        # First check if the video already exists
        check_query = """
            SELECT video_key, transcript FROM Dim_Video 
            WHERE video_id = %s;
        """
        
        with verbinding.cursor() as cursor:
            cursor.execute(check_query, (video_id,))
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Video exists, update title and duration but keep transcript unchanged
                video_key, existing_transcript = existing_record
                
                # Classify the existing transcript if it exists
                sentiment = None
                if existing_transcript:
                    prediction = predict_transcript_popularity(existing_transcript)
                    if prediction:
                        sentiment = prediction['is_popular']
                
                update_query = """
                    UPDATE Dim_Video 
                    SET titel = %s, 
                        duur_in_seconden = %s,
                        sentiment = %s
                    WHERE video_key = %s
                    RETURNING video_key;
                """
                cursor.execute(update_query, (titel, duur_in_seconden, sentiment, video_key))
                video_key = cursor.fetchone()[0]
                logging.info(f"Video data bijgewerkt in Dim_Video voor video ID {video_id} (transcript ongewijzigd)")
            else:
                # Video doesn't exist, insert new record with transcript
                
                # Classify the transcript if it exists
                sentiment = None
                if transcription:
                    prediction = predict_transcript_popularity(transcription)
                    if prediction:
                        sentiment = prediction['is_popular']
                
                insert_query = """
                    INSERT INTO Dim_Video (video_id, titel, duur_in_seconden, transcript, sentiment)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING video_key;
                """
                cursor.execute(insert_query, (video_id, titel, duur_in_seconden, transcription, sentiment))
                video_key = cursor.fetchone()[0]
                logging.info(f"Nieuwe video data ingevoegd in Dim_Video voor video ID {video_id}")
            
            verbinding.commit()
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




def insert_populariteit_to_new_schema(video_data, video_key, tijd_key, categorie_key, connection):
    try:
        with connection.cursor() as cursor:
            # Bereken de features
            views = video_data[3]
            likes = video_data[5]
            comments = video_data[4]
            upload_date = datetime.strptime(video_data[2], '%Y-%m-%d')
            days_since_upload = max((datetime.now() - upload_date).days, 1)

            views_per_day = views / days_since_upload
            engagement_ratio = (likes + comments) / max(views, 1)

            # Haal categorie gemiddelde op met de juiste join
            cursor.execute("""
                           SELECT AVG(fp.views)
                           FROM Feit_VideoPopulariteit fp
                           WHERE fp.categorie_key = %s
                           """, (categorie_key,))
            result = cursor.fetchone()
            category_avg_views = result[0] if result and result[0] is not None else views
            views_relative_to_category = views / category_avg_views

            comment_like_ratio = comments / max(likes, 1)

            # Voorspel rating met opgeslagen model
            rating = predict_cluster_label(video_data)
            if rating is None:
                rating = False  # default waarde

            # Log the calculated values
            logging.info(f"Calculated values for video_key {video_key}:")
            logging.info(f"views: {views}")
            logging.info(f"likes: {likes}")
            logging.info(f"comments: {comments}")
            logging.info(f"views_per_day: {views_per_day}")
            logging.info(f"engagement_ratio: {engagement_ratio}")
            logging.info(f"views_relative_to_category: {views_relative_to_category}")
            logging.info(f"comment_like_ratio: {comment_like_ratio}")
            logging.info(f"rating: {rating}")

            # Insert query met alle features en rating
            insert_query = """
                           INSERT INTO Feit_VideoPopulariteit (video_key, tijd_key, categorie_key, \
                                                               views, likes, comment_count, \
                                                               views_per_day, engagement_ratio, \
                                                               views_relative_to_category, comment_like_ratio, \
                                                               rating) \
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
                           """
            
            # Print the values being passed to the query
            print(f"\nInserting popularity data for video_key {video_key}:")
            print(f"views: {views}")
            print(f"likes: {likes}")
            print(f"comments: {comments}")
            print(f"views_per_day: {views_per_day}")
            print(f"engagement_ratio: {engagement_ratio}")
            print(f"views_relative_to_category: {views_relative_to_category}")
            print(f"comment_like_ratio: {comment_like_ratio}")
            print(f"rating: {rating}")
            
            cursor.execute(insert_query, (
                video_key, tijd_key, categorie_key,
                views, likes, comments,
                views_per_day, engagement_ratio,
                views_relative_to_category, comment_like_ratio,
                rating
            ))

            # Verify the insertion by querying the database
            verify_query = """
                          SELECT views_relative_to_category, comment_like_ratio, rating
                          FROM Feit_VideoPopulariteit
                          WHERE video_key = %s AND tijd_key = %s
                          """
            cursor.execute(verify_query, (video_key, tijd_key))
            result = cursor.fetchone()
            
            if result:
                db_views_relative_to_category, db_comment_like_ratio, db_rating = result
                logging.info(f"Verified values in database:")
                logging.info(f"views_relative_to_category: {db_views_relative_to_category}")
                logging.info(f"comment_like_ratio: {db_comment_like_ratio}")
                logging.info(f"rating: {db_rating}")
                
                print(f"\nVerified values in database:")
                print(f"views_relative_to_category: {db_views_relative_to_category}")
                print(f"comment_like_ratio: {db_comment_like_ratio}")
                print(f"rating: {db_rating}")
            else:
                logging.warning(f"Could not verify insertion - no data found for video_key {video_key} and tijd_key {tijd_key}")
                print(f"\nWARNING: Could not verify insertion - no data found for video_key {video_key} and tijd_key {tijd_key}")

            connection.commit()
            logging.info(f"Successfully inserted popularity data for video_key {video_key}")
            print(f"\nSuccessfully inserted popularity data for video_key {video_key}")
            return True

    except Exception as e:
        connection.rollback()
        logging.error(f"Error inserting popularity data: {e}")
        print(f"\nERROR: Error inserting popularity data: {e}")
        return False