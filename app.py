import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from flask import render_template, Flask, abort
import logging
import db


APP = Flask(__name__)

# Start page (mudar as stats que qeuro que aparceçam aqui)
@APP.route('/')
def index():
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
    ''', [id]).fetchall()

    # Obter atores do filme
    actors = db.execute('''
        SELECT name
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

    return render_template('movie.html',
                           movie=movie,
                           genres=genres,
                           actors=actors,
                           scores = scores)

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
