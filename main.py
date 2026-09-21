from flask import Flask, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

@app.route('/api/scores', methods=['GET'])
def get_scores():
    try:
        # ESPN API'sinden tüm futbol maç verilerini çekiyoruz
        response = requests.get(
            "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard",
            timeout=10
        )
        data = response.json()
        
        matches = []
        for event in data.get('events', []):
            competition = event['competitions'][0]
            competitors = competition['competitors']
            
            # Ev sahibi ve deplasman takımları
            home_team = competitors[0]['team']['displayName']
            away_team = competitors[1]['team']['displayName']
            
            home_score = competitors[0].get('score', '0')
            away_score = competitors[1].get('score', '0')
            
            status_state = competition['status']['type']['state'] # 'pre', 'in', 'post'
            
            # Durum haritalama: 'post' -> FINISHED, 'in' -> LIVE, 'pre' -> PENDING
            status = 'PENDING'
            if status_state == 'post':
                status = 'FINISHED'
            elif status_state == 'in':
                status = 'LIVE'
                
            matches.append({
                'home': home_team,
                'away': away_team,
                'homeScore': int(home_score) if str(home_score).isdigit() else 0,
                'awayScore': int(away_score) if str(away_score).isdigit() else 0,
                'status': status
            })
            
        return jsonify({'status': 'success', 'matches': matches})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
