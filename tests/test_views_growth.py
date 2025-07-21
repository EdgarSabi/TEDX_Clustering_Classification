import logging
from datetime import datetime
from setup_connections import connect_to_database
from setup_database import (
    insert_video_to_new_schema,
    insert_tijd_to_new_schema,
    insert_categorie_to_new_schema,
    insert_populariteit_to_new_schema
)

logging.basicConfig(level=logging.INFO)


def create_test_video_data(views, likes, comments):
    return (
        "TEST_VIDEO_001",  # video_id
        "Test Video Title",  # titel
        "2024-01-01",  # upload_date
        views,  # views
        comments,  # comments
        likes,  # likes
        120,  # duur_in_seconden
        1,  # category_id
        "TEST_TRANSCRIPT",  # transcript
        {"sentiment_label": "positive"}  # sentiment_result
    )


def main():
    try:
        with connect_to_database() as connection:
            logging.info("Starting test scenario")

            # Stap 1: Initiële video met basis statistieken
            initial_views, initial_likes, initial_comments = 100, 10, 5
            video_data = create_test_video_data(initial_views, initial_likes, initial_comments)

            # Haal eerst prev_values (zou None moeten zijn voor nieuwe video)
            prev_values = None
            with connection.cursor() as cursor:
                cursor.execute("""
                               SELECT views, likes
                               FROM Dim_Video
                               WHERE video_id = %s
                               """, (video_data[0],))
                prev_values = cursor.fetchone()

            # Video invoegen
            video_key = insert_video_to_new_schema(video_data, connection)
            if not video_key:
                raise Exception("Failed to insert test video")

            # Tijd en categorie invoegen
            tijd_key = insert_tijd_to_new_schema(video_data[2], connection)
            categorie_key = insert_categorie_to_new_schema(video_data[7], "Test Category", connection)

            # Eerste populariteit record maken
            success = insert_populariteit_to_new_schema(
                video_data, video_key, tijd_key, categorie_key, connection, prev_values
            )
            logging.info(f"Initial video inserted - Views: {initial_views}, Likes: {initial_likes}")

            # Stap 2: Simuleer een update met hogere waarden
            updated_views, updated_likes, updated_comments = 150, 15, 8

            # Haal huidige waarden op als prev_values voor de update
            with connection.cursor() as cursor:
                cursor.execute("""
                               SELECT views, likes
                               FROM Dim_Video
                               WHERE video_id = %s
                               """, (video_data[0],))
                prev_values = cursor.fetchone()

            # Maak nieuwe video data met geüpdatete statistieken
            updated_video_data = create_test_video_data(updated_views, updated_likes, updated_comments)

            # Update de video en populariteit
            video_key = insert_video_to_new_schema(updated_video_data, connection)
            success = insert_populariteit_to_new_schema(
                updated_video_data, video_key, tijd_key, categorie_key, connection, prev_values
            )

            # Controleer de resultaten
            with connection.cursor() as cursor:
                cursor.execute("""
                               SELECT dv.video_id,
                                      dv.views,
                                      dv.likes,
                                      fp.views_growth,
                                      fp.likes_growth,
                                      fp.last_update
                               FROM Feit_VideoPopulariteit fp
                                        JOIN Dim_Video dv ON fp.video_key = dv.video_key
                               WHERE dv.video_id = 'TEST_VIDEO_001'
                               ORDER BY fp.last_update DESC LIMIT 1;
                               """)
                result = cursor.fetchone()

                if result:
                    video_id, views, likes, views_growth, likes_growth, last_update = result
                    logging.info("\nTest Results:")
                    logging.info(f"Video ID: {video_id}")
                    logging.info(f"Current Views: {views}, Current Likes: {likes}")
                    logging.info(f"Views Growth: {views_growth} (Expected: {updated_views - initial_views})")
                    logging.info(f"Likes Growth: {likes_growth} (Expected: {updated_likes - initial_likes})")
                    logging.info(f"Last Update: {last_update}")

                    # Verify if growth calculations are correct
                    assert views_growth == (updated_views - initial_views), "Views growth calculation incorrect"
                    assert likes_growth == (updated_likes - initial_likes), "Likes growth calculation incorrect"
                    logging.info("✅ All growth calculations are correct!")

            #Verwijder test data
            # with connection.cursor() as cursor:
            #     cursor.execute("DELETE FROM Feit_VideoPopulariteit WHERE video_key = %s", (video_key,))
            #     cursor.execute("DELETE FROM Dim_Video WHERE video_id = 'TEST_VIDEO_001'")
            #     connection.commit()

    except Exception as e:
        logging.error(f"Test failed: {e}")
        if connection:
            connection.rollback()
    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()