import logging
from datetime import datetime
from clusteranalysis import predict_cluster_label
from classification import predict_sentiment
from setup_connections import connect_to_database

def setup_database_schema(verbinding=None):
    close_connection = False
    try:
        if verbinding is None:
            verbinding = connect_to_database()
            close_connection = True

        if verbinding:
            with verbinding.cursor() as cursor:
                cursor.execute("""
                CREATE TABLE Dim_Video (
                    video_key SERIAL PRIMARY KEY,
                    video_id VARCHAR(255) UNIQUE,
                    titel VARCHAR(255),
                    duur_in_seconden INTEGER,
                    transcript TEXT,
                    views INT,
                    likes INT,
                    comment_count INT
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
                    sentiment VARCHAR(15),
                    rating VARCHAR(25),
                    views_growth INT DEFAULT 0,
                    likes_growth INT DEFAULT 0,
                    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (video_key, tijd_key)
                );
                """)

                verbinding.commit()
                logging.info("Database succesvol opgezet")
    except Exception as e:
        logging.error(f"Fout bij het opzetten van het nieuwe database schema: {e}")
        if verbinding:
            verbinding.rollback()
    finally:
        if close_connection and verbinding:
            verbinding.close()


def insert_video_to_new_schema(video_data, verbinding):
    try:
        video_id, titel, _, views, comments, likes, duur_in_seconden, _, transcription, sentiment_result = video_data

        # First check if the video already exists
        check_query = """
            SELECT video_key, transcript FROM Dim_Video 
            WHERE video_id = %s;
        """
        
        with verbinding.cursor() as cursor:
            cursor.execute(check_query, (video_id,))
            existing_record = cursor.fetchone()
            
            if existing_record:
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
    try:
        upload_datum_gestript = datetime.strptime(upload_datum, '%Y-%m-%d')
        dag = upload_datum_gestript.day
        dag_van_week = upload_datum_gestript.weekday() + 1  # 1 = Monday, 7 = Sunday
        maand = upload_datum_gestript.month
        jaar = upload_datum_gestript.year

        check_query = """
            SELECT tijd_key FROM Dim_Tijd 
            WHERE jaar = %s AND maand = %s AND dag = %s;
        """

        with verbinding.cursor() as cursor:
            cursor.execute(check_query, (jaar, maand, dag))
            result = cursor.fetchone()

            if result:
                tijd_key = result[0]
                logging.info(f"Bestaande tijd data gevonden in Dim_Tijd voor datum {upload_datum}")
            else:
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
    try:
        check_query = """
            SELECT categorie_key FROM Dim_Categorie 
            WHERE category_id = %s;
        """

        with verbinding.cursor() as cursor:
            cursor.execute(check_query, (category_id,))
            result = cursor.fetchone()

            if result:
                update_query = """
                    UPDATE Dim_Categorie 
                    SET category_name = %s 
                    WHERE category_id = %s
                    RETURNING categorie_key;
                """
                cursor.execute(update_query, (category_name, category_id))
                categorie_key = cursor.fetchone()[0]
            else:
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


def insert_populariteit_to_new_schema(video_data, video_key, tijd_key, categorie_key, connection, prev_values=None):
    try:
        with connection.cursor() as cursor:
            current_views = float(video_data[3])
            current_likes = float(video_data[5])
            comments = float(video_data[4])

            upload_date = datetime.strptime(video_data[2], '%Y-%m-%d')
            days_since_upload = max((datetime.now() - upload_date).days, 1)
            views_per_day = current_views / days_since_upload
            engagement_ratio = (current_likes + comments) / max(current_views, 1)

            views_growth = 0
            likes_growth = 0

            if prev_values:
                prev_views, prev_likes = prev_values
                views_growth = max(0, int(current_views - float(prev_views)))
                likes_growth = max(0, int(current_likes - float(prev_likes)))
                logging.info(f"Growth calculation - Views: {current_views} - {prev_views} = {views_growth}")
                logging.info(f"Growth calculation - Likes: {current_likes} - {prev_likes} = {likes_growth}")
            else:
                logging.info("No previous values found, growth will be 0")


            cursor.execute("""
                SELECT AVG(views) 
                FROM Dim_Video v
                WHERE v.video_key IN (
                    SELECT DISTINCT fp.video_key
                    FROM Feit_VideoPopulariteit fp
                    WHERE fp.categorie_key = %s
                )
            """, (categorie_key,))
            
            category_avg_result = cursor.fetchone()
            category_avg_views = float(category_avg_result[0]) if category_avg_result and category_avg_result[0] else current_views
            views_relative_to_category = current_views / max(category_avg_views, 1)
            
            comment_like_ratio = comments / max(current_likes, 1)

            cluster_result = predict_cluster_label(video_data)
            rating = cluster_result['popularity_label'] if cluster_result else 'niet populair'

            transcription = video_data[8]
            sentiment_result = video_data[9] if len(video_data) > 9 else None

            sentiment = None
            if sentiment_result and isinstance(sentiment_result, dict) and 'sentiment_label' in sentiment_result:
                sentiment = sentiment_result['sentiment_label']
                logging.info(f"Using sentiment from video_data: {sentiment}")
            elif transcription and transcription != "CAPTION_SKIPPED":
                prediction = predict_sentiment(transcription)
                if prediction and 'sentiment_label' in prediction:
                    sentiment = prediction['sentiment_label']
                    logging.info(f"Calculated new sentiment in setup_database: {sentiment}")
                else:
                    logging.warning("Failed to calculate sentiment")
            else:
                logging.info("No transcript available for sentiment analysis")

            logging.info(f"Calculated values for video_key {video_key}: "
                         f"views_per_day={views_per_day:.2f}, "
                         f"engagement_ratio={engagement_ratio:.4f}, "
                         f"views_relative_to_category={views_relative_to_category:.2f}, "
                         f"comment_like_ratio={comment_like_ratio:.2f}, rating={rating}, sentiment={sentiment}" 
                         f"views_growth={views_growth:.2f}, likes_growth={likes_growth:.2f}")

            cursor.execute("""
                SELECT tijd_key FROM Feit_VideoPopulariteit 
                WHERE video_key = %s
            """, (video_key,))
            existing_record = cursor.fetchone()

            current_time = datetime.now()
            
            if existing_record:
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
                        views_growth = %s,
                        likes_growth = %s,
                        last_update = %s
                    WHERE video_key = %s
                """
                cursor.execute(update_query, (
                    tijd_key, categorie_key,
                    views_per_day, engagement_ratio,
                    views_relative_to_category, comment_like_ratio,
                    sentiment, rating,
                    views_growth, likes_growth,
                    current_time, video_key
                ))
                logging.info(f"Updated popularity data for video_key {video_key}")
            else:
                insert_query = """
                    INSERT INTO Feit_VideoPopulariteit (
                        video_key, tijd_key, categorie_key, 
                        views_per_day, engagement_ratio, 
                        views_relative_to_category, comment_like_ratio, 
                        sentiment, rating,
                        views_growth, likes_growth,
                        last_update
                    ) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    video_key, tijd_key, categorie_key,
                    views_per_day, engagement_ratio,
                    views_relative_to_category, comment_like_ratio,
                    sentiment, rating,
                    views_growth, likes_growth,
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