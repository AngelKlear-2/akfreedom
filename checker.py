#!/usr/bin/env python3
"""
МАРУСЯ VPN Checker — жёсткий фильтр + чистые названия
Только качественные источники + нормальные имена + эмодзи
+ определение страны через ipinfo.io/{ip}/country
"""

import os
import re
import sys
import socket
import time
import concurrent.futures
import argparse
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote

try:
    import requests
    from github import Github
except ImportError:
    print("Установи зависимости: pip install requests PyGithub")
    sys.exit(1)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
REPO_NAME = "AngelKlear-2/akfreedom"
BRANCH = "main"
EKB = timezone(timedelta(hours=5))

SOURCES = {
    "blacklist": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
    ],
    "whitelist": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    ],
    "vpnserver": [
        "https://raw.githubusercontent.com/sobolevcode/happ-keys/refs/heads/main/link",
    ],
}

TIMEOUT = 2.3
MAX_WORKERS = 35
MAX_LATENCY_MS = 4500
KEEP_TOP = {"vpnserver": 4, "whitelist": 5, "blacklist": 5}   # сильно меньше

# кэш стран, чтобы не долбить ipinfo по сто раз
_country_cache = {}

COUNTRY_MAP = {
    "NL": ("Нидерланды", "🇳🇱"),
    "RU": ("Россия", "🇷🇺"),
    "DE": ("Германия", "🇩🇪"),
    "US": ("США", "🇺🇸"),
    "PL": ("Польша", "🇵🇱"),
    "FI": ("Финляндия", "🇫🇮"),
    "SE": ("Швеция", "🇸🇪"),
    "LV": ("Латвия", "🇱🇻"),
    "FR": ("Франция", "🇫🇷"),
    "CA": ("Канада", "🇨🇦"),
    "GB": ("Великобритания", "🇬🇧"),
    "UK": ("Великобритания", "🇬🇧"),
    "TR": ("Турция", "🇹🇷"),
    "SG": ("Сингапур", "🇸🇬"),
    "JP": ("Япония", "🇯🇵"),
    "KR": ("Корея", "🇰🇷"),
    "HK": ("Гонконг", "🇭🇰"),
    "UA": ("Украина", "🇺🇦"),
    "KZ": ("Казахстан", "🇰🇿"),
    "EE": ("Эстония", "🇪🇪"),
    "LT": ("Литва", "🇱🇹"),
    "CZ": ("Чехия", "🇨🇿"),
    "AT": ("Австрия", "🇦🇹"),
    "CH": ("Швейцария", "🇨🇭"),
    "IT": ("Италия", "🇮🇹"),
    "ES": ("Испания", "🇪🇸"),
    "BE": ("Бельгия", "🇧🇪"),
    "NO": ("Норвегия", "🇳🇴"),
    "DK": ("Дания", "🇩🇰"),
    "IE": ("Ирландия", "🇮🇪"),
    "PT": ("Португалия", "🇵🇹"),
    "RO": ("Румыния", "🇷🇴"),
    "BG": ("Болгария", "🇧🇬"),
    "MD": ("Молдова", "🇲🇩"),
    "BY": ("Беларусь", "🇧🇾"),
    "GE": ("Грузия", "🇬🇪"),
    "AM": ("Армения", "🇦🇲"),
    "AZ": ("Азербайджан", "🇦🇿"),
    "IN": ("Индия", "🇮🇳"),
    "CN": ("Китай", "🇨🇳"),
    "TW": ("Тайвань", "🇹🇼"),
    "AU": ("Австралия", "🇦🇺"),
    "BR": ("Бразилия", "🇧🇷"),
    "MX": ("Мексика", "🇲🇽"),
    "AR": ("Аргентина", "🇦🇷"),
    "ZA": ("ЮАР", "🇿🇦"),
    "IL": ("Израиль", "🇮🇱"),
    "AE": ("ОАЭ", "🇦🇪"),
    "SA": ("Саудовская Аравия", "🇸🇦"),
    "TH": ("Таиланд", "🇹🇭"),
    "VN": ("Вьетнам", "🇻🇳"),
    "ID": ("Индонезия", "🇮🇩"),
    "MY": ("Малайзия", "🇲🇾"),
    "PH": ("Филиппины", "🇵🇭"),
}

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

def get_country_code(host: str) -> str:
    """Тянет код страны через ipinfo.io/{host}/country (как curl)"""
    if not host:
        return ""
    if host in _country_cache:
        return _country_cache[host]
    try:
        r = requests.get(
            f"https://ipinfo.io/{host}/country",
            timeout=6,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if r.status_code == 200:
            code = r.text.strip().upper()
            if code and len(code) == 2 and code.isalpha():
                _country_cache[host] = code
                return code
    except Exception:
        pass
    _country_cache[host] = ""
    return ""

def fetch_source(url: str) -> list:
    try:
        r = requests.get(url, timeout=16, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        text = r.text
        if not any(p in text[:400] for p in ("vless://", "vmess://", "trojan://", "ss://", "hysteria2://", "hy2://")):
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
    return (uri, lat, host)

def clean_name(uri: str, lat: float, host: str = None) -> str:
    """Делает нормальное русское название + эмодзи. Страну берём из ipinfo по IP."""
    # берём старый remark если есть (на всякий)
    remark = ""
    if "#" in uri:
        remark = unquote(uri.rsplit("#", 1)[1]).strip()

    # убираем мусор
    remark = re.sub(r"t\.me/\S+", "", remark, flags=re.I)
    remark = re.sub(r"CF[\u4e00-\u9fff\w_\-]*", "", remark)
    remark = re.sub(r"[\u4e00-\u9fff]+", "", remark)  # китайские иероглифы
    remark = re.sub(r"@\w+", "", remark)
    remark = re.sub(r"\|\s*\d+ms.*", "", remark)
    remark = re.sub(r"\s+", " ", remark).strip(" -_|#")

    country = "Сервер"
    flag = "🌐"

    # 1) главное — ipinfo по IP/host
    if host:
        code = get_country_code(host)
        if code and code in COUNTRY_MAP:
            country, flag = COUNTRY_MAP[code]
        elif code:
            # неизвестный код — просто код
            country, flag = code, "🌐"

    # 2) fallback по ключевым словам (если ipinfo не дал)
    if country == "Сервер":
        low = (remark + " " + uri).lower()
        if any(x in low for x in ["russia", "россия", "ru ", "msk", "moscow", "frkn", "яя", "yandex"]):
            country, flag = "Россия", "🇷🇺"
        elif any(x in low for x in ["poland", "польша", "pl "]):
            country, flag = "Польша", "🇵🇱"
        elif any(x in low for x in ["netherlands", "нидерланды", "nl ", "amsterdam"]):
            country, flag = "Нидерланды", "🇳🇱"
        elif any(x in low for x in ["finland", "финляндия", "fi "]):
            country, flag = "Финляндия", "🇫🇮"
        elif any(x in low for x in ["germany", "германия", "de ", "frankfurt"]):
            country, flag = "Германия", "🇩🇪"
        elif any(x in low for x in ["sweden", "швеция", "se "]):
            country, flag = "Швеция", "🇸🇪"
        elif any(x in low for x in ["latvia", "латвия", "lv "]):
            country, flag = "Латвия", "🇱🇻"
        elif any(x in low for x in ["france", "франция", "fr "]):
            country, flag = "Франция", "🇫🇷"
        elif any(x in low for x in ["usa", "сша", "us ", "america"]):
            country, flag = "США", "🇺🇸"
        elif any(x in low for x in ["canada", "канада", "ca "]):
            country, flag = "Канада", "🇨🇦"
        elif "anycast" in low:
            country, flag = "Anycast", "🌐"

    # эмодзи по качеству
    emoji = ""
    if lat <= 80:
        emoji = " ⚡"
    elif lat <= 180:
        emoji = " ⚡"
    low = (remark + " " + uri).lower()
    if "game" in low or "игр" in low or "gaming" in low:
        emoji += " 🎮"
    if "anycast" in low:
        emoji += " 🌐"

    # итоговый remark — ссылку не трогаем, только название
    final = f"{flag} {country}{emoji}"
    return final

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

    working.sort(key=lambda x: x[1])  # самые быстрые сверху
    top = KEEP_TOP.get(name, 15)
    working = working[:top]
    print(f"Рабочих (топ {top}): {len(working)}")

    result = []
    for uri, lat, host in working:
        base = uri.split("#")[0] if "#" in uri else uri  # ссылку не меняем
        nice = clean_name(uri, lat, host)
        result.append(f"{base}#{nice} | {lat}ms")
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
        "blacklist.txt": f"# blacklist.txt\n# Обычные VPN\n# updated: {now}\n# working: {len(black)}\n\n" + "\n".join(black),
        "whitelist.txt": f"# whitelist.txt\n# Обход белых списков / CIDR\n# updated: {now}\n# working: {len(white)}\n\n" + "\n".join(white),
        "vpn.txt": f"# vpn.txt Mixed\n# updated: {now}\n\n" + "\n".join(black + ["", "# === ОБХОД БС ===", ""] + white),
        "config.txt": (
            f"# ---\n#profile-title: МАРУСЯ VPN\n"
            f"#profile-update-interval: 15\n"
            f"#support-url: https://t.me/@litiru\n"
            f"#announce: 🏳️ {now} | Первые - качественные 🏳️\n\n"
            f"# ========== ОБЫЧНЫЕ ==========\n"
            + "\n".join(black)
            + "\n\n# ========== ОБХОД БЕЛЫХ СПИСКОВ ==========\n"
            + "\n".join(white)
            + "\n"
        ),
    }
    push_to_github(files)
    print(f"\nГотово. Black: {len(black)} | White: {len(white)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", type=int, default=0)
    args = parser.parse_args()
    if args.loop <= 0:
        run_once()
        return
    print(f"Бесконечный режим: каждые {args.loop} мин")
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[ERROR] {e}")
        time.sleep(args.loop * 60)

if __name__ == "__main__":
    main()
