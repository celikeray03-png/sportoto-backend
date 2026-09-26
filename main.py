import os, json, requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

ADMIN_PASSWORD = "admin"
FILE_PATH = "coupon.json"

def get_saved_coupon():
    if os.path.exists(FILE_PATH):
        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"title": "Spor Toto Kuponu", "matches_data": None}

def save_coupon_to_file(data):
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

LEAGUES = ["tur.1", "tur.2", "uefa.nations", "fifa.friendly", "eng.1", "ger.1", "esp.1", "ita.1", "fra.1"]

def fetch_league_date(args):
    league, date_str = args
    matches = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date_str}"
        response = requests.get(url, timeout=3.0)
        if response.status_code == 200:
            for event in response.json().get('events', []):
                comp = event['competitions'][0]
                teams = comp['competitors']
                matches.append({
                    'home': teams[0]['team']['displayName'],
                    'away': teams[1]['team']['displayName'],
                    'homeScore': int(teams[0].get('score', 0)) if str(teams[0].get('score', 0)).isdigit() else 0,
                    'awayScore': int(teams[1].get('score', 0)) if str(teams[1].get('score', 0)).isdigit() else 0,
                    'status': 'FINISHED' if comp['status']['type']['state'] == 'post' else ('LIVE' if comp['status']['type']['state'] == 'in' else 'PENDING')
                })
    except Exception:
        pass
    return matches

@app.route('/api/coupon', methods=['GET'])
def get_coupon():
    return jsonify({'status': 'success', 'coupon': get_saved_coupon()})

@app.route('/api/admin/update-coupon', methods=['POST'])
def update_coupon():
    data = request.json or {}
    if data.get('password') != ADMIN_PASSWORD:
        return jsonify({'status': 'error', 'message': 'Hatalı şifre!'}), 401
    
    coupon_data = {
        "title": data.get('title', 'Spor Toto Kuponu'),
        "matches_data": data.get('matches_data')
    }
    save_coupon_to_file(coupon_data)
    return jsonify({'status': 'success', 'message': 'Kupon başarıyla kaydedildi!'})

@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    today = datetime.now()
    date_list = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 6)]
    tasks = [(league, d) for league in LEAGUES for d in date_list]

    with ThreadPoolExecutor(max_workers=15) as executor:
        for res in executor.map(fetch_league_date, tasks):
            all_matches.extend(res)

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
