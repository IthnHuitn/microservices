FROM openresty/openresty:alpine-fat

# Создаем необходимые директории
RUN mkdir -p /var/log/nginx
RUN mkdir -p /etc/nginx/scripts
RUN touch /var/log/nginx/error.log
RUN touch /var/log/nginx/access.log

# Копируем конфигурацию в правильную директорию OpenResty
COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf

EXPOSE 80