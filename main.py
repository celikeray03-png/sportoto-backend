import os, requests
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Bülten maçlarının olduğu temel ligler
LEAGUES = [
    "uefa.nations", "fifa.friendly", "tur.1", "tur.2",
    "eng.1", "ger.1", "esp.1", "ita.1", "fra.1"
]

MONTHS_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

def fetch_single_league_date(args):
    league, date_str = args
    matches = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date_str}"
        res = requests.get(url, timeout=2.5)
        if res.status_code == 200:
            for event in res.json().get('events', []):
                comp = event['competitions'][0]
                teams = comp['competitors']
                status_obj = comp.get('status', {})
                status_type = status_obj.get('type', {})
                state = status_type.get('state', '')
                
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

                display_clock = status_obj.get('displayClock', '')
                short_detail = status_type.get('shortDetail', '')
                
                match_minute = ""
                if state == 'in':
                    if display_clock and display_clock != '0:00':
                        match_minute = f"{display_clock}'"
                    elif short_detail and "'" in short_detail:
                        match_minute = short_detail
                    else:
                        match_minute = "Canlı"

                matches.append({
                    'home': teams[0]['team']['displayName'],
                    'away': teams[1]['team']['displayName'],
                    'homeScore': int(teams[0].get('score', 0)) if str(teams[0].get('score', 0)).isdigit() else 0,
                    'awayScore': int(teams[1].get('score', 0)) if str(teams[1].get('score', 0)).isdigit() else 0,
                    'status': 'FINISHED' if state == 'post' else ('LIVE' if state == 'in' else 'PENDING'),
                    'matchTime': match_time,
                    'matchDate': match_date,
                    'matchMinute': match_minute
                })
    except Exception:
        pass
    return matches

@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    today = datetime.now()
    
    # Dün + Bugün + Önümüzdeki 4 Gün (Toplam 6 Gün)
    date_list = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 5)]
    tasks = [(league, d) for league in LEAGUES for d in date_list]

    # ThreadPoolExecutor ile paralel sorgulama yapıp süreyi kısa tutuyoruz
    with ThreadPoolExecutor(max_workers=20) as executor:
        for res in executor.map(fetch_single_league_date, tasks):
            all_matches.extend(res)

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
