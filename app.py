import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from flask import render_template, Flask, abort, g, request
import logging
import db
import sqlite3
from math import ceil

APP = Flask(__name__)

# Start page
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
    return render_template('index.html', stats=stats)

# Filmes 
@APP.route('/shows/')
def list_movies():
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '').lower()

    all_movies = db.execute('''
        SELECT show_id, title
        FROM shows
        ORDER BY title
    ''').fetchall()

    filtered_movies = [m for m in all_movies if search in m['title'].lower()]

    items_per_page = 100
    total_pages = ceil(len(filtered_movies) / items_per_page)
    movies = filtered_movies[(page-1)*items_per_page : page*items_per_page]

    return render_template('movie-list.html', movies=movies, page=page, total_pages=total_pages, search=search)

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

    genres = db.execute('''
        SELECT g.name
        FROM types 
        NATURAL JOIN genres g
        WHERE show_id = ?
        ORDER BY g.name
    ''', [id]).fetchall()

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

    creators = db.execute('''
        SELECT name, person_id
        FROM creators
        NATURAL JOIN people
        WHERE show_id = ?
    ''', [id]).fetchall()

    writers = db.execute('''
        SELECT name, person_id
        FROM writers
        NATURAL JOIN people
        WHERE show_id = ?
    ''', [id]).fetchall()

    directors = db.execute('''
        SELECT name, person_id
        FROM directors
        NATURAL JOIN people
        WHERE show_id = ?
    ''', [id]).fetchall()

    producers = db.execute('''
        SELECT name, producer_id
        FROM production
        NATURAL JOIN companies
        WHERE show_id = ?
    ''', [id]).fetchall()

    return render_template('movie.html',
                           movie=movie,
                           genres=genres,
                           actors=actors,
                           scores=scores,
                           creators=creators,
                           writers=writers,
                           directors=directors,
                           producers=producers)

# Genres
@APP.route('/genres/')
def list_genres():
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '').lower()

    all_genres = db.execute('''
        SELECT genre_id, name
        FROM genres
        ORDER BY name
    ''').fetchall()

    filtered_genres = [g for g in all_genres if search in g['name'].lower()]

    items_per_page = 100
    total_pages = ceil(len(filtered_genres) / items_per_page)
    genres = filtered_genres[(page-1)*items_per_page : page*items_per_page]

    return render_template('genre-list.html', genres=genres, page=page, total_pages=total_pages, search=search)

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

    return render_template('genre.html', info=info, movies=movies)

# Production companies
@APP.route('/production-companies/')
def list_producers():
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '').lower()

    all_companies = db.execute('''
        SELECT producer_id, name
        FROM companies
        ORDER BY name
    ''').fetchall()

    filtered_companies = [c for c in all_companies if search in c['name'].lower()]

    items_per_page = 100
    total_pages = ceil(len(filtered_companies) / items_per_page)
    companies = filtered_companies[(page-1)*items_per_page : page*items_per_page]

    return render_template('production-companies.html', companies=companies, page=page, total_pages=total_pages, search=search)

@APP.route('/production-companies/<int:id>/')
def get_producer(id):
    info = db.execute('''
        SELECT name AS producer_name, COUNT(show_id) AS total
        FROM companies
        NATURAL JOIN production
        WHERE producer_id = ?
        ORDER BY name
    ''', [id]).fetchone()

    movies = db.execute('''
        SELECT show_id, title
        FROM shows
        NATURAL JOIN production
        NATURAL JOIN companies
        WHERE producer_id = ?
        ORDER BY title
    ''', [id]).fetchall()

    return render_template('producer.html', info=info, movies=movies)

# People
@APP.route('/people/')
def list_people():
    page = int(request.args.get('page', 1))
    search = request.args.get('search', '').lower()

    all_people = db.execute('''
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
        ) r ON p.person_id = r.person_id
        GROUP BY p.person_id, p.name
        ORDER BY p.name;
    ''').fetchall()

    filtered_people = [p for p in all_people if search in p['name'].lower()]

    items_per_page = 100
    total_pages = ceil(len(filtered_people) / items_per_page)
    people = filtered_people[(page-1)*items_per_page : page*items_per_page]

    return render_template('people-list.html', people=people, page=page, total_pages=total_pages, search=search)

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

# FAQ e perguntas 
@APP.route('/faq/')
def list_questions():
    questions = [
        ("p1", "Highest metascore by genre"),
        ("p2", "Highest userscore by genre"),
        ("p3", "Percentage histogram of movies by metascore range"),
        ("p4", "Top 20 largest absolute difference meta vs user"),
        ("p5", "Show with highest metascore each year"),
        ("p6", "Shows with metascore higher than the average of their genre"),
        ("p7", "Shows with the same main cast in different years"),
        ("p8", "Shows where a person had different roles"),
        ("p9", "Top 100 shows with most people in production"),
        ("p10","Bottom 100 shows with least people in production"),
        ("p11","Top 5 Genres with Most Movies"),
        ("p12","Genre with Highest Metascore by Decade"),
        ("p13","Genre with Highest Userscore by Decade"),
    ]
    return render_template("faq.html", questions=questions)

# --------------------------
# p1 — Maior metascore por género
# --------------------------
@APP.route('/faq/p1/')
def pergunta1():
    p1 = db.execute("""
        SELECT g.name, s.title, m.metascore
        FROM shows s
        NATURAL JOIN metascore m
        NATURAL JOIN types
        NATURAL JOIN genres g
        WHERE m.metascore = (
            SELECT MAX(m2.metascore)
            FROM metascore m2
            NATURAL JOIN types 
            NATURAL JOIN genres g1
            WHERE g1.name = g.name
        )
        AND m.metascore_count = (
            SELECT MAX(m3.metascore_count)
            FROM metascore m3
            NATURAL JOIN types
            NATURAL JOIN genres g2
            WHERE g2.genre_id = g.genre_id AND m3.metascore = m.metascore
        )
        ORDER BY g.name;
    """).fetchall()

    return render_template("p1.html", p1=p1)


# --------------------------
# p2 — Maior userscore por género
# --------------------------
@APP.route('/faq/p2/')
def pergunta2():
    p2 = db.execute("""
        SELECT g.name, s.title, u.userscore
        FROM shows s
        NATURAL JOIN userscore u
        NATURAL JOIN types
        NATURAL JOIN genres g
        WHERE u.userscore = (
            SELECT MAX(u2.userscore)
            FROM userscore u2
            NATURAL JOIN types 
            NATURAL JOIN genres g1
            WHERE g1.name = g.name
        )
        AND u.userscore_count = (
            SELECT MAX(u3.userscore_count)
            FROM userscore u3
            NATURAL JOIN types
            NATURAL JOIN genres g2
            WHERE g2.genre_id = g.genre_id AND u3.userscore = u.userscore
        )
        ORDER BY g.name;
    """).fetchall()

    return render_template("p2.html", p2=p2)


# --------------------------
# p3 — histograma percentual de filmes por faixa de metascore
# --------------------------
@APP.route('/faq/p3/')
def pergunta3():
    p3 = db.execute("""
        WITH Total AS (
            SELECT COUNT(*) AS total_filmes
            FROM metascore
        ),
        Buckets AS (
            SELECT 
                (metascore / 20) * 20 AS bucket_start,
                COUNT(*) AS total_in_bucket
            FROM metascore
            GROUP BY bucket_start
        )
        SELECT
            bucket_start || '-' || (bucket_start + 19) AS interval,
            ROUND((CAST(total_in_bucket AS REAL) / (SELECT total_filmes FROM Total)) * 100, 2) AS percent
        FROM Buckets
        ORDER BY bucket_start;
    """).fetchall()
    return render_template("p3.html", p3=p3)



# --------------------------
# p4 — Top 20 maior diferença absoluta meta vs user
# --------------------------
@APP.route('/faq/p4/')
def pergunta4():
    p4 = db.execute("""
        SELECT s.title, ABS(m.metascore - u.userscore) AS diferenca
        FROM shows s
        NATURAL JOIN metascore m
        NATURAL JOIN userscore u
        WHERE metascore_count != 0 AND userscore_count != 0
        ORDER BY diferenca DESC, s.title
        LIMIT 20;
    """).fetchall()

    return render_template("p4.html", p4=p4)


# --------------------------
# p5 — Filme com maior metascore em cada ano
# --------------------------
@APP.route('/faq/p5/')
def p5():
    p5 = db.execute("""
        WITH MaxMetascorePerYear AS (
        SELECT substr(s.releaseDate,1,4) AS year,
            MAX(m.metascore) AS max_metascore
        FROM shows s
        JOIN metascore m ON s.show_id = m.show_id
        WHERE m.metascore IS NOT NULL
        GROUP BY year
        )
        SELECT s.title, s.releaseDate, substr(s.releaseDate,1,4) AS year, m.metascore
        FROM MaxMetascorePerYear mm
        JOIN shows s ON substr(s.releaseDate,1,4) = mm.year
        JOIN metascore m ON s.show_id = m.show_id
        WHERE m.metascore = mm.max_metascore
        AND s.show_id = (
            SELECT MIN(s2.show_id)
            FROM shows s2
            JOIN metascore m2 ON s2.show_id = m2.show_id
            WHERE substr(s2.releaseDate,1,4) = mm.year
            AND m2.metascore = mm.max_metascore
        )
        ORDER BY year;
    """).fetchall()
    return render_template('p5.html', p5=p5)



# --------------------------
# p6 — Filmes com metascore maior que a média do seu género
# --------------------------
@APP.route('/faq/p6/')
def pergunta6():
    p6 = db.execute("""
        SELECT 
            s.title AS title,
            g.name AS genre,
            m.metascore AS metascore
        FROM shows s
        JOIN metascore m ON s.show_id = m.show_id
        JOIN types t ON s.show_id = t.show_id
        JOIN genres g ON t.genre_id = g.genre_id
        WHERE m.metascore IS NOT NULL
        AND m.metascore > (
            SELECT AVG(m2.metascore)
            FROM shows s2
            JOIN metascore m2 ON s2.show_id = m2.show_id
            JOIN types t2 ON s2.show_id = t2.show_id
            WHERE t2.genre_id = g.genre_id
        )
        ORDER BY g.name, m.metascore DESC;

    """).fetchall()

    return render_template("p6.html", p6=p6)




# --------------------------
# p7 — Shows com o mesmo elenco principal em anos diferentes
# --------------------------
@APP.route('/faq/p7/')
def pergunta7():
    p7 = db.execute("""
        WITH PrincipalCast AS (
            SELECT t.show_id,
                   GROUP_CONCAT(t.person_id, ',') AS principal_cast_list
            FROM top_cast t
            WHERE t.person_id IN (
                SELECT person_id
                FROM top_cast t2
                WHERE t2.show_id = t.show_id
                ORDER BY person_id ASC
                LIMIT 5
            )
            GROUP BY t.show_id
            HAVING COUNT(*) = 5
        )
        SELECT
            s1.title AS show_1_title,
            s2.title AS show_2_title,
            s1.releaseDate AS show_1_year,
            s2.releaseDate AS show_2_year
        FROM PrincipalCast pc1
        JOIN PrincipalCast pc2
          ON pc1.principal_cast_list = pc2.principal_cast_list
         AND pc1.show_id < pc2.show_id
        JOIN shows s1 ON pc1.show_id = s1.show_id
        JOIN shows s2 ON pc2.show_id = s2.show_id
        WHERE STRFTIME('%Y', s1.releaseDate) <> STRFTIME('%Y', s2.releaseDate);
    """).fetchall()

    return render_template("p7.html", p7=p7)



# --------------------------
# p8 — Shows onde uma pessoa teve papéis diferentes
# --------------------------
@APP.route('/faq/p8/')
def pergunta8():
    p8 = db.execute("""
        SELECT DISTINCT s.title, p.name
        FROM shows s
        LEFT JOIN directors d ON s.show_id = d.show_id
        LEFT JOIN writers w ON s.show_id = w.show_id
        LEFT JOIN creators c ON s.show_id = c.show_id
        LEFT JOIN top_cast tc ON s.show_id = tc.show_id
        LEFT JOIN people p ON p.person_id = COALESCE(d.person_id, w.person_id, c.person_id, tc.person_id)
        WHERE (d.person_id IS NOT NULL AND w.person_id = d.person_id)
           OR (d.person_id IS NOT NULL AND tc.person_id = d.person_id)
           OR (d.person_id IS NOT NULL AND c.person_id = d.person_id)
           OR (w.person_id IS NOT NULL AND tc.person_id = w.person_id)
           OR (w.person_id IS NOT NULL AND c.person_id = w.person_id)
        ORDER BY s.title;
    """).fetchall()

    return render_template("p8.html", p8=p8)


# --------------------------
# p9 — Top 100 shows com mais pessoas na produção
# --------------------------
@APP.route('/faq/p9/')
def pergunta9():
    p9 = db.execute("""
        SELECT s.title, 
               COUNT(DISTINCT d.person_id) +
               COUNT(DISTINCT w.person_id) +
               COUNT(DISTINCT c.person_id) AS total_people
        FROM shows s
        LEFT JOIN directors d ON s.show_id = d.show_id
        LEFT JOIN writers w ON s.show_id = w.show_id
        LEFT JOIN creators c ON s.show_id = c.show_id
        GROUP BY s.title
        ORDER BY total_people DESC
        LIMIT 100;
    """).fetchall()

    return render_template("p9.html", p9=p9)


# --------------------------
# p10 — Bottom 100 shows com menos pessoas (cast+writer+creator+director)
# --------------------------
@APP.route('/faq/p10/')
def pergunta10():
    p10 = db.execute("""
        SELECT s.title,
               COUNT(DISTINCT d.person_id) +
               COUNT(DISTINCT w.person_id) +
               COUNT(DISTINCT c.person_id) AS total_people
        FROM shows s
        LEFT JOIN directors d ON s.show_id = d.show_id
        LEFT JOIN writers w ON s.show_id = w.show_id
        LEFT JOIN creators c ON s.show_id = c.show_id
        GROUP BY s.title
        HAVING total_people > 0
        ORDER BY total_people
        LIMIT 100;
    """).fetchall()

    return render_template("p10.html", p10=p10)


# --------------------------
# p11 — Top 5 Gêneros com Mais Filmes
# --------------------------

@APP.route('/faq/p11/')
def pergunta11():
    p11 = db.execute("""
        SELECT 
            g.name AS genre,
            COUNT(t.show_id) AS total_movies
        FROM genres g
        JOIN types t ON g.genre_id = t.genre_id
        GROUP BY g.genre_id
        ORDER BY total_movies DESC
        LIMIT 5;
    """).fetchall()
    return render_template("p11.html", p11=p11)

# --------------------------
# p12 — Gênero com Maior Metascore por Década
# --------------------------


@APP.route('/faq/p12/')
def pergunta12():
    p12 = db.execute("""
        WITH MetaPerDecade AS (
            SELECT 
                (CAST(substr(s.releaseDate,1,4) AS INTEGER) / 10) * 10 AS decade,
                g.genre_id,
                g.name AS genre,
                MAX(m.metascore) AS max_metascore,
                COUNT(*) AS film_count
            FROM shows s
            JOIN types t ON s.show_id = t.show_id
            JOIN genres g ON t.genre_id = g.genre_id
            JOIN metascore m ON s.show_id = m.show_id
            WHERE releaseDate IS NOT NULL
            AND length(releaseDate) >= 4
            AND substr(releaseDate,1,4) GLOB '[0-9][0-9][0-9][0-9]'
            GROUP BY decade, g.genre_id
        ),
        Ranked AS (
            SELECT 
                decade,
                genre,
                max_metascore,
                film_count,
                ROW_NUMBER() OVER (
                    PARTITION BY decade
                    ORDER BY max_metascore DESC, film_count DESC, genre_id ASC
                ) AS rn
            FROM MetaPerDecade
        )
        SELECT decade, genre, max_metascore
        FROM Ranked
        WHERE rn = 1
        ORDER BY decade;
    """).fetchall()
    return render_template("p12.html", p12=p12)

# --------------------------
# p13 — Gênero com Maior Userscore por Década
# --------------------------

@APP.route('/faq/p13/')
def pergunta13():
    p13 = db.execute("""
        WITH UserPerDecade AS (
            SELECT 
                (CAST(substr(s.releaseDate,1,4) AS INTEGER) / 10) * 10 AS decade,
                g.genre_id,
                g.name AS genre,
                MAX(u.userscore) AS max_userscore,
                COUNT(*) AS film_count
            FROM shows s
            JOIN types t ON s.show_id = t.show_id
            JOIN genres g ON t.genre_id = g.genre_id
            JOIN userscore u ON s.show_id = u.show_id
            WHERE releaseDate IS NOT NULL
              AND length(releaseDate) >= 4
              AND substr(releaseDate,1,4) GLOB '[0-9][0-9][0-9][0-9]'
            GROUP BY decade, g.genre_id
        ),
        Ranked AS (
            SELECT 
                decade,
                genre,
                max_userscore,
                film_count,
                ROW_NUMBER() OVER (
                    PARTITION BY decade
                    ORDER BY max_userscore DESC, film_count DESC, genre_id ASC
                ) AS rn
            FROM UserPerDecade
        )
        SELECT decade, genre, max_userscore
        FROM Ranked
        WHERE rn = 1
        ORDER BY decade;
    """).fetchall()
    
    return render_template("p13.html", p13=p13)



