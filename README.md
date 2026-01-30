# Security API Integration

CrowdStrike benzeri bir security API'si ile entegrasyon örneği. Mock API + async client + Elasticsearch pipeline.
Bu demoyu, gerçek API'nin sınırlamalarını aşmaya çalışırken hazırladım. Batching, concurrency and exponential backoff retry mekanizmalarını denemek istedim.


## Hızlı Başlangıç

Docker ve Docker Compose kurulu olmalı.

```bash
git clone https://github.com/yourusername/security-api-integration.git
cd security-api-integration
docker-compose up --build
```

Birkaç saniye bekle. Client otomatik çalışacak, API'den veri çekip Elasticsearch'e kaydedecek.

Sonuçları kontrol et:
```bash
curl "http://localhost:9200/octoxlabs-data/_count?pretty"
```

25 device görmen lazım.

## Ne Yapıyor?

İki ana parça var:

**Mock API (Django)** - Security vendor API'sini simüle ediyor:
- OAuth2 authentication (client credentials)
- Rate limiting header'ları (X-RateLimit-Remaining, X-RateLimit-RetryAfter)
- Pagination
- Test modları (hata simülasyonu için)

**Async Client (Python)** - API'den veri çeken script:
- Token alıyor
- Tüm device'ları pagination ile çekiyor
- Detayları batch halinde concurrent olarak alıyor
- Group bilgilerini ekliyor
- Elasticsearch'e kaydediyor

Rate limit'e takılırsa bekliyor, server error alırsa retry yapıyor (exponential backoff).

## API Endpoints

```
GET  /health/                         Health check
POST /oauth2/token/                   Token al
GET  /devices/host-groups/            Host group listesi
GET  /devices/devices/                Device ID listesi
POST /devices/entities/               Device detayları (batch)
POST /devices/entities/online-state/  Device state'leri (batch)
```

## Test Senaryoları

Hata durumlarını test etmek için:

```bash
cd client
python test_scenarios.py
```

Rate limit, server error, eksik ID gibi durumları simüle edip client'ın nasıl handle ettiğini gösteriyor.

API'de test modları var:
```bash
# Rate limit hit simülasyonu
curl "http://localhost:8000/devices/devices/?test_mode=rate_limit_hit"

# Server error simülasyonu
curl "http://localhost:8000/devices/devices/?test_mode=server_error"
```

## Proje Yapısı

```
api/
  models.py           HostGroup, Device, DeviceState modelleri
  views.py            API endpoint'leri
  paginators.py       Custom pagination (CrowdStrike formatı)
  middleware.py       Rate limit middleware
  management/commands/setup_oauth.py

client/
  async_client.py     Ana script
  test_scenarios.py   Test senaryoları

docker-compose.yml    Elasticsearch + API + Client
```

## Notlar

- OAuth2 credentials `.env` dosyasında, `setup_oauth` management command'ı ile otomatik oluşturuluyor
- Pagination formatı CrowdStrike API'sine benziyor (meta, errors, resources)
- Client batch size 10, concurrent request yapıyor
- Retry: 3 deneme, exponential backoff (2s, 4s, 8s)

## Teknolojiler

- Django 5.2, Django REST Framework
- django-oauth-toolkit
- Python asyncio, aiohttp
- Elasticsearch 8.11
- Docker

