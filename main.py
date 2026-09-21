from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Spor Toto'da yer alan ana liglerin ESPN kodları
LEAGUES = [
    "tur.1",  # Trendyol Süper Lig
    "tur.2",  # Trendyol 1. Lig
    "eng.1",  # İngiltere Premier League
    "eng.2",  # İngiltere Championship
    "ger.1",  # Almanya Bundesliga
    "esp.1",  # İspanya La Liga
    "ita.1"   # İtalya Serie A
]

@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    
    # Son 3 gün ve gelecek 2 günü kapsayacak tarih formatı (YYYYMMDD-YYYYMMDD)
    today = datetime.now()
    start_date = (today - timedelta(days=3)).strftime("%Y%m%d")
    end_date = (today + timedelta(days=2)).strftime("%Y%m%d")
    date_param = f"{start_date}-{end_date}"

    for league in LEAGUES:
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date_param}"
            response = requests.get(url, timeout=5)
            
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
        except Exception as e:
            continue

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
