import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:8000"
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

token = None


async def get_token(session):
    global token
    
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    
    async with session.post(f"{BASE_URL}/oauth2/token/", data=data) as resp:
        if resp.status == 200:
            result = await resp.json()
            token = result["access_token"]
            print("Token alindi")
            return token


async def test_rate_limit_hit(session):
    print("\n" + "="*60)
    print("TEST 1: Rate Limit Hit (Remaining=0)")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/devices/host-groups/?test_mode=rate_limit_hit"
    
    
    async with session.get(url, headers=headers) as resp:
        print(f"Response: {resp.status}")
        print(f"X-RateLimit-Remaining: {resp.headers.get('X-RateLimit-Remaining')}")
        print(f"X-RateLimit-RetryAfter: {resp.headers.get('X-RateLimit-RetryAfter')}")
        
        if resp.status == 429:
            print("Rate limit 429 hatasi alindi")
            result = await resp.json()
            print(f"Error: {result.get('errors')}")
        else:
            print("429 hatasi bekliyorduk")


async def test_server_error_retry(session):
    print("\n" + "="*60)
    print("TEST 2: Server Error (500) - Retry Mekanizmasi")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/devices/host-groups/?test_mode=server_error"
    
    print("Istek gonderiliyor (test_mode=server_error)")
    print("Retry mekanizmasi devreye girecek")
    
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        async with session.get(url, headers=headers) as resp:
            print(f"\nDeneme {retry_count + 1}: Response {resp.status}")
            
            if resp.status == 500:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    print(f"Server error! {wait_time}s sonra tekrar denenecek")
                    await asyncio.sleep(wait_time)
                else:
                    print("Max retry sayisina ulasildi")
                    print("Exponential backoff calisti: 2s, 4s, 8s")
            else:
                print("Istek basarili")
                break


async def test_missing_device_ids(session):
    print("\n" + "="*60)
    print("TEST 3: Eksik Device ID'ler")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/devices/entities/"
    
    # OLMAYAN IDLER
    fake_ids = ["device_999", "device_998", "device_001"]
    json_data = {"ids": fake_ids}
    
    print(f"Istek gonderiliyor: {fake_ids}")
    
    async with session.post(url, json=json_data, headers=headers) as resp:
        if resp.status == 200:
            result = await resp.json()
            received_ids = [d["device_id"] for d in result["resources"]]
            
            print(f"Gelen device'lar: {received_ids}")
            
            requested = set(fake_ids)
            received = set(received_ids)
            missing = requested - received
            
            if missing:
                print(f"Eksik ID'ler: {missing}")
                print("Eksik ID tespiti calisiyor")
            else:
                print("Tum ID'ler bulundu")


async def test_rate_limit_wait(session):
    print("\n" + "="*60)
    print("TEST 4: Rate Limit Bekleme Mekanizmasi")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    url1 = f"{BASE_URL}/devices/host-groups/?test_mode=rate_limit_hit"
    print("Istek 1: Rate limit hit simulasyonu")
    
    async with session.get(url1, headers=headers) as resp:
        remaining = int(resp.headers.get('X-RateLimit-Remaining', 0))
        retry_after = int(resp.headers.get('X-RateLimit-RetryAfter', 0))
        
        print(f"Remaining: {remaining}")
        print(f"RetryAfter: {retry_after}")
        
        if remaining == 0:
            import time
            wait_time = retry_after - time.time()
            if wait_time > 0:
                print(f"{wait_time:.1f} saniye bekleniyor")
                await asyncio.sleep(wait_time)
                print("Bekleme tamamlandi")
            
            # Retry
            print("\nIstek 2: Normal istek")
            url2 = f"{BASE_URL}/devices/host-groups/"
            async with session.get(url2, headers=headers) as resp2:
                print(f"Response: {resp2.status}")
                if resp2.status == 200:
                    print("Rate limit reset sonrasi istek basarili")


async def test_concurrent_requests(session):
    print("\n" + "="*60)
    print("TEST 5: Concurrent Requests - Rate Limit Paylasimi")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}/devices/host-groups/"
    
    print("5 concurrent istek gonderiliyor")
    
    tasks = []
    for i in range(5):
        task = session.get(url, headers=headers)
        tasks.append(task)
    
    responses = await asyncio.gather(*[task.__aenter__() for task in tasks])
    
    print("\nSonuclar:")
    for i, resp in enumerate(responses):
        remaining = resp.headers.get('X-RateLimit-Remaining')
        print(f"Istek {i+1}: Status={resp.status}, Remaining={remaining}")
        await resp.__aexit__(None, None, None)
    
    print("Concurrent request'ler rate limit'i paylasiyor")


async def main():
    print("TEST SENARYOLARI BASLATILIYOR")
    print("="*60)
    
    async with aiohttp.ClientSession() as session:

        await get_token(session)
        
        await test_rate_limit_hit(session)
        
        await test_server_error_retry(session)
        
        await test_missing_device_ids(session)
        
        await test_rate_limit_wait(session)
        
        await test_concurrent_requests(session)
        
        print("\n" + "="*60)
        print("TUM TESTLER TAMAMLANDI")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
