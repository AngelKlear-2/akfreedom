#!/usr/bin/env python3
"""
МАРУСЯ VPN Checker — авто-проверка + пуш в GitHub
Жёсткий фильтр: только качественные источники для РФ (МТС + Ростелеком)
"""

import os
import re
import sys
import socket
import time
import concurrent.futures
import argparse
from datetime import datetime, timezone, timedelta

try:
    import requests
    from github import Github
except ImportError:
    print("Установи зависимости:")
    print("  pip install requests PyGithub")
    sys.exit(1)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
REPO_NAME = "AngelKlear-2/akfreedom"
BRANCH = "main"

# Екатеринбург = UTC+5
EKB = timezone(timedelta(hours=5))

# Только самые рабочие источники для России
SOURCES = {
    "blacklist": [
        # Основные от igareck (проверенные)
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
        # Ещё пару относительно чистых
        "https://raw.githubusercontent.com/aviamastersgh/vpn-free-russia/main/verified_configs.txt",
    ],
    "whitelist": [
        # Самые важные — обход белых списков / CIDR
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
        # Subzio (хорошие hy2 + white)
        "https://raw.githubusercontent.com/Subzio/subzio/main/WHITE_LIST_PROXY_COLLECTION.txt",
        "https://raw.githubusercontent.com/Subzio/subzio/main/HYSTERIA2.txt",
    ],
}

TIMEOUT = 2.5
MAX_WORKERS = 40
MAX_LATENCY_MS = 5500          # жёстче отсекаем медленные
KEEP_TOP = {"blacklist": 40, "whitelist": 60}   # больше белых, меньше обычных

def extract_host_port(uri: str):
    try:
        m = re.search(r"@([^:/?#]+):(\d+)", uri)
        if m:
            return m.group(1), int(m.group(2))
        m = re.search(r"//(?:[^@/\s]+@)?([^:/?#]+):(\d+)", uri)
        if m:
            return m.group(1), int(m.group(2))
    except Exception:
        pass
    return None, None

def tcp_ping(host: str, port: int, timeout: float = TIMEOUT):
    try:
        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout):
            return round((time.perf_counter() - start) * 1000, 1)
    except Exception:
        return None

def fetch_source(url: str) -> list:
    try:
        r = requests.get(url, timeout=18, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        text = r.text
        if not any(p in text[:300] for p in ("vless://", "vmess://", "trojan://", "ss://", "hysteria2://", "hy2://")):
            import base64
            try:
                text = base64.b64decode(text + "==").decode("utf-8", errors="ignore")
            except Exception:
                pass
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(("vless://", "vmess://", "trojan://", "ss://", "hysteria2://", "hy2://")):
                lines.append(line)
        return lines
    except Exception as e:
        print(f"  [!] {url.split('/')[-1]} → {e}")
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
    print(f"\n=== {name.upper()} ===")
    all_uris = []
    for u in urls:
        fetched = fetch_source(u)
        all_uris.extend(fetched)
        print(f"  +{len(fetched):4d}  {u.split('/')[-1]}")
    all_uris = list(dict.fromkeys(all_uris))
    print(f"Уникальных: {len(all_uris)}")

    working = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(check_uri, uri) for uri in all_uris]
        for fut in concurrent.futures.as_completed(futs):
            res = fut.result()
            if res:
                working.append(res)

    working.sort(key=lambda x: x[1])
    top = KEEP_TOP.get(name, 50)
    working = working[:top]
    print(f"Рабочих (топ {top}): {len(working)}")
    for uri, lat in working[:3]:
        print(f"  {lat:6.1f} ms  {uri[:70]}...")

    result = []
    for uri, lat in working:
        if "#" in uri:
            base, remark = uri.rsplit("#", 1)
            result.append(f"{base}#{remark} | {lat}ms")
        else:
            result.append(f"{uri}#{lat}ms")
    return result

def push_to_github(files: dict):
    if not GITHUB_TOKEN:
        print("\n[!] Нет GITHUB_TOKEN — сохраняю локально")
        for name, content in files.items():
            with open(name, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  saved {name}")
        return

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    now = datetime.now(timezone.utc).isoformat()

    for path, content in files.items():
        try:
            contents = repo.get_contents(path, ref=BRANCH)
            repo.update_file(path, f"auto {path} {now}", content, contents.sha, branch=BRANCH)
            print(f"[+] updated {path}")
        except Exception:
            repo.create_file(path, f"create {path}", content, branch=BRANCH)
            print(f"[+] created {path}")

def run_once():
    print(f"\n{'='*50}")
    print(f"Старт: {datetime.now(EKB).strftime('%Y-%m-%d %H:%M:%S ЕКБ')}")
    print(f"{'='*50}")

    black = process_list("blacklist", SOURCES["blacklist"])
    white = process_list("whitelist", SOURCES["whitelist"])

    now = datetime.now(EKB).strftime("%Y-%m-%d %H:%M ЕКБ")

    files = {
        "blacklist.txt": f"# blacklist.txt\n# BLACK LISTS (обычные)\n# updated: {now}\n# working: {len(black)}\n\n" + "\n".join(black),
        "whitelist.txt": f"# whitelist.txt\n# WHITE LISTS / CIDR / Обход БС\n# updated: {now}\n# working: {len(white)}\n\n" + "\n".join(white),
        "vpn.txt": f"# vpn.txt Mixed\n# updated: {now}\n\n" + "\n".join(black[:30] + ["", "# === WHITE / ОБХОД БС ===", ""] + white),
        "config.txt": (
            f"# ---\n#profile-title: МАРУСЯ VPN (AKfreedom)\n"
            f"#profile-update-interval: 15\n"
            f"#support-url: https://t.me/@litiru\n"
            f"#announce: 🏳️ Auto {now} | МТС+Ростелеком 🏳️\n\n"
            f"# ========== ОБЫЧНЫЕ ВПН ==========\n"
            + "\n".join(black[:25])
            + "\n\n# ========== ОБХОД БЕЛЫХ СПИСКОВ (главное) ==========\n"
            + "\n".join(white)
            + "\n"
        ),
    }
    push_to_github(files)
    print(f"\nГотово. Black: {len(black)} | White: {len(white)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", type=int, default=0, help="Интервал в минутах (0 = один раз)")
    args = parser.parse_args()

    if args.loop <= 0:
        run_once()
        return

    print(f"Бесконечный режим: каждые {args.loop} минут")
    print("Ctrl+C чтобы остановить\n")
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            print("\nОстановлено пользователем")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
        print(f"\nСпим {args.loop} мин...")
        time.sleep(args.loop * 60)

if __name__ == "__main__":
    main()
