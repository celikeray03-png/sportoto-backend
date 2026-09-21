from flask import Flask, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Spor Toto'da yer alan tüm ana ligler
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
    
    # Son 4 gün ve bugünü kapsayan tekil gün listesi
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
                        
                        # Takım isimleri (Ev / Deplasman)
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
