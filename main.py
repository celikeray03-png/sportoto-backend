import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

ADMIN_PASSWORD = "admin"  # Admin şifreniz

# Aktif kupon verisi (Varsayılan boş)
ACTIVE_COUPON = {
    "title": "Spor Toto Kuponu",
    "matches_data": None
}

LEAGUES = [
    "tur.1", "tur.2", "uefa.nations", "fifa.friendly",
    "eng.1", "ger.1", "esp.1", "ita.1", "fra.1"
]

def fetch_league_date(args):
    league, date_str = args
    matches = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date_str}"
        response = requests.get(url, timeout=3.0)
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
                
                match_time = "--:--"
                raw_date = event.get('date')
                if raw_date:
                    try:
                        dt = datetime.strptime(raw_date, "%Y-%m-%dT%HZ")
                        dt_tr = dt + timedelta(hours=3)
                        match_time = dt_tr.strftime("%H:%M")
                    except Exception:
                        try:
                            dt = datetime.strptime(raw_date, "%Y-%m-%dT%H:%MZ")
                            dt_tr = dt + timedelta(hours=3)
                            match_time = dt_tr.strftime("%H:%M")
                        except Exception:
                            pass

                matches.append({
                    'home': home_team,
                    'away': away_team,
                    'homeScore': int(home_score) if str(home_score).isdigit() else 0,
                    'awayScore': int(away_score) if str(away_score).isdigit() else 0,
                    'status': status,
                    'matchTime': match_time
                })
    except Exception:
        pass
    return matches

@app.route('/api/coupon', methods=['GET'])
def get_coupon():
    return jsonify({'status': 'success', 'coupon': ACTIVE_COUPON})

@app.route('/api/admin/update-coupon', methods=['POST'])
def update_coupon():
    data = request.json or {}
    password = data.get('password')
    
    if password != ADMIN_PASSWORD:
        return jsonify({'status': 'error', 'message': 'Hatalı şifre!'}), 401
    
    ACTIVE_COUPON['title'] = data.get('title', 'Spor Toto Kuponu')
    ACTIVE_COUPON['matches_data'] = data.get('matches_data')
    
    return jsonify({'status': 'success', 'message': 'Kupon başarıyla güncellendi!'})

@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    today = datetime.now()
    date_list = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 6)]
    tasks = [(league, date_str) for league in LEAGUES for date_str in date_list]

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_league_date, tasks)
        for res in results:
            all_matches.extend(res)

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
