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

# Route for fetching player boxscore data
@app.route('/player_boxscore', methods=['GET'])
def player_boxscore():
    # Example API call (replace with your API endpoint)
    # Replace with the actual API URL and authentication details
    # api_url = "https://api.example.com/player-boxscore"
    # response = requests.get(api_url)

    # # Assuming the API response is a list of players with stats
    # if response.status_code == 200:
    #     data = response.json()
    # else:
    #     # Return sample data if API fails (for testing)
    #     data = [
    #         {"name": "Player 1", "points": 24, "rebounds": 10, "assists": 5},
    #         {"name": "Player 2", "points": 18, "rebounds": 7, "assists": 8},
    #         {"name": "Player 3", "points": 12, "rebounds": 5, "assists": 2},
    #     ]
    stream_name = request.args.get('stream_name', "1")
    game_name = request.args.get('game_name', "Unknown Game")
    game_url = request.args.get('game_url', "N/A")
    date_today = datetime.today().strftime("%Y%m%d")
    date_today = "20250121"
    print(date_today)
    sport_name = game_url.split('/')[0]
    if sport_name == 'nba':
        away_team = game_name.split(' vs ')[0]
        home_team = game_name.split(' vs ')[1]
        day_scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?limit=1000&dates={date_today}"
        day_scoreboard_response = httpx.get(day_scoreboard_url,timeout=10)
        day_scoreboard_response.raise_for_status()
        try:
            day_scoreboard_data = day_scoreboard_response.json().get('events',[])
            for game in day_scoreboard_data:
                day_game_name = game.get('name',' at ')
                game_away = day_game_name.split(' at ')[0]
                game_home = day_game_name.split(' at ')[1]

                if away_team in [game_away, game_home] or home_team in [game_away, game_home]:
                    espn_game_id = game.get('id')
                    espn_game_url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={espn_game_id}"
                    espn_game_response = httpx.get(espn_game_url,timeout=10)
                    espn_game_response.raise_for_status()
                    try:

                        espn_game_data = espn_game_response.json()
                        full_boxscore_data = espn_game_data.get('boxscore',{})
                        team_data = []
                        player_data = []
                        for team in full_boxscore_data.get('teams',[]):
                            team_name = team.get('team',{}).get('displayName')
                            team_dict = {}
                            team_dict['Team'] = team_name
                            for stat in team.get('statistics',[]):
                                temp_label = stat.get('label')
                                # if temp_label == 'FG':
                                #     team_dict['FGM'] = stat.get('displayValue')
                                # elif temp_label == '3PT'
                                if '%' in temp_label:
                                    temp_label = stat.get('name')
                                if '3' in temp_label:
                                    temp_label = "threePointers"
                                if ' ' in temp_label:
                                    temp_label = ''.join(temp_label.split(' '))

                                team_dict[temp_label] = stat.get('displayValue')
                            team_data.append(team_dict)

                        for team in full_boxscore_data.get('players',[]):
                            team_name = team.get('team',{}).get('displayName')
                            player_statistics = team.get('statistics',[{}])[0]
                            stat_labels = player_statistics.get('names',[])
                            for player in player_statistics.get('athletes',[]):
                                player_name = player.get('athlete',{}).get('displayName')
                                player_short_name = player.get('athlete',{}).get('shortName')
                                player_started = player.get('starter')
                                player_dict = {
                                    'Team' : team_name,
                                    'Name' : player_name,
                                    'IsStarter' : player_started
                                }
                                for i, stat in enumerate(player.get('stats',[])):
                                    if stat_labels[i] == '+/-':
                                        player_dict['plusMinus'] = stat
                                    if '3' in stat_labels[i]:
                                        player_dict['threePT'] = stat
                                    else:   
                                        player_dict[stat_labels[i]] = stat
                                player_data.append(player_dict)

                    except:
                        player_data = []
                        team_data = []
                    
            

            print(espn_game_id)                    

        except:
            player_data = []
            team_data = []
        print(game_name)
    else:
        player_data = []
        team_data = []
    return jsonify({"players": player_data, "teams": team_data})


if __name__ == '__main__':
    app.run(debug=True)
