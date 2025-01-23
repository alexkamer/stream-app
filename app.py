from flask import Flask, render_template, request, jsonify
import sqlite3
import httpx
from datetime import datetime, timedelta
import requests
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

# Route for serving the main stream page
@app.route('/stream', methods=['GET', 'POST'])
def stream():
    stream_name = request.form.get('stream_name', "1")
    game_name = request.form.get('game_name', "Unknown Game")
    game_url = request.form.get('game_url', "N/A")

    return render_template(
        'stream.html',
        selected_stream=stream_name,
        game_name=game_name,
        game_url=game_url
    )

@app.route('/player_boxscore', methods=['GET'])
def player_boxscore():
    stream_name = request.args.get('stream_name', "1")
    game_name = request.args.get('game_name', "Unknown Game")
    game_url = request.args.get('game_url', "N/A")
    date_today = datetime.today().strftime("%Y%m%d")

    # Extract sport type from the game_url
    sport_name = game_url.split('/')[0]
    player_data = []
    team_data = []

    if sport_name == 'nba':
        # Fetch NBA data
        away_team = game_name.split(' vs ')[0]
        home_team = game_name.split(' vs ')[1]
        day_scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?limit=1000&dates={date_today}"
        day_scoreboard_response = httpx.get(day_scoreboard_url, timeout=10)
        day_scoreboard_response.raise_for_status()

        day_scoreboard_data = day_scoreboard_response.json().get('events', [])
        for game in day_scoreboard_data:
            day_game_name = game.get('name', ' at ')
            game_away = day_game_name.split(' at ')[0]
            game_home = day_game_name.split(' at ')[1]

            if away_team in [game_away, game_home] or home_team in [game_away, game_home]:
                espn_game_id = game.get('id')
                espn_game_url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={espn_game_id}"
                espn_game_response = httpx.get(espn_game_url, timeout=10)
                espn_game_response.raise_for_status()

                espn_game_data = espn_game_response.json()
                full_boxscore_data = espn_game_data.get('boxscore', {})

                # Parse team data
                for team in full_boxscore_data.get('teams', []):
                    team_name = team.get('team', {}).get('displayName')
                    team_dict = {'Team': team_name}
                    for stat in team.get('statistics', []):
                        temp_label = stat.get('label')
                        if '%' in temp_label:
                            temp_label = stat.get('name')
                        team_dict[temp_label] = stat.get('displayValue')
                    team_data.append(team_dict)

                # Parse player data
                for team in full_boxscore_data.get('players', []):
                    team_name = team.get('team', {}).get('displayName')
                    player_statistics = team.get('statistics', [{}])[0]
                    stat_labels = player_statistics.get('names', [])
                    for player in player_statistics.get('athletes', []):
                        player_name = player.get('athlete', {}).get('displayName')
                        player_started = player.get('starter')
                        player_dict = {'Team': team_name, 'Name': player_name, 'IsStarter': player_started}
                        for i, stat in enumerate(player.get('stats', [])):
                            player_dict[stat_labels[i]] = stat
                        player_data.append(player_dict)


    # Add logic for other sports here (e.g., football)

    return jsonify({
        "sport": sport_name,  # Include sport type in the response
        "players": player_data,
        "teams": team_data
    })

if __name__ == '__main__':
    app.run(debug=True)
