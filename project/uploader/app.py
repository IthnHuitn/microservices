from flask import Flask, request, jsonify, Response
import requests
from PIL import Image
import io
import uuid
import os
from minio import Minio
from minio.error import S3Error

app = Flask(__name__)

# Настройки MinIO
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'images')
MINIO_SECURE = os.getenv('MINIO_SECURE', 'false').lower() == 'true'

# Инициализация клиента MinIO
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

# Создаем бакет, если его нет
try:
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
        print(f"Bucket '{MINIO_BUCKET}' created successfully")
    else:
        print(f"Bucket '{MINIO_BUCKET}' already exists")
except Exception as e:
    print(f"Error checking/creating bucket: {e}")

@app.route('/v1/upload', methods=['POST'])
def upload_file():
    """Загрузка файла"""
    try:
        if not request.data:
            return jsonify({'error': 'No file provided'}), 400
        
        if len(request.data) > 10 * 1024 * 1024:
            return jsonify({'error': 'File too large'}), 413
        
        # Определяем тип контента
        content_type = request.content_type or 'application/octet-stream'
        
        # Пытаемся определить, изображение ли это
        try:
            img = Image.open(io.BytesIO(request.data))
            img_format = img.format.lower() if img.format else 'jpeg'
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Сжимаем с высоким качеством
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95, optimize=True)
            output.seek(0)
            file_data = output.read()
            file_ext = 'jpg'
            mime_type = 'image/jpeg'
        except:
            # Не изображение — сохраняем как есть
            file_data = request.data
            file_ext = 'bin'
            mime_type = content_type
        
        # Генерируем уникальное имя файла
        filename = f"{str(uuid.uuid4())}.{file_ext}"
        
        # Загружаем в MinIO
        try:
            minio_client.put_object(
                MINIO_BUCKET,
                filename,
                io.BytesIO(file_data),
                len(file_data),
                content_type=mime_type
            )
            print(f"File '{filename}' uploaded successfully, size: {len(file_data)} bytes")
        except S3Error as e:
            print(f"MinIO upload error: {e}")
            return jsonify({'error': f'MinIO upload error: {str(e)}'}), 500
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': filename,
            'url': f'/images/{filename}'
        }), 201
        
    except Exception as e:
        app.logger.error(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)