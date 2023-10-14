import psycopg2


def connect_to_db(db_params):
    conn = psycopg2.connect(**db_params)
    return conn


def close_db(conn):
    conn.close()


def create_table(conn, cursor, name):
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {name} (
        id SERIAL PRIMARY KEY,
        url TEXT,
        title TEXT,
        price_usd TEXT,
        odometer INT,
        username TEXT,
        phone_number TEXT,
        image_url TEXT,
        images_count INT,
        car_number TEXT,
        car_vin TEXT,
        datetime_found TIMESTAMP
    );
    """)
    conn.commit()


def insert_into_db(conn, cursor, db_name, data):
    cursor.execute(f"""
                INSERT INTO {db_name} (
                url,
                title,
                price_usd, 
                odometer,
                username,
                phone_number,
                image_url,
                images_count,
                car_number,
                car_vin,
                datetime_found
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [*data])
    conn.commit()
