from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app)

shared_coupon_data = None

# Sadece Spor Toto bülteninde olan ana kategoriler
LEAGUES = [
    "tur.1",          # Süper Lig
    "tur.2",          # 1. Lig
    "uefa.nations",   # UEFA Uluslar Ligi
    "fifa.friendly",  # Hazırlık / Milli
    "eng.1",          # Premier League
    "ger.1",          # Bundesliga
    "esp.1",          # La Liga
    "ita.1",          # Serie A
    "fra.1"           # Ligue 1
]

def fetch_league_date(args):
    league, date_str = args
    matches = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date_str}"
        response = requests.get(url, timeout=2)
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
                
                matches.append({
                    'home': home_team,
                    'away': away_team,
                    'homeScore': int(home_score) if str(home_score).isdigit() else 0,
                    'awayScore': int(away_score) if str(away_score).isdigit() else 0,
                    'status': status
                })
    except Exception:
        pass
    return matches

@app.route('/api/coupon', methods=['GET', 'POST'])
def handle_coupon():
    global shared_coupon_data
    if request.method == 'POST':
        shared_coupon_data = request.json
        return jsonify({'status': 'success', 'message': 'Kupon kaydedildi'})
    else:
        return jsonify({'status': 'success', 'coupon': shared_coupon_data})

@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    today = datetime.now()
    
    # Bugün, dün, yarın ve gelecek 5 gün
    date_list = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 6)]

    # Sorgu parametrelerini oluştur
    tasks = [(league, date_str) for league in LEAGUES for date_str in date_list]

    # İstekleri paralel (saniyeler içinde) çalıştır
    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_league_date, tasks)
        for res in results:
            all_matches.extend(res)

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
