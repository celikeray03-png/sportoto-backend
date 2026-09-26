import os, requests
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

LEAGUES = [
    "tur.1", "tur.2", "uefa.nations", "fifa.friendly",
    "eng.1", "ger.1", "esp.1", "ita.1", "fra.1"
]

MONTHS_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

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
                status_obj = comp.get('status', {})
                
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

                # Canlı dakika bilgisi (Örn: "67'", "45+2'")
                display_clock = status_obj.get('displayClock', '')
                if display_clock and not display_clock.endswith("'"):
                    display_clock += "'"

                matches.append({
                    'home': teams[0]['team']['displayName'],
                    'away': teams[1]['team']['displayName'],
                    'homeScore': int(teams[0].get('score', 0)) if str(teams[0].get('score', 0)).isdigit() else 0,
                    'awayScore': int(teams[1].get('score', 0)) if str(teams[1].get('score', 0)).isdigit() else 0,
                    'status': 'FINISHED' if status_obj.get('type', {}).get('state') == 'post' else ('LIVE' if status_obj.get('type', {}).get('state') == 'in' else 'PENDING'),
                    'matchTime': match_time,
                    'matchDate': match_date,
                    'matchMinute': display_clock
                })
    except Exception:
        pass
    return matches

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
