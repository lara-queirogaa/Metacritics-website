import sqlite3
import pandas as pd
import math

df = pd.read_csv("tv_shows.csv")
df = df.rename(columns={"id": "show_id"})
conn = sqlite3.connect("Metacritic.db")
cur = conn.cursor()

cur.executescript("""
    DROP TABLE IF EXISTS genres;
    DROP TABLE IF EXISTS companies;
    DROP TABLE IF EXISTS people;
    DROP TABLE IF EXISTS metascore;
    DROP TABLE IF EXISTS userscore;
    DROP TABLE IF EXISTS shows;
    DROP TABLE IF EXISTS types;
    DROP TABLE IF EXISTS production;
    DROP TABLE IF EXISTS directors;
    DROP TABLE IF EXISTS writers;
    DROP TABLE IF EXISTS top_cast;
    DROP TABLE IF EXISTS creators;

    CREATE TABLE genres(
        genre_id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name             VARCHAR(50) NOT NULL   
    );

    CREATE TABLE companies(
        producer_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        name             VARCHAR(50) NOT NULL   
    );

    CREATE TABLE people(
        person_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        name             VARCHAR(100) NOT NULL   
    );

    CREATE TABLE metascore(
        show_id          INTEGER NOT NULL PRIMARY KEY,
        metascore        INTEGER,
        metascore_count  INTEGER 
    );

    CREATE TABLE userscore(
        show_id          INTEGER NOT NULL PRIMARY KEY,
        userscore        INTEGER,
        userscore_count  INTEGER
    );

    CREATE TABLE shows(
        show_id          INTEGER PRIMARY KEY,
        title            VARCHAR(100) NOT NULL,
        releaseDate      INTEGER,
        rating           VARCHAR(30),
        description      VARCHAR(500),
        duration         INTEGER,
        num_seasons      INTEGER NOT NULL,
        tagline          VARCHAR(100),
        FOREIGN KEY (show_id) REFERENCES metascore(show_id),
        FOREIGN KEY (show_id) REFERENCES userscore(show_id)
    );

    CREATE TABLE types(
        show_id          INTEGER NOT NULL,
        genre_id         INTEGER NOT NULL,
        PRIMARY KEY (show_id, genre_id),
        FOREIGN KEY (show_id) REFERENCES shows(show_id),
        FOREIGN KEY (genre_id) REFERENCES genres(genre_id)
    );

    CREATE TABLE production(
        show_id          INTEGER NOT NULL,
        producer_id      INTEGER NOT NULL,
        PRIMARY KEY (show_id, producer_id),
        FOREIGN KEY (show_id) REFERENCES shows(show_id),
        FOREIGN KEY (producer_id) REFERENCES companies(producer_id)
    );

    CREATE TABLE directors(
        show_id          INTEGER NOT NULL,
        person_id        INTEGER NOT NULL,
        PRIMARY KEY (show_id, person_id),
        FOREIGN KEY (show_id) REFERENCES shows(show_id),
        FOREIGN KEY (person_id) REFERENCES people(person_id)
    );

    CREATE TABLE writers(
        show_id          INTEGER NOT NULL,
        person_id        INTEGER NOT NULL,
        PRIMARY KEY (show_id, person_id),
        FOREIGN KEY (show_id) REFERENCES shows(show_id),
        FOREIGN KEY (person_id) REFERENCES people(person_id)
    );

    CREATE TABLE top_cast(
        show_id          INTEGER NOT NULL,
        person_id        INTEGER NOT NULL,
        PRIMARY KEY (show_id, person_id),
        FOREIGN KEY (show_id) REFERENCES shows(show_id),
        FOREIGN KEY (person_id) REFERENCES people(person_id)
    );

    CREATE TABLE creators(
        show_id          INTEGER NOT NULL,
        person_id        INTEGER NOT NULL,
        PRIMARY KEY (show_id, person_id),
        FOREIGN KEY (show_id) REFERENCES shows(show_id),
        FOREIGN KEY (person_id) REFERENCES people(person_id)
    );
""")


#coloca os dados na tabela shows
df[["show_id", "title", "releaseDate", "rating", "description", "duration",
    "num_seasons", "tagline"]].to_sql("shows", conn, if_exists="append", index = False)

#coloca os dados na tabela metascore
df[["show_id", "metascore", "metascore_count"]].to_sql("metascore", conn, if_exists="append", index = False)

#userscore
df[["show_id", "userscore", "userscore_count"]].to_sql("userscore", conn, if_exists="append", index = False)

#genres
all_genres = (
    df["genres"].str.split(",").explode().str.strip().unique()
)

for c in all_genres:
    cur.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (c,))
conn.commit()

#types
for _, row in df.iterrows():
    show_id = row["show_id"]
    genres = row["genres"]
    if not genres or pd.isna(genres):
        continue
    for g in genres.split(","):
        genre_name = g.strip()
        if genre_name == "":
            continue
        cur.execute("SELECT genre_id FROM genres WHERE name = ?", (genre_name,))
        genre_id = cur.fetchone()[0]
        cur.execute("INSERT OR IGNORE INTO types (show_id, genre_id) VALUES (?, ?)", (show_id, genre_id))
conn.commit()

#companies
all_companies = (
    df["production_companies"].str.split(",").explode().str.strip().unique()
)

for c in all_companies:
    cur.execute("INSERT OR IGNORE INTO companies (name) VALUES (?)", (c,))
conn.commit()

#production
for _, row in df.iterrows():
    show_id = row["show_id"]
    companies = row["production_companies"]
    if not companies or pd.isna(companies):
        continue
    for c in companies.split(","):
        company_name = c.strip()
        if company_name == "":
            continue
        cur.execute("SELECT producer_id FROM companies WHERE name = ?", (company_name,))
        producer_id = cur.fetchone()[0]
        cur.execute("INSERT OR IGNORE INTO production (show_id, producer_id) VALUES (?, ?)", (show_id, producer_id))
conn.commit()

#people, top_cast, writers, creators e directors
def explode_names(cell):
    if cell is None:
        return []
    if isinstance(cell, float) and math.isnan(cell):
        return []
    s = str(cell).strip()
    if s == "":
        return []
    return [p.strip() for p in s.split(",") if p.strip() != ""]


def get_or_create_person(cur, name):
    cur.execute("SELECT person_id FROM people WHERE name = ?", (name,))
    rows = cur.fetchall()

    if len(rows) > 0:
        main_id = rows[0][0]
        for extra in rows[1:]:
            cur.execute("DELETE FROM people WHERE person_id = ?", (extra[0],))

        return main_id

    cur.execute("INSERT INTO people (name) VALUES (?)", (name,))
    return cur.lastrowid


def populate_relationship(df, cur, conn, colname, link_table):
    for _, row in df.iterrows():
        show_id = row.get("show_id")
        if show_id is None or (isinstance(show_id, float) and math.isnan(show_id)):
            continue

        names = explode_names(row.get(colname))

        for name in names:
            pid = get_or_create_person(cur, name)
            cur.execute(
                f"INSERT OR IGNORE INTO {link_table} (show_id, person_id) VALUES (?, ?)",
                (show_id, pid)
            )

    conn.commit()

populate_relationship(df, cur, conn, "director",    "directors")
populate_relationship(df, cur, conn, "writer",      "writers")
populate_relationship(df, cur, conn, "top_cast",    "top_cast")
populate_relationship(df, cur, conn, "created_by",  "creators")

conn.commit()
conn.close()