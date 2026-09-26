import os, requests
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

MONTHS_TR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    today = datetime.now()
    
    # Dün + Bugün + Önümüzdeki 4 Günün tarih parametre dizisi (Tek adrese atılır)
    dates_param = ",".join([(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 5)])
    
    try:
        # TEK BİR İSTEKLE TÜM FUTBOL MAÇLARINI ÇEKİYORUZ
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/scoreboard?dates={dates_param}&limit=500"
        res = requests.get(url, timeout=4.0)
        
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

                all_matches.append({
                    'home': teams[0]['team']['displayName'],
                    'away': teams[1]['team']['displayName'],
                    'homeScore': int(teams[0].get('score', 0)) if str(teams[0].get('score', 0)).isdigit() else 0,
                    'awayScore': int(teams[1].get('score', 0)) if str(teams[1].get('score', 0)).isdigit() else 0,
                    'status': 'FINISHED' if state == 'post' else ('LIVE' if state == 'in' else 'PENDING'),
                    'matchTime': match_time,
                    'matchDate': match_date,
                    'matchMinute': match_minute
                })
    except Exception as e:
        print("Hata:", e)

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
