import psycopg2.errors
from user_personal_data.connections import password, database, user


def drop_tables():
    with psycopg2.connect(database=database, user=user, password=password) as conn:  # Здесь хранится инфорбация о базе данных
        with conn.cursor() as cur:
            try:
                cur.execute('''
                    DROP TABLE words;
                    DROP TABLE random_words;
                ''')
            except psycopg2.errors.UndefinedTable:
                print('Mistake')
    conn.close()


def create_tables():
    with psycopg2.connect(database=database, user=user, password=password) as conn:  # Здесь хранится инфорбация о базе данных
        with conn.cursor() as cur:
            drop_tables()

            cur.execute('''
                        CREATE TABLE IF NOT EXISTS words (
                            id SERIAL PRIMARY KEY,
                            question_word VARCHAR (40),
                            answer_word VARCHAR (30),
                            user_id BIGINT
                        );
                        CREATE TABLE IF NOT EXISTS random_words(
                            id SERIAL PRIMARY KEY,
                            word VARCHAR(20)
                         );
                    ''')
            conn.commit()
            cur.execute("""    
                        INSERT INTO random_words (word) 
                        VALUES ('cave'),
                        ('worm'),
                        ('advance'),
                        ('wage'),
                        ('note'),
                        ('please'),
                        ('month'),
                        ('mouth'),
                        ('lower'),
                        ('lawyer'),
                        ('layer'),
                        ('wider'),
                        ('game'),
                        ('eye'),
                        ('now');
                    """)
            conn.commit()
