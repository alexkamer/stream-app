from flask import Flask, render_template, request
import sqlite3

app = Flask(__name__)

# Helper function to fetch unique sports
def get_sports():
    conn = sqlite3.connect('boxStreams.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT sport FROM boxStreams ORDER BY sport")
    sports = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sports

# Helper function to get live streams filtered by sport
def get_live_streams(sport=None):
    conn = sqlite3.connect('boxStreams.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if sport:
        cursor.execute("SELECT * FROM boxStreams WHERE sport = ? ORDER BY start_date, start_time", (sport,))
    else:
        cursor.execute("SELECT * FROM boxStreams ORDER BY start_date, start_time")
    streams = cursor.fetchall()
    conn.close()
    return streams

@app.route('/')
def index():
    sport = request.args.get('sport')
    sports = get_sports()
    streams = get_live_streams(sport)
    return render_template('index.html', sports=sports, streams=streams, selected_sport=sport)

@app.route('/stream', methods=['POST'])
def stream():
    game_name = request.form['game_name']  # Retrieve the game name from the form submission
    game_url = request.form['game_url']
    return render_template('stream.html', game_name=game_name, game_url=game_url)

if __name__ == '__main__':
    app.run(debug=True)
