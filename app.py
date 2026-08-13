import re
import csv
import io
import os
import sqlite3
from datetime import date
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-fallback-key")

DB_PATH = "swara.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@login_required
def index():
    return render_template("filter.html")


@app.route("/welcome")
def welcome():
    return render_template("welcome.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not first_name or not last_name or not email or not password:
            flash("All fields are required.")
            return render_template("register.html")

        if not is_valid_email(email):
            flash("Please enter a valid email address.")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return render_template("register.html")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            db.close()
            flash("Email already registered.")
            return render_template("register.html")

        hash = generate_password_hash(password)
        db.execute(
            "INSERT INTO users (first_name, last_name, email, hash) VALUES (?, ?, ?, ?)",
            (first_name, last_name, email, hash)
        )
        db.commit()
        db.close()

        flash("Registered successfully. Please log in.")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Must provide email and password.")
            return render_template("login.html")

        db = get_db()
        row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if row is None or not check_password_hash(row["hash"], password):
            flash("Invalid email and/or password.")
            return render_template("login.html")

        session["user_id"] = row["id"]
        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/pwdreset")
def reset():
    return render_template("pwdreset.html")


@app.route("/filter", methods=["GET"])
@login_required
def filter_songs():
    ragam = request.args.get("Ragam", "").strip()
    talam = request.args.get("Talam", "").strip()
    composer = request.args.get("Composer", "").strip()
    deity = request.args.get("Deity", "").strip()
    song_type = request.args.get("Type", "").strip()

    query = "SELECT * FROM songs WHERE user_id = ?"
    params = [session["user_id"]]

    if ragam:
        query += " AND ragam LIKE ?"
        params.append(f"%{ragam}%")
    if talam:
        query += " AND talam LIKE ?"
        params.append(f"%{talam}%")
    if composer:
        query += " AND composer LIKE ?"
        params.append(f"%{composer}%")
    if deity:
        query += " AND deity LIKE ?"
        params.append(f"%{deity}%")
    if song_type:
        query += " AND song_type LIKE ?"
        params.append(f"%{song_type}%")

    query += " ORDER BY title"

    db = get_db()
    songs = db.execute(query, params).fetchall()
    db.close()

    return render_template("filtered.html", songs=songs)

@app.route("/songs")
@login_required
def songs():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM songs WHERE user_id = ? ORDER BY title", (session["user_id"],)
    ).fetchall()
    db.close()
    return render_template("songs.html", songs=rows)


@app.route("/songs/add", methods=["POST"])
@login_required
def add_song():
    title = request.form.get("title")
    ragam = request.form.get("ragam")
    talam = request.form.get("talam")
    composer = request.form.get("composer")
    deity = request.form.get("deity")
    song_type = request.form.get("song_type")

    if not title:
        flash("Title is required.")
        return redirect("/songs")

    db = get_db()
    db.execute(
        "INSERT INTO songs (user_id, title, ragam, talam, composer, deity, song_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session["user_id"], title, ragam, talam, composer, deity, song_type)
    )
    db.commit()
    db.close()

    flash(f"Added {title}.")
    return redirect("/songs")

@app.route("/songs/import", methods=["POST"])
@login_required
def import_songs():
    file = request.files.get("csv_file")
    if not file or file.filename == "":
        flash("No file selected.")
        return redirect("/songs")

    stream = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.DictReader(stream)

    db = get_db()
    count = 0
    for row in reader:
        title = row.get("title", "").strip()
        if not title:
            continue
        db.execute(
            "INSERT INTO songs (user_id, title, ragam, talam, composer, deity, song_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session["user_id"],
                title,
                row.get("ragam", "").strip(),
                row.get("talam", "").strip(),
                row.get("composer", "").strip(),
                row.get("deity", "").strip(),
                row.get("song_type", "").strip(),
            )
        )
        count += 1
    db.commit()
    db.close()

    flash(f"Imported {count} songs.")
    return redirect("/songs")

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html")

@app.route("/plog")
@login_required
def practice_log():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM practice_log WHERE user_id = ? ORDER BY date DESC", (session["user_id"],)
    ).fetchall()
    db.close()
    return render_template("practiceLog.html", entries=rows, date=date.today().isoformat())


@app.route("/plog/add", methods=["POST"])
@login_required
def add_practice():
    entry = request.form.get("entry")
    songs = request.form.get("songs")

    if not entry:
        flash("Please describe what you practiced.")
        return redirect("/plog")

    db = get_db()
    db.execute(
        "INSERT INTO practice_log (user_id, entry, songs, date) VALUES (?, ?, ?, ?)",
        (session["user_id"], entry, songs, date.today().isoformat())
    )
    db.commit()
    db.close()

    flash("Practice entry added.")
    return redirect("/plog")

if __name__ == "__main__":
    app.run(debug=True)