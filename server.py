from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort
import sqlite3
import random
import math
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'change-me-in-production'

# Database setup
def init_db():
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image_url TEXT,
            elo_rating INTEGER DEFAULT 1500,
            matches_played INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            winner_id INTEGER,
            loser_id INTEGER,
            winner_elo_before INTEGER,
            loser_elo_before INTEGER,
            winner_elo_after INTEGER,
            loser_elo_after INTEGER,
            match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (winner_id) REFERENCES movies (id),
            FOREIGN KEY (loser_id) REFERENCES movies (id)
        )
    ''')
    conn.commit()
    conn.close()

# ELO calculation
def calculate_elo(winner_elo, loser_elo, k=32):
    expected_winner = 1 / (1 + math.pow(10, (loser_elo - winner_elo) / 400))
    expected_loser = 1 / (1 + math.pow(10, (winner_elo - loser_elo) / 400))
    
    new_winner_elo = round(winner_elo + k * (1 - expected_winner))
    new_loser_elo = round(loser_elo + k * (0 - expected_loser))
    
    return new_winner_elo, new_loser_elo

# Routes
@app.route('/')
def home():
    return redirect(url_for('match'))

@app.route('/match')
def match():
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()

    # Determine if we should exclude the last shown pair
    c.execute('SELECT COUNT(*) FROM movies')
    total_movies = c.fetchone()[0]

    last_pair = session.get('last_pair')

    movies = []
    if total_movies >= 3 and last_pair and len(last_pair) == 2:
        # Try to fetch two random movies excluding the last shown pair
        c.execute(
            'SELECT id, name, image_url, elo_rating FROM movies WHERE id NOT IN (?, ?) ORDER BY RANDOM() LIMIT 2',
            (last_pair[0], last_pair[1])
        )
        movies = c.fetchall()

    if len(movies) < 2:
        # Fallback: fetch any two random movies
        c.execute('SELECT id, name, image_url, elo_rating FROM movies ORDER BY RANDOM() LIMIT 2')
        movies = c.fetchall()

    conn.close()

    if len(movies) < 2:
        return render_template('match.html', error="You need at least 2 movies to start matching!")

    # Store current pair to avoid repeating next time
    session['last_pair'] = [movies[0][0], movies[1][0]]

    return render_template('match.html', movies=movies)

@app.route('/vote', methods=['POST'])
def vote():
    winner_id = int(request.json['winner_id'])
    loser_id = int(request.json['loser_id'])
    
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    
    # Get current ELO ratings
    c.execute('SELECT elo_rating FROM movies WHERE id = ?', (winner_id,))
    winner_elo = c.fetchone()[0]
    c.execute('SELECT elo_rating FROM movies WHERE id = ?', (loser_id,))
    loser_elo = c.fetchone()[0]
    
    # Calculate new ELO ratings
    new_winner_elo, new_loser_elo = calculate_elo(winner_elo, loser_elo)
    
    # Update ELO ratings and match counts
    c.execute('UPDATE movies SET elo_rating = ?, matches_played = matches_played + 1 WHERE id = ?', 
              (new_winner_elo, winner_id))
    c.execute('UPDATE movies SET elo_rating = ?, matches_played = matches_played + 1 WHERE id = ?', 
              (new_loser_elo, loser_id))
    
    # Record the match
    c.execute('''INSERT INTO matches 
                 (winner_id, loser_id, winner_elo_before, loser_elo_before, winner_elo_after, loser_elo_after)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (winner_id, loser_id, winner_elo, loser_elo, new_winner_elo, new_loser_elo))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/tie', methods=['POST'])
def tie():
    movie_a_id = int(request.json['movie_a_id'])
    movie_b_id = int(request.json['movie_b_id'])

    conn = sqlite3.connect('movies.db')
    c = conn.cursor()

    # Get current ELO ratings
    c.execute('SELECT elo_rating FROM movies WHERE id = ?', (movie_a_id,))
    a_elo = c.fetchone()[0]
    c.execute('SELECT elo_rating FROM movies WHERE id = ?', (movie_b_id,))
    b_elo = c.fetchone()[0]

    # Treat as a draw: both get 0.5 score
    expected_a = 1 / (1 + math.pow(10, (b_elo - a_elo) / 400))
    expected_b = 1 / (1 + math.pow(10, (a_elo - b_elo) / 400))
    new_a_elo = round(a_elo + 32 * (0.5 - expected_a))
    new_b_elo = round(b_elo + 32 * (0.5 - expected_b))

    # Update both movies
    c.execute('UPDATE movies SET elo_rating = ?, matches_played = matches_played + 1 WHERE id = ?', (new_a_elo, movie_a_id))
    c.execute('UPDATE movies SET elo_rating = ?, matches_played = matches_played + 1 WHERE id = ?', (new_b_elo, movie_b_id))

    # Optionally record the tie as a match entry with both participants
    c.execute('''INSERT INTO matches 
                 (winner_id, loser_id, winner_elo_before, loser_elo_before, winner_elo_after, loser_elo_after)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (movie_a_id, movie_b_id, a_elo, b_elo, new_a_elo, new_b_elo))

    conn.commit()
    conn.close()

    return jsonify({'success': True})

@app.route('/skip', methods=['POST'])
def skip():
    # No rating updates; just acknowledge so the client can load a new pair
    return jsonify({'success': True})

@app.route('/see')
def leaderboard():
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('''SELECT id, name, image_url, elo_rating, matches_played 
                 FROM movies 
                 ORDER BY elo_rating DESC''')
    movies = c.fetchall()
    conn.close()
    
    return render_template('leaderboard.html', movies=movies)

@app.route('/new')
def add_movie_form():
    if not session.get('admin'):
        return redirect(url_for('login', next=url_for('add_movie_form')))
    return render_template('add_movie.html')

@app.route('/add', methods=['POST'])
def add_movie():
    if not session.get('admin'):
        return redirect(url_for('login', next=url_for('add_movie')))
    name = request.form['name']
    image_url = request.form['image_url']
    
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('INSERT INTO movies (name, image_url) VALUES (?, ?)', (name, image_url))
    conn.commit()
    conn.close()
    
    return redirect(url_for('leaderboard'))

@app.route('/delete/<int:movie_id>', methods=['POST'])
def delete_movie(movie_id):
    if not session.get('admin'):
        abort(403)
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('DELETE FROM matches WHERE winner_id = ? OR loser_id = ?', (movie_id, movie_id))
    c.execute('DELETE FROM movies WHERE id = ?', (movie_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('leaderboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or request.form.get('next') or url_for('leaderboard')
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        admin_pwd = os.environ.get('ADMIN_PASSWORD') or os.environ.get('ADD_MOVIE_PASSWORD')
        if admin_pwd and password == admin_pwd:
            session['admin'] = True
            return redirect(next_url)
        else:
            error = 'Invalid password'
    return render_template('login.html', error=error, next_url=next_url)

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('admin', None)
    return redirect(url_for('leaderboard'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
