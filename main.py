from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Ortak kupon hafızası (Geçici bulut belleği)
shared_coupon_data = None

LEAGUES = [
    "tur.1",        # Trendyol Süper Lig
    "tur.2",        # Trendyol 1. Lig
    "uefa.nations", # UEFA Uluslar Ligi
    "fifa.friendly",# Hazırlık / Milli Maçlar
    "eng.1",        # Premier League
    "ger.1",        # Bundesliga
    "esp.1",        # La Liga
    "ita.1",        # Serie A
    "fra.1",        # Fransa Ligue 1
    "fra.2"         # Fransa Ligue 2
]

@app.route('/api/coupon', methods=['GET', 'POST'])
def handle_coupon():
    global shared_coupon_data
    if request.method == 'POST':
        shared_coupon_data = request.json
        return jsonify({'status': 'success', 'message': 'Kupon ortak belleğe kaydedildi'})
    else:
        return jsonify({'status': 'success', 'coupon': shared_coupon_data})

@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    today = datetime.now()
    date_list = [(today - timedelta(days=i)).strftime("%Y%m%d") for i in range(5)]

    for league in LEAGUES:
        for date_str in date_list:
            try:
                url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date_str}"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    for event in data.get('events', []):
                        comp = event['competitions'][0]
                        teams = comp['competitors']
                        home_team = teams[0]['team']['displayName']
                        away_team = teams[1]['team']['displayName']
                        home_score = teams[0].get('score', '0')
                        away_score = teams[1].get('score', '0')
                        status_state = comp['status']['type']['state']
                        status = 'FINISHED' if status_state == 'post' else ('LIVE' if status_state == 'in' else 'PENDING')
                        
                        all_matches.append({
                            'home': home_team,
                            'away': away_team,
                            'homeScore': int(home_score) if str(home_score).isdigit() else 0,
                            'awayScore': int(away_score) if str(away_score).isdigit() else 0,
                            'status': status
                        })
            except Exception:
                continue

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
