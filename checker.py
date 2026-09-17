#!/usr/bin/env python3
"""
VPN Config Checker + Auto-Push to GitHub
Проверяет конфиги на TCP-доступность + latency, оставляет рабочие,
пушит в AngelKlear-2/akfreedom

Требования:
  pip install requests PyGithub

Запуск:
  export GITHUB_TOKEN=ghp_xxxxxxxx
  python checker.py

Или в cron / GitHub Actions / Vercel Cron каждые 1-5 мин.
"""

import os
import re
import socket
import time
import concurrent.futures
from datetime import datetime, timezone

import requests
from github import Github

# ================== НАСТРОЙКИ ==================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
REPO_NAME = "AngelKlear-2/akfreedom"
BRANCH = "main"

SOURCES = {
    "blacklist": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    ],
    "whitelist": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
    ],
}

TIMEOUT = 3.0
MAX_WORKERS = 40
MAX_LATENCY_MS = 8000
KEEP_TOP_N = {"blacklist": 80, "whitelist": 40, "vpn": 100}

def extract_host_port(uri: str):
    try:
        m = re.search(r"@([^:/?]+):(\d+)", uri)
        if m:
            return m.group(1), int(m.group(2))
        m = re.search(r"//(?:[^@]+@)?([^:/?]+):(\d+)", uri)
        if m:
            return m.group(1), int(m.group(2))
    except Exception:
        pass
    return None, None

def tcp_ping(host: str, port: int, timeout: float = TIMEOUT):
    try:
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout):
            latency = (time.perf_counter() - start) * 1000
            return round(latency, 1)
    except Exception:
        return None

def fetch_source(url: str) -> list:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        lines = []
        for line in r.text.splitlines():
            line = line.strip()
            if line.startswith(("vless://", "vmess://", "trojan://", "ss://", "hysteria2://", "hy2://")):
                lines.append(line)
        return lines
    except Exception as e:
        print(f"[!] Failed {url}: {e}")
        return []

def check_uri(uri: str):
    host, port = extract_host_port(uri)
    if not host or not port:
        return None
    lat = tcp_ping(host, port)
    if lat is None or lat > MAX_LATENCY_MS:
        return None
    return (uri, lat)

def process_list(name: str, urls: list) -> list:
    print(f"\n=== Processing {name} ===")
    all_uris = []
    for u in urls:
        all_uris.extend(fetch_source(u))
    all_uris = list(dict.fromkeys(all_uris))
    print(f"Fetched {len(all_uris)} unique URIs")

    working = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(check_uri, uri): uri for uri in all_uris}
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            if res:
                working.append(res)

    working.sort(key=lambda x: x[1])
    top_n = KEEP_TOP_N.get(name, 50)
    working = working[:top_n]
    print(f"Working: {len(working)} (kept top {top_n})")
    for uri, lat in working[:5]:
        print(f"  {lat:6.1f} ms  {uri[:80]}...")

    result = []
    for uri, lat in working:
        if "#" in uri:
            base, remark = uri.rsplit("#", 1)
            new_uri = f"{base}#{remark} | {lat}ms"
        else:
            new_uri = f"{uri}#{lat}ms"
        result.append(new_uri)
    return result

def push_to_github(files: dict):
    if not GITHUB_TOKEN:
        print("[!] No GITHUB_TOKEN, skip push. Saving locally only.")
        for name, content in files.items():
            with open(name, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Saved {name}")
        return

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)

    for path, content in files.items():
        try:
            contents = repo.get_contents(path, ref=BRANCH)
            repo.update_file(path, f"auto-update {path} {datetime.now(timezone.utc).isoformat()}", content, contents.sha, branch=BRANCH)
            print(f"[+] Updated {path}")
        except Exception:
            repo.create_file(path, f"create {path}", content, branch=BRANCH)
            print(f"[+] Created {path}")

def main():
    print(f"Starting checker at {datetime.now(timezone.utc).isoformat()}")
    black = process_list("blacklist", SOURCES["blacklist"])
    white = process_list("whitelist", SOURCES["whitelist"])
    mixed = black[:60] + ["", "# ========== WHITE LISTS ==========", ""] + white
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    files = {
        "blacklist.txt": f"# blacklist.txt\n# BLACK LISTS\n# updated: {now}\n# working: {len(black)}\n\n" + "\n".join(black),
        "whitelist.txt": f"# whitelist.txt\n# WHITE LISTS / CIDR\n# updated: {now}\n# working: {len(white)}\n\n" + "\n".join(white),
        "vpn.txt": f"# vpn.txt\n# Mixed\n# updated: {now}\n\n" + "\n".join(mixed),
        "config.txt": f"# ---\n#profile-title: МАРУСЯ VPN (AKfreedom)\n#profile-update-interval: 5\n#support-url: https://t.me/@litiru\n#announce: 🏳️ Auto-updated | {now} 🏳️\n\n# ========== ОБЫЧНЫЕ ВПН ==========\n" + "\n".join(black[:40]) + "\n\n# ========== ОБХОД БЕЛЫХ СПИСКОВ ==========\n" + "\n".join(white) + "\n",
    }
    push_to_github(files)
    print("Done.")

if __name__ == "__main__":
    main()
