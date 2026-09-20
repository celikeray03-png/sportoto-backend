from flask import Flask, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # CORS engellerini kaldırır

@app.route('/api/scores', methods=['GET'])
def get_scores():
    # Canlı maç sonuçlarını ve durumlarını dönen API endpoint'i
    try:
        # Örnek canlı skor API entegrasyonu (TheSportsDB / LiveScore / FotMob vb.)
        # Gerçek canlı veri feed'i bağlandığında anlık güncellenir
        response = requests.get("https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard")
        data = response.json()
        
        matches = []
        for event in data.get('events', []):
            competition = event['competitions'][0]
            competitors = competition['competitors']
            
            home_team = competitors[0]['team']['displayName']
            away_team = competitors[1]['team']['displayName']
            home_score = competitors[0].get('score', '0')
            away_score = competitors[1].get('score', '0')
            
            status = competition['status']['type']['state']  # 'pre', 'in', 'post'
            
            matches.append({
                'home': home_team,
                'away': away_team,
                'homeScore': int(home_score) if home_score.isdigit() else 0,
                'awayScore': int(away_score) if away_score.isdigit() else 0,
                'status': 'LIVE' if status == 'in' else ('FINISHED' if status == 'post' else 'PENDING')
            })
            
        return jsonify({'status': 'success', 'matches': matches})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)