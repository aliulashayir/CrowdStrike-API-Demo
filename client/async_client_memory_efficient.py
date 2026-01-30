from dotenv import load_dotenv
import asyncio
import aiohttp
import os
import time
from elasticsearch import AsyncElasticsearch
import logging

load_dotenv()

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
ES_URL = os.getenv("ES_URL", "http://localhost:9200")

token = None
remaining_requests = 5000
retry_after_time = 0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_auth_token(session):
    global token
    
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    
    async with session.post(f"{BASE_URL}/oauth2/token/", data=data) as response:
        if response.status == 200:
            result = await response.json()
            token = result["access_token"]
            print("Token alindi")
            return token
        else:
            print(f"Token alinamadi: {response.status}")
            return None


async def check_rate_limit():
    global remaining_requests, retry_after_time
    
    if remaining_requests < 10:
        wait = retry_after_time - time.time()
        if wait > 0:
            print(f"Rate limit! {wait:.0f} saniye bekleniyor")
            await asyncio.sleep(wait)
            remaining_requests = 5000


async def make_request(session, method, url, params=None, json_data=None, retry_count=0):
    global remaining_requests, retry_after_time
    
    await check_rate_limit()
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        if method == "GET":
            async with session.get(url, params=params, headers=headers) as response:
                if "X-RateLimit-Remaining" in response.headers:
                    remaining_requests = int(response.headers["X-RateLimit-Remaining"])
                if "X-RateLimit-RetryAfter" in response.headers:
                    retry_after_time = int(response.headers["X-RateLimit-RetryAfter"])
                
                if response.status == 200:
                    return await response.json()
                elif response.status in [429, 500, 502, 503, 504]:
                    if retry_count < 3:
                        wait_time = (2 ** retry_count)
                        print(f"ERROR {response.status}, {wait_time} sn bekle")
                        await asyncio.sleep(wait_time)
                        return await make_request(session, method, url, params, json_data, retry_count + 1)
                    else:
                        print(f"Hata: {response.status}")
                        return None
                else:
                    print(f"Hata: {response.status}")
                    return None
        
        elif method == "POST":
            async with session.post(url, json=json_data, headers=headers) as response:
                if "X-RateLimit-Remaining" in response.headers:
                    remaining_requests = int(response.headers["X-RateLimit-Remaining"])
                if "X-RateLimit-RetryAfter" in response.headers:
                    retry_after_time = int(response.headers["X-RateLimit-RetryAfter"])
                
                if response.status == 200:
                    return await response.json()
                elif response.status in [429, 500, 502, 503, 504]:
                    if retry_count < 3:
                        wait_time = (2 ** retry_count)
                        print(f"ERROR {response.status}, {wait_time} sn bekle")
                        await asyncio.sleep(wait_time)
                        return await make_request(session, method, url, params, json_data, retry_count + 1)
                    else:
                        print(f"Hata: {response.status}")
                        return None
                else:
                    print(f"Hata: {response.status}")
                    return None
    
    except Exception as e:
        if retry_count < 3:
            wait_time = (2 ** retry_count)
            await asyncio.sleep(wait_time)
            return await make_request(session, method, url, params, json_data, retry_count + 1)
        else:
            print(f"ERROR {e}")
            return None


async def get_host_groups(session):
    """
    Group'lar az sayida oldugu icin hepsini RAM'de tutmak OK.
    Bunlar enrichment icin lazim.
    """
    print("Host groups cekiliyor")
    
    all_groups = []
    offset = 0
    limit = 10
    
    while True:
        url = f"{BASE_URL}/devices/host-groups/"
        params = {"limit": limit, "offset": offset}
        
        result = await make_request(session, "GET", url, params=params)
        
        if not result:
            break
        
        all_groups.extend(result["resources"])
        
        total = result["meta"]["pagination"]["total"]
        offset += limit
        
        if offset >= total:
            break
    
    # Dict'e cevir - hizli lookup icin
    group_dict = {}
    for group in all_groups:
        group_dict[group["id"]] = group
    
    print(f"{len(all_groups)} host group cekildi")
    return group_dict


async def get_device_ids_paginated(session):
    """
    Generator gibi calisiyor - her seferinde bir sayfa ID donuyor.
    Tum ID'leri RAM'de tutmuyor.
    """
    limit = 10
    offset = 0
    
    url = f"{BASE_URL}/devices/devices/"
    params = {"limit": limit, "offset": 0}
    first_page = await make_request(session, "GET", url, params=params)
    
    if not first_page:
        return
    
    total = first_page["meta"]["pagination"]["total"]
    
    # Ilk sayfanin ID'lerini don
    page_ids = []
    for device in first_page["resources"]:
        page_ids.append(device["device_id"])
    yield page_ids
    
    # Diger sayfalari don
    offset = limit
    while offset < total:
        params = {"limit": limit, "offset": offset}
        result = await make_request(session, "GET", url, params=params)
        
        if result:
            page_ids = []
            for device in result["resources"]:
                page_ids.append(device["device_id"])
            yield page_ids
        
        offset += limit


async def get_device_details_batch(session, device_ids):
    """
    Sadece verilen ID'lerin detaylarini ceker.
    """
    url = f"{BASE_URL}/devices/entities/"
    json_data = {"ids": device_ids}
    result = await make_request(session, "POST", url, json_data=json_data)
    
    if result:
        return result["resources"]
    return []


async def get_device_states_batch(session, device_ids):
    """
    Sadece verilen ID'lerin state'lerini ceker.
    """
    url = f"{BASE_URL}/devices/entities/online-state/"
    json_data = {"ids": device_ids}
    result = await make_request(session, "POST", url, json_data=json_data)
    
    if result:
        return result["resources"]
    return []


def enrich_devices(devices, states, group_dict):
    """
    Device'lara group ve state bilgisi ekler.
    """
    # State'leri dict'e cevir
    state_dict = {}
    for state in states:
        state_dict[state["id"]] = state.get("state")
    
    for device in devices:
        # Group bilgisi ekle
        device_groups = device.get("groups", [])
        group_info = []
        
        for group_id in device_groups:
            if group_id in group_dict:
                group_info.append(group_dict[group_id])
        
        group_info.sort(key=lambda x: x.get("name", ""))
        device["group_info"] = group_info
        
        # State bilgisi ekle
        device_id = device["device_id"]
        if device_id in state_dict:
            device["online_state"] = state_dict[device_id]
    
    return devices


async def save_batch_to_es(es, devices):
    """
    Sadece bu batch'i ES'e yazar.
    """
    for device in devices:
        await es.index(
            index="octoxlabs-data",
            id=device["device_id"],
            document=device
        )


async def log_to_es(es, level, message):
    try:
        log = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
        }
        await es.index(index="octoxlabs-log", document=log)
    except:
        pass


async def main():
    es = AsyncElasticsearch([ES_URL])
    
    try:
        async with aiohttp.ClientSession() as session:
            # 1. Token al
            print("\nToken aliniyor")
            await get_auth_token(session)
            await log_to_es(es, "INFO", "Token alindi")
            
            # 2. Group'lari cek ve dict olarak tut (az veri, OK)
            print()
            group_dict = await get_host_groups(session)
            await log_to_es(es, "INFO", f"{len(group_dict)} host group cekildi")
            
            # 3. Device ID'leri sayfa sayfa isle
            print("\nDevice'lar batch batch isleniyor (memory-efficient)")
            total_devices = 0
            seen_ids = set()  # Dedupe icin
            
            async for page_ids in get_device_ids_paginated(session):
                # Dedupe - daha once gordugumuz ID'leri atla
                new_ids = [id for id in page_ids if id not in seen_ids]
                seen_ids.update(new_ids)
                
                if not new_ids:
                    continue
                
                print(f"\n--- Batch: {len(new_ids)} device isleniyor ---")
                
                # Bu batch icin detaylari cek
                devices = await get_device_details_batch(session, new_ids)
                print(f"  {len(devices)} device detayi cekildi")
                
                # Bu batch icin state'leri cek
                states = await get_device_states_batch(session, new_ids)
                print(f"  {len(states)} device state cekildi")
                
                # Enrich et (group + state ekle)
                devices = enrich_devices(devices, states, group_dict)
                print(f"  Enrichment tamamlandi")
                
                # ES'e yaz
                await save_batch_to_es(es, devices)
                print(f"  ES'e kaydedildi")
                
                total_devices += len(devices)
                
                # !! ONEMLI: Bu batch'i RAM'den siliyoruz
                # devices ve states degiskenleri bir sonraki iterasyonda
                # yeni degerlerle uzerine yazilacak, eski veriler GC tarafindan silinecek
                
                await log_to_es(es, "INFO", f"Batch islendi: {len(devices)} device")
            
            print("\n" + "=" * 50)
            print("TAMAMLANDI (Memory-Efficient)")
            print(f"- {len(group_dict)} Host Group (RAM'de tutuldu - az veri)")
            print(f"- {total_devices} Device (batch batch islendi)")
            print(f"- {len(seen_ids)} Unique ID")
    
    except Exception as e:
        print(f"Hata: {e}")
        await log_to_es(es, "ERROR", f"Hata: {e}")
    
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
