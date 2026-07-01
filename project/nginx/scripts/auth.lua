-- Файл: /etc/nginx/scripts/auth.lua
-- Упрощенная версия без внешних зависимостей

-- Получаем токен из заголовка Authorization
local auth_header = ngx.var.http_authorization

-- Проверяем наличие токена
if not auth_header then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header["Content-Type"] = "application/json"
    ngx.say('{"error": "Authorization header is missing"}')
    ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

-- Используем встроенный модуль для HTTP запроса
local res = ngx.location.capture("/internal/auth/validate", {
    method = ngx.HTTP_GET,
    body = "",
    args = {},
    ctx = function()
        ngx.req.set_header("Authorization", auth_header)
    end
})

-- Проверяем ответ от сервиса
if res.status ~= 200 then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header["Content-Type"] = "application/json"
    ngx.say('{"error": "Invalid or expired token"}')
    ngx.exit(ngx.HTTP_UNAUTHORIZED)
end
