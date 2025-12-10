import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from flask import render_template, Flask, abort, g
import logging
import db
import sqlite3


APP = Flask(__name__)

# Start page (mudar as stats que qeuro que aparceçam aqui)
@APP.route('/')
def index():
    #ola
    stats = db.execute('''
        SELECT * FROM
        (SELECT COUNT(*) n_movies FROM shows)
        JOIN (SELECT COUNT(*) n_people FROM people)
        JOIN (SELECT COUNT(*) n_genres FROM genres)
        JOIN (SELECT COUNT(*) n_production_companies FROM companies)
                       ''').fetchone()
    logging.info(stats)
    return render_template('index.html',stats = stats)

# Filmes 
@APP.route('/shows/')
def list_movies():
    movies = db.execute('''
        SELECT show_id, title
        FROM shows 
        ORDER BY title
    ''').fetchall()
    return render_template('movie-list.html', movies=movies)

# Cada filme individual 
@APP.route('/shows/<int:id>/')
def get_movie(id):
    movie = db.execute('''
        SELECT show_id, title, releaseDate, rating, num_seasons, tagline, description, duration
        FROM shows
        WHERE show_id = ?
    ''', [id]).fetchone()

    if movie is None:
        abort(404, 'Show id {} não existe.'.format(id))

    # Obter géneros do filme
    genres = db.execute('''
        SELECT g.name
        FROM types 
        NATURAL JOIN genres g
        WHERE show_id = ?
        order by g.name
    ''', [id]).fetchall()

    # Obter atores do filme
    actors = db.execute('''
        SELECT name, person_id
        FROM top_cast 
        NATURAL JOIN people
        WHERE show_id = ?
    ''', [id]).fetchall()

    scores = db.execute('''
        SELECT metascore, userscore
        FROM metascore
        NATURAL JOIN userscore
        WHERE show_id = ?                  
    ''', [id]).fetchall()

    # Obter creators
    creators = db.execute('''
        SELECT name, person_id
        FROM creators
        NATURAL JOIN people
        WHERE show_id = ?
    ''', [id]).fetchall()

    # Obter writers
    writers = db.execute('''
        SELECT name, person_id
        FROM writers
        NATURAL JOIN people
        WHERE show_id = ?
    ''', [id]).fetchall()

    # Obter directors
    directors = db.execute('''
        SELECT name, person_id
        FROM directors
        NATURAL JOIN people
        WHERE show_id = ?
    ''', [id]).fetchall()

    # Obter production companies (producers)
    producers = db.execute('''
        SELECT name, producer_id
        FROM production
        NATURAL JOIN companies
        WHERE show_id = ?
    ''', [id]).fetchall()


    return render_template('movie.html',
                           movie = movie,
                           genres = genres,
                           actors = actors,
                           scores = scores,
                           creators = creators,
                           writers = writers,
                           directors = directors,
                           producers = producers)

# Genres
@APP.route('/genres/')
def list_genres():
    genres = db.execute('''
        SELECT genre_id, name
        FROM genres
        ORDER BY genre_id
    ''').fetchall()
    return render_template('genre-list.html', genres=genres)


# cada genre
@APP.route('/genres/<int:id>/')
def get_genre(id):
    info = db.execute('''
        SELECT name AS genre_name, COUNT(show_id) AS total
        FROM genres
        NATURAL JOIN types
        WHERE genre_id = ?
        ORDER BY name
    ''', [id]).fetchone()

    movies = db.execute('''
        SELECT show_id, title
        FROM shows
        NATURAL JOIN types
        NATURAL JOIN genres
        WHERE genre_id = ?
        ORDER BY title
    ''', [id]).fetchall()

    return render_template('genre.html',
                           info=info,
                           movies=movies)

# Production
@APP.route('/production-companies/')
def list_producers():
    companies = db.execute('''
        SELECT producer_id, name
        FROM companies
        ORDER BY producer_id
    ''').fetchall()
    return render_template('production-companies.html', companies=companies)


# cada producer
@APP.route('/production-companies/<int:id>/')
def get_producer(id):
    info = db.execute('''
        SELECT name AS producer_name, COUNT(show_id) AS total
        FROM companies
        NATURAL JOIN production
        WHERE producer_id = ?
        order by name
    ''', [id]).fetchone()

    movies = db.execute('''
        SELECT show_id, title
        FROM shows
        NATURAL JOIN production
        NATURAL JOIN companies
        WHERE producer_id = ?
        ORDER BY title
    ''', [id]).fetchall()

    return render_template('producer.html',
                           info=info,
                           movies=movies)

# People
@APP.route('/people/')
def list_people():
    people = db.execute('''
        SELECT 
            p.person_id,
            p.name,
            REPLACE(GROUP_CONCAT(DISTINCT r.role), ',', ', ') AS roles
        FROM people p

        LEFT JOIN (
            SELECT DISTINCT person_id, 'actor' AS role FROM top_cast
            UNION 
            SELECT DISTINCT person_id, 'director' AS role FROM directors
            UNION 
            SELECT DISTINCT person_id, 'creator' AS role FROM creators
            UNION 
            SELECT DISTINCT person_id, 'writer' AS role FROM writers
        ) r
        ON p.person_id = r.person_id

        GROUP BY p.person_id, p.name
        ORDER BY p.name;
    ''').fetchall()

    return render_template('people-list.html', people=people)

# each person
@APP.route('/person/<int:id>/')
def person_movies(id):
    person = db.execute("""
        SELECT person_id, name
        FROM people
        WHERE person_id = ?
    """, [id]).fetchone()

    movies = db.execute("""
        SELECT m.show_id, m.title, r.role
        FROM shows m
        LEFT JOIN (
            SELECT show_id, person_id, 'actor' AS role FROM top_cast
            UNION ALL
            SELECT show_id, person_id, 'director' AS role FROM directors
            UNION ALL
            SELECT show_id, person_id, 'creator' AS role FROM creators
            UNION ALL
            SELECT show_id, person_id, 'writer' AS role FROM writers
        ) r
        ON m.show_id = r.show_id
        WHERE r.person_id = ?
        ORDER BY m.title, r.role
    """, [id]).fetchall()

    return render_template("person.html", person=person, movies=movies)



# ... (o teu código de configuração existente) ...

def get_db():
    # Ajusta isto para a tua conexão de base de dados atual
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('a_tua_base_de_dados.db') # MUDAR O NOME
        db.row_factory = sqlite3.Row # Isto permite chamar colunas por nome
    return db

@app.route('/faq')
def faq_stats():
    db = get_db()
    cursor = db.cursor()
    
    stats = {}

    # 1. Maior Metascore (com desempate por contagem)
    query_meta = """
    SELECT g.name as genre, s.title, m.metascore
    FROM shows s
    NATURAL JOIN metascore m
    NATURAL JOIN types
    NATURAL JOIN genres g
    WHERE m.metascore = (
        SELECT MAX(m.metascore) FROM metascore m
        NATURAL JOIN types NATURAL JOIN genres g1 WHERE g1.name = g.name
    ) AND m.metascore_count = (
        SELECT MAX(m1.metascore_count) FROM metascore m1
        NATURAL JOIN types NATURAL JOIN genres g2 
        WHERE g2.genre_id = g.genre_id AND m1.metascore = m.metascore 
    )
    ORDER BY g.name;
    """
    stats['top_metascore'] = cursor.execute(query_meta).fetchall()

    # 2. Maior Userscore
    query_user = """
    SELECT g.name as genre, s.title, u.userscore
    FROM shows s
    NATURAL JOIN userscore u
    NATURAL JOIN types
    NATURAL JOIN genres g
    WHERE u.userscore = (
        SELECT MAX(u.userscore) FROM userscore u
        NATURAL JOIN types NATURAL JOIN genres g1 WHERE g1.name = g.name
    ) AND u.userscore_count = (
        SELECT MAX(u1.userscore_count) FROM userscore u1
        NATURAL JOIN types NATURAL JOIN genres g2 
        WHERE g2.genre_id = g.genre_id AND u1.userscore = u.userscore 
    )
    ORDER BY g.name;
    """
    stats['top_userscore'] = cursor.execute(query_user).fetchall()

    # 3. Top 10 Diferença Percentual
    query_diff_perc = """
    SELECT s.title, ms.metascore, us.userscore * 10 AS userscore_scaled,
    ABS(CAST(ms.metascore AS REAL) - (us.userscore * 10)) / (us.userscore * 10) * 100 AS diff_perc
    FROM shows s
    JOIN metascore ms ON s.show_id = ms.show_id
    JOIN userscore us ON s.show_id = us.show_id
    WHERE us.userscore_count >= 50 AND ms.metascore_count >= 10 AND (us.userscore * 10) > 0
    ORDER BY diff_perc DESC LIMIT 10;
    """
    stats['diff_perc'] = cursor.execute(query_diff_perc).fetchall()

    # 4. Top 20 Diferença Absoluta
    query_diff_abs = """
    SELECT s.title, ABS(m.metascore - (u.userscore * 10)) AS diff 
    FROM shows s
    NATURAL JOIN metascore m 
    NATURAL JOIN userscore u
    WHERE metascore_count != 0 AND userscore_count != 0
    ORDER BY diff DESC, s.title LIMIT 20;
    """
    # Nota: ajustei u.userscore * 10 para ficar na mesma escala que metascore
    stats['diff_abs'] = cursor.execute(query_diff_abs).fetchall()

    # 5. Diretores "Elite" (>5 shows, rating acima da média)
    query_directors = """
    SELECT p.name, COUNT(s.show_id) AS total, AVG(s.rating) AS avg_rating
    FROM people p
    JOIN directors d ON p.person_id = d.person_id
    JOIN shows s ON d.show_id = s.show_id
    GROUP BY p.person_id, p.name
    HAVING COUNT(s.show_id) > 5
    AND AVG(s.rating) > (SELECT AVG(rating) FROM shows WHERE rating IS NOT NULL)
    ORDER BY avg_rating DESC;
    """
    stats['elite_directors'] = cursor.execute(query_directors).fetchall()

    # 6. Pessoa "Cult" (User > 9.0, Meta < 60)
    query_cult = """
    WITH CultShows AS (
        SELECT s.show_id FROM shows s
        JOIN userscore us ON s.show_id = us.show_id
        JOIN metascore ms ON s.show_id = ms.show_id
        WHERE us.userscore > 9.0 AND ms.metascore < 60
    ),
    AllInvolvements AS (
        SELECT person_id, show_id FROM directors
        UNION ALL SELECT person_id, show_id FROM writers
        UNION ALL SELECT person_id, show_id FROM cast
        UNION ALL SELECT person_id, show_id FROM creators
    )
    SELECT p.name, COUNT(ai.show_id) AS count
    FROM people p
    JOIN AllInvolvements ai ON p.person_id = ai.person_id
    JOIN CultShows cs ON ai.show_id = cs.show_id
    GROUP BY p.person_id, p.name
    ORDER BY count DESC LIMIT 1;
    """
    stats['cult_hero'] = cursor.execute(query_cult).fetchone()

    # 7. Shows com mesmo elenco em anos diferentes
    query_cast = """
    WITH PrincipalCast AS (
        SELECT show_id, GROUP_CONCAT(person_id ORDER BY person_id ASC) AS cast_list
        FROM (
            SELECT show_id, person_id, ROW_NUMBER() OVER(PARTITION BY show_id ORDER BY person_id ASC) as rn
            FROM cast
        ) WHERE rn <= 5 GROUP BY show_id HAVING COUNT(person_id) = 5
    )
    SELECT s1.title AS t1, s2.title AS t2, s1.releaseDate AS y1, s2.releaseDate AS y2
    FROM PrincipalCast pc1
    JOIN PrincipalCast pc2 ON pc1.cast_list = pc2.cast_list AND pc1.show_id < pc2.show_id
    JOIN shows s1 ON pc1.show_id = s1.show_id
    JOIN shows s2 ON pc2.show_id = s2.show_id
    WHERE strftime('%Y', s1.releaseDate) <> strftime('%Y', s2.releaseDate);
    """
    stats['same_cast'] = cursor.execute(query_cast).fetchall()

    # 8. Pessoa com múltiplos papéis no mesmo show
    query_roles = """
    SELECT DISTINCT s.title, p.name
    FROM shows s
    LEFT JOIN directors d ON s.show_id = d.show_id
    LEFT JOIN writers w ON s.show_id = w.show_id
    LEFT JOIN creators c ON s.show_id = c.show_id
    LEFT JOIN cast tc ON s.show_id = tc.show_id
    LEFT JOIN people p ON p.person_id = COALESCE(d.person_id, w.person_id, c.person_id, tc.person_id)
    WHERE (d.person_id IS NOT NULL AND w.person_id = d.person_id)
       OR (d.person_id IS NOT NULL AND tc.person_id = d.person_id)
       OR (d.person_id IS NOT NULL AND c.person_id = d.person_id)
       OR (w.person_id IS NOT NULL AND tc.person_id = w.person_id)
       OR (w.person_id IS NOT NULL AND c.person_id = w.person_id)
    ORDER BY s.title LIMIT 50; 
    """
    # Adicionei LIMIT 50 para a página não ficar gigante
    stats['multi_roles'] = cursor.execute(query_roles).fetchall()

    return render_template('faq.html', stats=stats)