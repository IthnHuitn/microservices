#!/bin/bash
set -e

echo "Waiting for Elasticsearch..."
until curl -s -u elastic:qwerty123456 http://elasticsearch:9200 > /dev/null; do
    sleep 2
done

echo "Setting kibana_system password..."
curl -s -X POST \
    -u elastic:qwerty123456 \
    -H "Content-Type: application/json" \
    -d '{"password":"qwerty123456"}' \
    http://elasticsearch:9200/_security/user/kibana_system/_password

echo "Creating admin user..."
curl -s -X POST \
    -u elastic:qwerty123456 \
    -H "Content-Type: application/json" \
    -d '{"password":"qwerty123456","roles":["superuser"],"full_name":"Admin User","email":"admin@example.com"}' \
    http://elasticsearch:9200/_security/user/admin

echo "Users created successfully!"