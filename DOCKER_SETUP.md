# Docker Compose ile Çalıştırma

## Gereksinimler
- Docker
- Docker Compose

## Hızlı Başlangıç

### 1. Tüm servisleri başlat
```bash
docker-compose up --build
```

Bu komut şunları başlatır:
- **Elasticsearch** (port 9200)
- **Mock API** (Django, port 8000)
- **Client** (async script)
### 2. Sadece belirli servisleri başlat

#### Elasticsearch + API (client olmadan)
```bash
docker-compose up elasticsearch api
```

#### Client'ı manuel çalıştır (local)
```bash
cd client
python async_client.py
```

### 3. Test senaryolarını çalıştır
```bash
cd client
python test_scenarios.py
```

## Servisler

### Elasticsearch
- URL: http://localhost:9200
- Index'ler:
  - `octoxlabs-data` - Device verileri
  - `octoxlabs-log` - Log kayıtları

### Mock API
- URL: http://localhost:8000
- Endpoints:
  - `GET /health/` - Health check
  - `POST /oauth2/token/` - Token alma
  - `GET /devices/host-groups/` - Host groups
  - `GET /devices/devices/` - Device listesi
  - `POST /devices/entities/` - Device detayları
  - `POST /devices/entities/online-state/` - Device state'leri

### Client
- Otomatik olarak çalışır
- API'den veri çeker
- Elasticsearch'e kaydeder

## Test Modları

API'de test modları var (query parameter ile):

```bash
# Rate limit hit
curl "http://localhost:8000/devices/host-groups/?test_mode=rate_limit_hit"

# Server error
curl "http://localhost:8000/devices/host-groups/?test_mode=server_error"

# Slow response
curl "http://localhost:8000/devices/host-groups/?test_mode=slow_response"
```

## Elasticsearch Sorgulama

### Veriyi görüntüle
```bash
# Tüm device'ları listele
curl "http://localhost:9200/octoxlabs-data/_search?pretty"

# Log'ları listele
curl "http://localhost:9200/octoxlabs-log/_search?pretty"

# Belirli bir device'ı getir
curl "http://localhost:9200/octoxlabs-data/_doc/device_001?pretty"
```

## Temizlik

### Container'ları durdur
```bash
docker-compose down
```

### Container'ları + volume'leri sil
```bash
docker-compose down -v
```

### Elasticsearch verilerini sil
```bash
docker-compose down -v
docker volume rm octoxlabs_es_data
```

## Sorun Giderme

### Port zaten kullanımda
```bash
# Çalışan container'ları kontrol et
docker ps

# Belirli bir portu kullanan process'i bul
lsof -i :8000
lsof -i :9200
```

### Elasticsearch başlamıyor
```bash
# Log'ları kontrol et
docker-compose logs elasticsearch

# Memory ayarını düşür (docker-compose.yml'de)
ES_JAVA_OPTS=-Xms256m -Xmx256m
```

### Client hata veriyor
```bash
# Client log'larını kontrol et
docker-compose logs client

# Client'ı yeniden başlat
docker-compose restart client
```

## Manuel Kurulum (Docker olmadan)

### 1. Elasticsearch'i başlat
```bash
docker run -d --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.0
```

### 2. Django API'yi başlat
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata api/fixtures/test_data.json
python manage.py runserver
```

### 3. Client'ı çalıştır
```bash
cd client
pip install -r requirements.txt
python async_client.py
```
