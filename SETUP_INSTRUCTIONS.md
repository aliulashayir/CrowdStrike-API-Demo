# Octoxlabs Integration Case Study - Kurulum

## Hızlı Başlangıç (Docker Compose)

### Gereksinimler
- Docker
- Docker Compose

### Kurulum

1. **Zip dosyasını aç**
```bash
unzip octoxlabs-case-study.zip
cd case
```

2. **Tüm servisleri başlat**
```bash
docker-compose up --build
```

Bu komut:
- Elasticsearch'i başlatır (port 9200)
- Django Mock API'yi başlatır (port 8000)
- Async client'ı çalıştırır (veri çeker ve Elasticsearch'e kaydeder)

3. **Sonuçları kontrol et**
```bash
# Elasticsearch'te kaydedilen device sayısı
curl "http://localhost:9200/octoxlabs-data/_count?pretty"

# Tüm device'ları listele
curl "http://localhost:9200/octoxlabs-data/_search?pretty"

# Log'ları listele
curl "http://localhost:9200/octoxlabs-log/_search?pretty"
```

## Manuel Kurulum (Docker olmadan)

### 1. Elasticsearch'i başlat
```bash
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.11.0
```

### 2. Django API'yi başlat
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata api/fixtures/test_data.json

# OAuth2 Application oluştur (Django shell)
python manage.py shell
```

Django shell'de:
```python
from oauth2_provider.models import Application
from django.contrib.auth.models import User

# Admin user oluştur (yoksa)
user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')

# OAuth2 Application oluştur
app = Application.objects.create(
    name="Test Client",
    client_type=Application.CLIENT_CONFIDENTIAL,
    authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET"
)
print(f"Client ID: {app.client_id}")
print(f"Client Secret: {app.client_secret}")
```

`client/.env` dosyasını güncelle:
```
CLIENT_ID="YOUR_CLIENT_ID"
CLIENT_SECRET="YOUR_CLIENT_SECRET"
ES_URL="http://localhost:9200"
```

API'yi başlat:
```bash
python manage.py runserver
```

### 3. Client'ı çalıştır
```bash
cd client
pip install -r requirements.txt
python async_client.py
```

## Test Senaryoları

```bash
cd client
python test_scenarios.py
```

Test edilen senaryolar:
- Rate limit hit (Remaining=0)
- Server error + exponential backoff
- Eksik device ID'ler
- Rate limit bekleme mekanizması
- Concurrent requests

## API Endpoints

### Token Alma
```bash
curl -X POST http://localhost:8000/oauth2/token/ \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

### Host Groups
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/devices/host-groups/?limit=10&offset=0"
```

### Device Listesi
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/devices/devices/?limit=10&offset=0"
```

### Device Detayları
```bash
curl -X POST http://localhost:8000/devices/entities/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["device_001", "device_002"]}'
```

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

## Proje Yapısı

```
.
├── api/                    # Django REST API
│   ├── models.py          # HostGroup, Device, DeviceState
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # API endpoints
│   ├── paginators.py      # Custom pagination
│   ├── middleware.py      # Rate limit middleware
│   └── fixtures/          # Test data
├── client/                # Async client
│   ├── async_client.py    # Ana script
│   ├── test_scenarios.py  # Test senaryoları
│   └── .env              # Credentials
├── docker-compose.yml     # Docker Compose config
├── Dockerfile            # API Dockerfile
└── README.md             # Proje dokümantasyonu
```

## Özellikler

### Mock API
- OAuth2 authentication (client credentials flow)
- Rate limiting (X-RateLimit-Remaining, X-RateLimit-RetryAfter)
- Pagination (offset-based, max 500)
- 5 endpoint
- Test modları

### Async Client
- OAuth2 token yönetimi
- Rate limit kontrolü ve bekleme
- Exponential backoff (retry: 2s, 4s, 8s)
- Concurrent requests (asyncio.gather)
- Pagination ile tüm veriyi çekme
- ID dedupe
- Eksik ID tespiti ve retry
- Enrichment (group bilgilerini device'lara ekleme)
- Elasticsearch entegrasyonu (veri + log)

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

## Temizlik

```bash
# Container'ları durdur
docker-compose down

# Container'ları + volume'leri sil
docker-compose down -v
```

## İletişim

Sorularınız için: [email]
