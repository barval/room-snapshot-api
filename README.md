# Room Snapshot API

API для получения снимков комнат с камер видеонаблюдения (версия: 1.0)  
  
1. Запрос списка комнат (GET /rooms)  
URL: http://your-server-ip:5005/rooms  
  
2. Запрос снимка комнаты (GET /snapshot/{room})  
URL: http://your-server-ip:5005/snapshot/{room_code}  
  
Список комнат и кодов комнат (задаётся в config/cameras.conf):  
- Спальня/spa  
- Гостиная/gos  
- Кабинет/kab  
- Прихожая/pri  
- Кухня/kuh  
- Детская/det  
- Тамбур/tam  
- Коридор/kor  
- Балкон/bal  
  
Логин/пароль к камерам задаётся в файле .env в формате:  
```
RTSP_AUTH=login:password
```
  
## Требования
- доступ в Интернет  
- доступ к камерам видеонаблюдения  
- заполненные файлы .env, cameras.conf  

## Использование
Необходимо заполнить параметры и запустить docker-compose  
  
Получить список комнат:  
```
curl http://localhost:5005/rooms  
```
  
Получить снимок комнаты:  
```
curl http://localhost:5005/snapshot/gos -o gos.jpg
```