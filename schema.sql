CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL
);

CREATE TABLE songs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    ragam TEXT,
    talam TEXT,
    composer TEXT,
    deity TEXT,
    song_type TEXT,
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);