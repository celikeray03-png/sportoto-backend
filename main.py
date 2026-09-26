import os, requests
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

MONTHS_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

def fetch_date_scores(date_str):
    matches = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/scoreboard?dates={date_str}&limit=300"
        response = requests.get(url, timeout=3.0)
        if response.status_code == 200:
            for event in response.json().get('events', []):
                comp = event['competitions'][0]
                teams = comp['competitors']
                
                match_time = "--:--"
                match_date = ""
                raw_date = event.get('date')
                if raw_date:
                    try:
                        dt = datetime.strptime(raw_date.split('.')[0].replace('Z', ''), "%Y-%m-%dT%H:%M") + timedelta(hours=3)
                        match_time = dt.strftime("%H:%M")
                        match_date = f"{dt.day} {MONTHS_TR.get(dt.month, '')}"
                    except Exception:
                        pass

                matches.append({
                    'home': teams[0]['team']['displayName'],
                    'away': teams[1]['team']['displayName'],
                    'homeScore': int(teams[0].get('score', 0)) if str(teams[0].get('score', 0)).isdigit() else 0,
                    'awayScore': int(teams[1].get('score', 0)) if str(teams[1].get('score', 0)).isdigit() else 0,
                    'status': 'FINISHED' if comp['status']['type']['state'] == 'post' else ('LIVE' if comp['status']['type']['state'] == 'in' else 'PENDING'),
                    'matchTime': match_time,
                    'matchDate': match_date
                })
    except Exception:
        pass
    return matches

@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    today = datetime.now()
    # Spor Toto bültenini kapsayacak şekilde: Dün + Bugün + Önümüzdeki 5 Gün (Toplam 7 Gün)
    date_list = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 6)]

    with ThreadPoolExecutor(max_workers=10) as executor:
        for res in executor.map(fetch_date_scores, date_list):
            all_matches.extend(res)

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
