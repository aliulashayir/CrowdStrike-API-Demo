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
    
    print(f"{len(all_groups)} host group cekildi")
    return all_groups


async def get_device_ids(session):
    print("Device ID'leri cekiliyor")
    
    all_ids = []
    limit = 10
    
    url = f"{BASE_URL}/devices/devices/"
    params = {"limit": limit, "offset": 0}
    first_page = await make_request(session, "GET", url, params=params)
    
    if not first_page:
        return []
    
    total = first_page["meta"]["pagination"]["total"]
    
    for device in first_page["resources"]:
        all_ids.append(device["device_id"])
        
    tasks = []
    for offset in range(limit, total, limit):
        params = {"limit": limit, "offset": offset}
        task = make_request(session, "GET", url, params=params)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    for result in results:
        if result:
            for device in result["resources"]:
                all_ids.append(device["device_id"])
    
    unique_ids = list(set(all_ids))
    
    if len(all_ids) != len(unique_ids):
        print(f"{len(all_ids) - len(unique_ids)} tekrar eden ID kaldirildi")
    
    print(f"{len(unique_ids)} unique device ID cekildi")
    return unique_ids


async def get_device_details(session, device_ids):
    print("Device detaylari cekiliyor")
    
    all_devices = []
    batch_size = 10

    batches = [] 
    for i in range(0, len(device_ids), batch_size):
        batch = device_ids[i:i+batch_size]
        batches.append(batch)
    

    tasks = []
    url = f"{BASE_URL}/devices/entities/"
    for batch in batches:
        json_data = {"ids": batch}
        task = make_request(session, "POST", url, json_data=json_data)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    received_ids = set()
    for result in results:
        if result:
            for device in result["resources"]:
                all_devices.append(device)
                received_ids.add(device["device_id"])
    

    requested_ids = set(device_ids)
    missing_ids = requested_ids - received_ids
    
    if missing_ids:
        print(f"{len(missing_ids)} device bulunamadi: {list(missing_ids)[:5]}")
        logger.warning(f"{len(missing_ids)} device bulunamadi")
        
        # Retry missing IDs individually
        if len(missing_ids) <= 10:
            print("Eksik ID'ler tekrar deneniyor")
            for missing_id in missing_ids:
                json_data = {"ids": [missing_id]}
                result = await make_request(session, "POST", url, json_data=json_data)
                if result and result["resources"]:
                    all_devices.extend(result["resources"])
                    print(f"{missing_id} bulundu")
    
    print(f"{len(all_devices)} device detayi cekildi")
    return all_devices


async def get_device_states(session, device_ids):
    print("Device state'leri cekiliyor")
    
    all_states = []
    batch_size = 10
    
    batches = []
    for i in range(0, len(device_ids), batch_size):
        batch = device_ids[i:i+batch_size]
        batches.append(batch)
        
    tasks = []
    url = f"{BASE_URL}/devices/entities/online-state/"
    for batch in batches:
        json_data = {"ids": batch}
        task = make_request(session, "POST", url, json_data=json_data)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    

    received_ids = set()
    for result in results:
        if result:
            for state in result["resources"]:
                all_states.append(state)
                received_ids.add(state["id"])
    
    requested_ids = set(device_ids)
    missing_ids = requested_ids - received_ids
    
    if missing_ids:
        print(f"{len(missing_ids)} device state bulunamadi")
        logger.warning(f"{len(missing_ids)} device state bulunamadi")
    
    print(f"{len(all_states)} device state cekildi")
    return all_states


def add_group_info(devices, groups):
    print("Group bilgileri ekleniyor")
    
    group_dict = {}
    for group in groups:
        group_dict[group["id"]] = group
    

    for device in devices:
        device_groups = device.get("groups", [])
        group_info = []
        
        for group_id in device_groups:
            if group_id in group_dict:
                group_info.append(group_dict[group_id])
        

        group_info.sort(key=lambda x: x.get("name", ""))
        device["group_info"] = group_info
    
    print(f"{len(devices)} device'a group bilgisi eklendi")
    return devices


async def save_to_es(es, devices, states):
    print("Elasticsearch'e kaydediliyor")
    
    try:
        batch_size = 100
        device_count = 0
        
        for i in range(0, len(devices), batch_size):
            batch = devices[i:i+batch_size]
            
            for device in batch:
                await es.index(
                    index="octoxlabs-data",
                    id=device["device_id"],
                    document=device
                )
                device_count += 1
            
        state_count = 0
        for state in states:
            device_id = state.get("id")
            if device_id:
                try:
                    await es.update(
                        index="octoxlabs-data",
                        id=device_id,
                        doc={"online_state": state.get("state")}
                    )
                    state_count += 1
                except:
                    pass
        
        print(f"{device_count} device ve {state_count} state kaydedildi")
        
    except Exception as e:
        print(f"Elasticsearch hatasi: {e}")
        logger.error(f"Elasticsearch hatasi: {e}")


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
            print("\nToken aliniyor")
            await get_auth_token(session)
            await log_to_es(es, "INFO", "Token alindi")
            
            print()
            groups = await get_host_groups(session)
            await log_to_es(es, "INFO", f"{len(groups)} host group cekildi")
            
            print()
            device_ids = await get_device_ids(session)
            await log_to_es(es, "INFO", f"{len(device_ids)} device ID cekildi")
            
            print()
            devices = await get_device_details(session, device_ids)
            await log_to_es(es, "INFO", f"{len(devices)} device detayi cekildi")
            
            print()
            states = await get_device_states(session, device_ids)
            await log_to_es(es, "INFO", f"{len(states)} device state cekildi")

            print()
            devices = add_group_info(devices, groups)
            await log_to_es(es, "INFO", "Enrichment tamamlandi")
            

            print()
            await save_to_es(es, devices, states)
            
            print("\n" + "=" * 50)
            print("TAMAMLANDI")
            print(f"- {len(groups)} Host Group")
            print(f"- {len(devices)} Device")
            print(f"- {len(states)} Device State")
            
            if devices:
                print("\nOrnek Device:")
                sample = devices[0]
                print(f"Hostname: {sample.get('hostname')}")
                print(f"Platform: {sample.get('platform_name')}")
                print(f"Groups: {[g.get('name') for g in sample.get('group_info', [])]}")
    
    except Exception as e:
        print(f"Hata: {e}")
        await log_to_es(es, "ERROR", f"Hata: {e}")
    
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
