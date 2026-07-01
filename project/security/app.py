from flask import Flask, request, jsonify
import jwt
import datetime
import uuid
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key-change-in-production'

# Временное хранилище пользователей (в продакшене - база данных)
users_db = {}
tokens_db = {}

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/v1/user', methods=['POST'])
def register_user():
    """Регистрация нового пользователя"""
    try:
        data = request.get_json()
        
        if not data or 'login' not in data or 'password' not in data:
            return jsonify({'error': 'Login and password are required'}), 400
        
        login = data['login']
        password = data['password']
        
        if login in users_db:
            return jsonify({'error': 'User already exists'}), 409
        
        user_id = str(uuid.uuid4())
        users_db[login] = {
            'id': user_id,
            'login': login,
            'password': password  # В реальном приложении нужно хешировать
        }
        
        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/v1/user', methods=['GET'])
@token_required
def get_user_info(current_user):
    """Получение информации о пользователе"""
    user = users_db.get(current_user)
    if user:
        return jsonify({
            'id': user['id'],
            'login': user['login']
        }), 200
    return jsonify({'error': 'User not found'}), 404

@app.route('/v1/token', methods=['POST'])
def login():
    """Авторизация и получение токена"""
    try:
        data = request.get_json()
        
        if not data or 'login' not in data or 'password' not in data:
            return jsonify({'error': 'Login and password are required'}), 400
        
        login = data['login']
        password = data['password']
        
        user = users_db.get(login)
        if not user or user['password'] != password:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Создаем JWT токен
        token = jwt.encode({
            'sub': login,
            'iat': datetime.datetime.utcnow(),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        # Сохраняем токен
        tokens_db[login] = token
        
        return jsonify({
            'token': token,
            'token_type': 'Bearer',
            'expires_in': 86400
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/v1/token/validation', methods=['GET'])
@token_required
def validate_token(current_user):
    """Проверка валидности токена"""
    return jsonify({
        'valid': True,
        'user': current_user,
        'message': 'Token is valid'
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'security'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)