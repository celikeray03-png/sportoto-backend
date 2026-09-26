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

# Sadece senin kuponunda geçen takımların olası İngilizce/Türkçe ad anahtarları
TARGET_TEAMS = [
    "turkey", "turkiye", "france", "fransa", "italy", "italya",
    "sweden", "isvec", "romania", "romanya", "belgium", "belcika",
    "slovenia", "slovenya", "scotland", "iskocya", "bulgaria", "bulgaristan",
    "luxembourg", "luksemburg", "north macedonia", "kuzey makedonya",
    "switzerland", "isvicre", "czechia", "czech republic", "cekya",
    "croatia", "hirvatistan", "england", "ingiltere", "spain", "ispanya",
    "lithuania", "litvanya", "azerbaijan", "azerbaycan", "austria", "avusturya",
    "kosovo", "kosova", "denmark", "danimarka", "wales", "galler",
    "serbia", "sirbistan", "netherlands", "hollanda", "germany", "almanya",
    "greece", "yunanistan", "norway", "norvec", "portugal", "portekiz"
]

def fetch_day_scores(date_str):
    matches = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/scoreboard?dates={date_str}&limit=400"
        res = requests.get(url, timeout=2.5)
        if res.status_code == 200:
            for event in res.json().get('events', []):
                comp = event['competitions'][0]
                teams = comp['competitors']
                
                h_name = teams[0]['team']['displayName'].lower()
                a_name = teams[1]['team']['displayName'].lower()
                
                # Sadece kuponumuzdaki takımlardan biri bu maçta geçiyorsa al
                is_relevant = any(t in h_name or t in a_name for t in TARGET_TEAMS)
                if not is_relevant:
                    continue

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
    
    # Dün + Bugün + Önümüzdeki 4 Gün (6 Günlük Tarama)
    date_list = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 5)]

    with ThreadPoolExecutor(max_workers=6) as executor:
        for res in executor.map(fetch_day_scores, date_list):
            all_matches.extend(res)

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
