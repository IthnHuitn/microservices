from flask import Flask, request, jsonify, Response
import io
import uuid
import os
from PIL import Image
from minio import Minio
from minio.error import S3Error
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# Свои метрики
REQUEST_COUNT = Counter('flask_http_request_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('flask_http_request_duration_seconds', 'Request duration', ['method', 'endpoint'])

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# Настройки MinIO
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'images')

minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)

try:
    if not minio_client.bucket_exists(MINIO_BUCKET):
        minio_client.make_bucket(MINIO_BUCKET)
except Exception as e:
    print(f"Error checking/creating bucket: {e}")

@app.route('/v1/upload', methods=['POST'])
def upload_file():
    try:
        if not request.data:
            REQUEST_COUNT.labels(method='POST', endpoint='/v1/upload', status='400').inc()
            return jsonify({'error': 'No file provided'}), 400
        
        try:
            img = Image.open(io.BytesIO(request.data))
            img_format = img.format.lower() if img.format else 'jpeg'
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95, optimize=True)
            output.seek(0)
            file_data = output.read()
            mime_type = 'image/jpeg'
            file_ext = 'jpg'
        except:
            file_data = request.data
            mime_type = request.content_type or 'application/octet-stream'
            file_ext = 'bin'
        
        filename = f"{str(uuid.uuid4())}.{file_ext}"
        
        minio_client.put_object(MINIO_BUCKET, filename, io.BytesIO(file_data), len(file_data), content_type=mime_type)
        
        REQUEST_COUNT.labels(method='POST', endpoint='/v1/upload', status='201').inc()
        return jsonify({'message': 'File uploaded successfully', 'filename': filename, 'url': f'/images/{filename}'}), 201
    except Exception as e:
        REQUEST_COUNT.labels(method='POST', endpoint='/v1/upload', status='500').inc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)