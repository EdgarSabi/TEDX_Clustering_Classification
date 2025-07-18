import logging
import psycopg2
from datetime import datetime

from clusteranalysis import predict_cluster_label
from classification import predict_sentiment
from setup_connections import connect_to_database

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
                CREATE TABLE Dim_Video (
                    video_key SERIAL PRIMARY KEY,
                    video_id VARCHAR(255) UNIQUE,
                    titel VARCHAR(255),
                    duur_in_seconden INTEGER,
                    transcript TEXT,
                    views INT,           -- verplaatst van Feit_VideoPopulariteit
                    likes INT,           -- verplaatst van Feit_VideoPopulariteit
                    comment_count INT    -- verplaatst van Feit_VideoPopulariteit
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
                CREATE TABLE Feit_VideoPopulariteit (
                    video_key INT REFERENCES Dim_Video(video_key),
                    tijd_key INT REFERENCES Dim_Tijd(tijd_key),
                    categorie_key INT REFERENCES Dim_Categorie(categorie_key),
                    views_per_day FLOAT,
                    engagement_ratio FLOAT DEFAULT 0.0,
                    views_relative_to_category FLOAT,
                    comment_like_ratio FLOAT,
                    sentiment VARCHAR(15),    -- verplaatst van Dim_Video
                    rating VARCHAR(25),       -- populariteitsvoorspelling
                    views_growth_rate FLOAT DEFAULT 0.0,  -- groei in views per dag
                    likes_growth_rate FLOAT DEFAULT 0.0,  -- groei in likes per dag
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- laatste update tijdstip
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
    Insert video data into the Dim_Video table or update existing record
    
    For existing records, only title and duration are updated, transcript is kept unchanged.

    Args:
        video_data (tuple): Tuple containing video metadata (video_id, title, upload_date, views, comments, likes, duration, category_id, transcription)
        verbinding: Database connection

    Returns:
        int: The video_key of the inserted or updated video
    """
    try:
        video_id, titel, _, views, comments, likes, duur_in_seconden, _, transcription = video_data

        # First check if the video already exists
        check_query = """
            SELECT video_key, transcript FROM Dim_Video 
            WHERE video_id = %s;
        """
        
        with verbinding.cursor() as cursor:
            cursor.execute(check_query, (video_id,))
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Video exists, update title, duration, views, likes, and comments but keep transcript unchanged
                video_key, existing_transcript = existing_record
                
                update_query = """
                    UPDATE Dim_Video 
                    SET titel = %s, 
                        duur_in_seconden = %s,
                        views = %s,
                        likes = %s,
                        comment_count = %s
                    WHERE video_key = %s
                    RETURNING video_key;
                """
                cursor.execute(update_query, (titel, duur_in_seconden, views, likes, comments, video_key))
                video_key = cursor.fetchone()[0]
                logging.info(f"Video data bijgewerkt in Dim_Video voor video ID {video_id} (transcript ongewijzigd)")
            else:
                # Video doesn't exist, insert new record with transcript
                
                insert_query = """
                    INSERT INTO Dim_Video (video_id, titel, duur_in_seconden, transcript, views, likes, comment_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING video_key;
                """
                cursor.execute(insert_query, (video_id, titel, duur_in_seconden, transcription, views, likes, comments))
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
    Insert time data into the Dim_Tijd table or return existing tijd_key if the date already exists

    Args:
        upload_datum (str): Upload date in format 'YYYY-MM-DD'
        verbinding: Database connection

    Returns:
        int: The tijd_key of the inserted or existing time dimension
    """
    try:
        upload_datum_gestript = datetime.strptime(upload_datum, '%Y-%m-%d')
        dag = upload_datum_gestript.day
        dag_van_week = upload_datum_gestript.weekday() + 1  # 1 = Monday, 7 = Sunday
        maand = upload_datum_gestript.month
        jaar = upload_datum_gestript.year

        # First check if the date already exists
        check_query = """
            SELECT tijd_key FROM Dim_Tijd 
            WHERE jaar = %s AND maand = %s AND dag = %s;
        """

        with verbinding.cursor() as cursor:
            cursor.execute(check_query, (jaar, maand, dag))
            result = cursor.fetchone()

            if result:
                # Date exists, return existing tijd_key
                tijd_key = result[0]
                logging.info(f"Bestaande tijd data gevonden in Dim_Tijd voor datum {upload_datum}")
            else:
                # Date doesn't exist, insert it
                insert_query = """
                    INSERT INTO Dim_Tijd (published_at, jaar, maand, dag, dag_van_week)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING tijd_key;
                """
                cursor.execute(insert_query, (upload_datum_gestript, jaar, maand, dag, dag_van_week))
                tijd_key = cursor.fetchone()[0]
                logging.info(f"Nieuwe tijd data ingevoegd in Dim_Tijd voor datum {upload_datum}")
            
            verbinding.commit()
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
            transcription = video_data[8]

            views_per_day = views / days_since_upload
            engagement_ratio = (likes + comments) / max(views, 1)

            # Combine queries to get category average and previous metrics in one go
            cursor.execute("""
                WITH category_avg AS (
                    SELECT AVG(v.views) as avg_views
                    FROM Dim_Video v
                    JOIN Feit_VideoPopulariteit fp ON v.video_key = fp.video_key
                    WHERE fp.categorie_key = %s
                ),
                prev_metrics AS (
                    SELECT fp.views_per_day, dv.views, dv.likes, fp.last_update 
                    FROM Feit_VideoPopulariteit fp
                    JOIN Dim_Video dv ON fp.video_key = dv.video_key
                    WHERE fp.video_key = %s 
                    ORDER BY fp.last_update DESC 
                    LIMIT 1
                )
                SELECT 
                    category_avg.avg_views,
                    prev_metrics.views_per_day,
                    prev_metrics.views,
                    prev_metrics.likes,
                    prev_metrics.last_update
                FROM 
                    (SELECT NULL) dummy
                LEFT JOIN category_avg ON true
                LEFT JOIN prev_metrics ON true
            """, (categorie_key, video_key))
            
            result = cursor.fetchone()
            
            # Extract category average views
            category_avg_views = result[0] if result and result[0] is not None else views
            views_relative_to_category = views / category_avg_views
            
            comment_like_ratio = comments / max(likes, 1)

            # Voorspel rating met opgeslagen model
            cluster_result = predict_cluster_label(video_data)
            if cluster_result is None:
                rating = 'niet populair'  # default waarde
            else:
                # Use the string value directly
                rating = cluster_result['popularity_label']
                
            # Predict sentiment if transcription exists
            sentiment = None
            if transcription:
                prediction = predict_sentiment(transcription)
                if prediction:
                    sentiment = prediction['sentiment_label']

            # Log the calculated values
            logging.info(f"Calculated values for video_key {video_key}: "
                         f"views_per_day={views_per_day:.2f}, engagement_ratio={engagement_ratio:.4f}, "
                         f"views_relative_to_category={views_relative_to_category:.2f}, "
                         f"comment_like_ratio={comment_like_ratio:.2f}, rating={rating}, sentiment={sentiment}")

            # Extract previous metrics from the combined query result
            previous_record = None
            if result and result[1] is not None:  # If we have previous metrics
                previous_record = result[1:]  # views_per_day, views, likes, last_update

            # Bereken groei rates
            current_time = datetime.now()
            views_growth_rate = 0
            likes_growth_rate = 0

            if previous_record:
                prev_views_per_day, prev_views, prev_likes, prev_update = previous_record
                days_since_update = max((current_time - prev_update).total_seconds() / 86400, 1)  # 86400 seconden in een dag
                
                # Bereken dagelijkse groei rates
                views_growth_rate = max(0, (views_per_day - prev_views_per_day) / days_since_update)
                likes_growth_rate = max(0, (likes - prev_likes) / days_since_update)
                
                logging.info(f"Growth rates calculated - Views per day: {views_growth_rate:.2f}/day, Likes: {likes_growth_rate:.2f}/day")

            # Check of er een bestaande rij is
            cursor.execute("""
                SELECT tijd_key FROM Feit_VideoPopulariteit 
                WHERE video_key = %s
            """, (video_key,))
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Update bestaande rij
                update_query = """
                    UPDATE Feit_VideoPopulariteit 
                    SET tijd_key = %s,
                        categorie_key = %s,
                        views_per_day = %s, 
                        engagement_ratio = %s, 
                        views_relative_to_category = %s, 
                        comment_like_ratio = %s, 
                        sentiment = %s,
                        rating = %s,
                        views_growth_rate = %s,
                        likes_growth_rate = %s,
                        last_update = %s
                    WHERE video_key = %s
                """
                cursor.execute(update_query, (
                    tijd_key, categorie_key,
                    views_per_day, engagement_ratio,
                    views_relative_to_category, comment_like_ratio,
                    sentiment, rating,
                    views_growth_rate, likes_growth_rate,
                    current_time, video_key
                ))
                logging.info(f"Updated popularity data for video_key {video_key}")
            else:
                # Voeg nieuwe rij toe
                insert_query = """
                    INSERT INTO Feit_VideoPopulariteit (
                        video_key, tijd_key, categorie_key, 
                        views_per_day, engagement_ratio, 
                        views_relative_to_category, comment_like_ratio, 
                        sentiment, rating,
                        views_growth_rate, likes_growth_rate,
                        last_update
                    ) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    video_key, tijd_key, categorie_key,
                    views_per_day, engagement_ratio,
                    views_relative_to_category, comment_like_ratio,
                    sentiment, rating,
                    views_growth_rate, likes_growth_rate,
                    current_time
                ))
                logging.info(f"Inserted new popularity data for video_key {video_key}")

            connection.commit()
            logging.info(f"Successfully inserted popularity data for video_key {video_key}")
            return True

    except Exception as e:
        connection.rollback()
        logging.error(f"Error inserting popularity data: {e}")
        print(f"\nERROR: Error inserting popularity data: {e}")
        return False