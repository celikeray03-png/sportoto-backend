import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)
CORS(app)

# Veritabanı Bağlantısı
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/postgres')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- VERİTABANI MODELLERİ ---
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default='user')

class Coupon(db.Model):
    __tablename__ = 'coupons'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    matches_data = db.Column(db.JSON, nullable=False)

class UserPermission(db.Model):
    __tablename__ = 'user_permissions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id', ondelete='CASCADE'))

LEAGUES = [
    "tur.1", "tur.2", "uefa.nations", "fifa.friendly",
    "eng.1", "ger.1", "esp.1", "ita.1", "fra.1"
]

def fetch_league_date(args):
    league, date_str = args
    matches = []
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={date_str}"
        response = requests.get(url, timeout=2.5)
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
                
                matches.append({
                    'home': home_team,
                    'away': away_team,
                    'homeScore': int(home_score) if str(home_score).isdigit() else 0,
                    'awayScore': int(away_score) if str(away_score).isdigit() else 0,
                    'status': status
                })
    except Exception:
        pass
    return matches

# --- API ENDPOINTLERİ ---

# 1. Kayıt Ol
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Kullanıcı adı ve şifre gereklidir.'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'Bu kullanıcı adı zaten alınmış.'}), 400

    new_user = User(username=username, password=password, role='user')
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Kayıt başarılı! Giriş yapabilirsiniz.', 'user': {'id': new_user.id, 'username': new_user.username, 'role': new_user.role}})

# 2. Giriş Yap
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip().lower()
    password = data.get('password', '').strip()

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({'status': 'error', 'message': 'Hatalı kullanıcı adı veya şifre.'}), 401

    return jsonify({
        'status': 'success',
        'user': {'id': user.id, 'username': user.username, 'role': user.role}
    })

# 3. Tüm Kullanıcıları Listele (Admin İçi)
@app.route('/api/users', methods=['GET'])
def get_users():
    users = User.query.filter(User.role != 'admin').all()
    user_list = [{'id': u.id, 'username': u.username} for u in users]
    return jsonify({'status': 'success', 'users': user_list})

# 4. Kupon Kaydet ve İzinleri Ata (Admin)
@app.route('/api/admin/save-coupon', methods=['POST'])
def save_coupon():
    data = request.json
    title = data.get('title', 'Spor Toto Kuponu')
    matches_data = data.get('matches_data')
    target_user_ids = data.get('user_ids', []) # Seçilen Kullanıcı ID'leri

    new_coupon = Coupon(title=title, matches_data=matches_data)
    db.session.add(new_coupon)
    db.session.commit()

    # İzinleri Ekle
    for uid in target_user_ids:
        perm = UserPermission(user_id=uid, coupon_id=new_coupon.id)
        db.session.add(perm)
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Kupon başarıyla oluşturuldu ve seçilen kişilere tanımlandı.'})

# 5. Kullanıcıya Özel Kuponları Getir
@app.route('/api/user/coupons/<int:user_id>', methods=['GET'])
def get_user_coupons(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'error', 'message': 'Kullanıcı bulunamadı.'}), 404

    if user.role == 'admin':
        # Admin tüm kuponları görür
        coupons = Coupon.query.order_by(Coupon.id.desc()).all()
    else:
        # Normal kullanıcı sadece yetkisi olanları görür
        perms = UserPermission.query.filter_by(user_id=user_id).all()
        coupon_ids = [p.coupon_id for p in perms]
        coupons = Coupon.query.filter(Coupon.id.in_(coupon_ids)).order_by(Coupon.id.desc()).all()

    result = [{'id': c.id, 'title': c.title, 'matches_data': c.matches_data} for c in coupons]
    return jsonify({'status': 'success', 'coupons': result})

# 6. Canlı Skorları Çek
@app.route('/api/scores', methods=['GET'])
def get_scores():
    all_matches = []
    today = datetime.now()
    date_list = [(today + timedelta(days=i)).strftime("%Y%m%d") for i in range(-1, 6)]
    tasks = [(league, date_str) for league in LEAGUES for date_str in date_list]

    with ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_league_date, tasks)
        for res in results:
            all_matches.extend(res)

    return jsonify({'status': 'success', 'matches': all_matches})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
