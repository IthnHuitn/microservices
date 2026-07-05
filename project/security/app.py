from flask import Flask, request, jsonify, Response
import jwt
import datetime
import uuid
from functools import wraps
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key-change-in-production'

# Свои метрики
REQUEST_COUNT = Counter('flask_http_request_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('flask_http_request_duration_seconds', 'Request duration', ['method', 'endpoint'])

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Временное хранилище пользователей
users_db = {}

@app.route('/v1/user', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        if not data or 'login' not in data or 'password' not in data:
            REQUEST_COUNT.labels(method='POST', endpoint='/v1/user', status='400').inc()
            return jsonify({'error': 'Login and password are required'}), 400
        
        login = data['login']
        password = data['password']
        
        if login in users_db:
            REQUEST_COUNT.labels(method='POST', endpoint='/v1/user', status='409').inc()
            return jsonify({'error': 'User already exists'}), 409
        
        user_id = str(uuid.uuid4())
        users_db[login] = {
            'id': user_id,
            'login': login,
            'password': password
        }
        
        REQUEST_COUNT.labels(method='POST', endpoint='/v1/user', status='201').inc()
        return jsonify({'message': 'User registered successfully', 'user_id': user_id}), 201
    except Exception as e:
        REQUEST_COUNT.labels(method='POST', endpoint='/v1/user', status='500').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/v1/user', methods=['GET'])
def get_user_info():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        REQUEST_COUNT.labels(method='GET', endpoint='/v1/user', status='401').inc()
        return jsonify({'message': 'Token is missing'}), 401
    
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user = users_db.get(data['sub'])
        if user:
            REQUEST_COUNT.labels(method='GET', endpoint='/v1/user', status='200').inc()
            return jsonify({'id': user['id'], 'login': user['login']}), 200
        REQUEST_COUNT.labels(method='GET', endpoint='/v1/user', status='404').inc()
        return jsonify({'error': 'User not found'}), 404
    except:
        REQUEST_COUNT.labels(method='GET', endpoint='/v1/user', status='401').inc()
        return jsonify({'message': 'Invalid token'}), 401

@app.route('/v1/token', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'login' not in data or 'password' not in data:
            REQUEST_COUNT.labels(method='POST', endpoint='/v1/token', status='400').inc()
            return jsonify({'error': 'Login and password are required'}), 400
        
        login = data['login']
        password = data['password']
        user = users_db.get(login)
        
        if not user or user['password'] != password:
            REQUEST_COUNT.labels(method='POST', endpoint='/v1/token', status='401').inc()
            return jsonify({'error': 'Invalid credentials'}), 401
        
        token = jwt.encode({
            'sub': login,
            'iat': datetime.datetime.utcnow(),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        REQUEST_COUNT.labels(method='POST', endpoint='/v1/token', status='200').inc()
        return jsonify({'token': token, 'token_type': 'Bearer', 'expires_in': 86400}), 200
    except Exception as e:
        REQUEST_COUNT.labels(method='POST', endpoint='/v1/token', status='500').inc()
        return jsonify({'error': str(e)}), 500

@app.route('/v1/token/validation', methods=['GET'])
def validate_token():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        REQUEST_COUNT.labels(method='GET', endpoint='/v1/token/validation', status='401').inc()
        return jsonify({'message': 'Token is missing'}), 401
    
    try:
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        REQUEST_COUNT.labels(method='GET', endpoint='/v1/token/validation', status='200').inc()
        return jsonify({'valid': True, 'user': data['sub'], 'message': 'Token is valid'}), 200
    except:
        REQUEST_COUNT.labels(method='GET', endpoint='/v1/token/validation', status='401').inc()
        return jsonify({'message': 'Invalid token'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)