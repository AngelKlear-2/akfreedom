#!/usr/bin/env python3
"""
МАРУСЯ VPN Checker
+ vpnserver (happ-keys) → 🇩🇪 Германия / Германия #2
+ whitelist → 🇪🇺 Обход LTE
+ auto → 🇪🇺 Авто-Обход LTE
Hysteria временно отключён (не работал у юзера)
Обновление: каждые 30 мин (actions)
"""

import os
import re
import sys
import socket
import time
import random
import concurrent.futures
import argparse
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote
from collections import defaultdict

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
    "vpnserver": [
        "https://raw.githubusercontent.com/sobolevcode/happ-keys/refs/heads/main/link",
    ],
    "whitelist": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-SNI-RU-all.txt",
    ],
    "auto": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_SS%2BAll_RUS.txt",
    ],
}

TIMEOUT = 3.0
MAX_WORKERS = 40
MAX_LATENCY_MS = 5000
KEEP_TOP = {"vpnserver": 15, "whitelist": 12, "auto": 10}
MAX_PER_COUNTRY = 3

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

EMOJI_TO_COUNTRY = {
    "🇳🇱": ("Нидерланды", "🇳🇱"),
    "🇷🇺": ("Россия", "🇷🇺"),
    "🇩🇪": ("Германия", "🇩🇪"),
    "🇺🇸": ("США", "🇺🇸"),
    "🇵🇱": ("Польша", "🇵🇱"),
    "🇫🇮": ("Финляндия", "🇫🇮"),
    "🇸🇪": ("Швеция", "🇸🇪"),
    "🇱🇻": ("Латвия", "🇱🇻"),
    "🇫🇷": ("Франция", "🇫🇷"),
    "🇨🇦": ("Канада", "🇨🇦"),
    "🇬🇧": ("Великобритания", "🇬🇧"),
    "🇹🇷": ("Турция", "🇹🇷"),
    "🇸🇬": ("Сингапур", "🇸🇬"),
    "🇯🇵": ("Япония", "🇯🇵"),
    "🇰🇷": ("Корея", "🇰🇷"),
    "🇭🇰": ("Гонконг", "🇭🇰"),
    "🇺🇦": ("Украина", "🇺🇦"),
    "🇰🇿": ("Казахстан", "🇰🇿"),
    "🇪🇪": ("Эстония", "🇪🇪"),
    "🇱🇹": ("Литва", "🇱🇹"),
    "🇨🇿": ("Чехия", "🇨🇿"),
    "🇦🇹": ("Австрия", "🇦🇹"),
    "🇨🇭": ("Швейцария", "🇨🇭"),
    "🇮🇹": ("Италия", "🇮🇹"),
    "🇪🇸": ("Испания", "🇪🇸"),
    "🇧🇪": ("Бельгия", "🇧🇪"),
    "🇳🇴": ("Норвегия", "🇳🇴"),
    "🇩🇰": ("Дания", "🇩🇰"),
    "🇮🇪": ("Ирландия", "🇮🇪"),
    "🇵🇹": ("Португалия", "🇵🇹"),
    "🇷🇴": ("Румыния", "🇷🇴"),
    "🇧🇬": ("Болгария", "🇧🇬"),
    "🇲🇩": ("Молдова", "🇲🇩"),
    "🇧🇾": ("Беларусь", "🇧🇾"),
    "🇬🇪": ("Грузия", "🇬🇪"),
    "🇦🇲": ("Армения", "🇦🇲"),
    "🇦🇿": ("Азербайджан", "🇦🇿"),
    "🇮🇳": ("Индия", "🇮🇳"),
    "🇨🇳": ("Китай", "🇨🇳"),
    "🇹🇼": ("Тайвань", "🇹🇼"),
    "🇦🇺": ("Австралия", "🇦🇺"),
    "🇧🇷": ("Бразилия", "🇧🇷"),
    "🇲🇽": ("Мексика", "🇲🇽"),
    "🇦🇷": ("Аргентина", "🇦🇷"),
    "🇿🇦": ("ЮАР", "🇿🇦"),
    "🇮🇱": ("Израиль", "🇮🇱"),
    "🇦🇪": ("ОАЭ", "🇦🇪"),
    "🇸🇦": ("Саудовская Аравия", "🇸🇦"),
    "🇹🇭": ("Таиланд", "🇹🇭"),
    "🇻🇳": ("Вьетнам", "🇻🇳"),
    "🇮🇩": ("Индонезия", "🇮🇩"),
    "🇲🇾": ("Малайзия", "🇲🇾"),
    "🇵🇭": ("Филиппины", "🇵🇭"),
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
        if not any(p in text[:500] for p in ("vless://", "vmess://", "trojan://", "ss://", "hysteria2://", "hy2://", "hysteria://")):
            import base64
            try:
                text = base64.b64decode(text + "==").decode("utf-8", errors="ignore")
            except Exception:
                pass
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(("vless://", "vmess://", "trojan://", "ss://", "hysteria2://", "hy2://", "hysteria://")):
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

def get_country_info(uri: str, host: str = None):
    name = "Сервер"
    flag = "🌐"

    if host:
        code = get_country_code(host)
        if code and code in COUNTRY_MAP:
            name, flag = COUNTRY_MAP[code]
        elif code:
            name, flag = code, "🌐"

    if name == "Сервер":
        remark = ""
        if "#" in uri:
            remark = unquote(uri.rsplit("#", 1)[1])
        for emo, (n, f) in EMOJI_TO_COUNTRY.items():
            if emo in remark:
                name, flag = n, f
                break

    if name == "Сервер":
        remark = ""
        if "#" in uri:
            remark = unquote(uri.rsplit("#", 1)[1]).strip()
        low = (remark + " " + uri).lower()
        if any(x in low for x in ["russia", "россия", "ru ", "msk", "moscow", "frkn", "яя", "yandex"]):
            name, flag = "Россия", "🇷🇺"
        elif any(x in low for x in ["poland", "польша", "pl "]):
            name, flag = "Польша", "🇵🇱"
        elif any(x in low for x in ["netherlands", "нидерланды", "nl ", "amsterdam"]):
            name, flag = "Нидерланды", "🇳🇱"
        elif any(x in low for x in ["finland", "финляндия", "fi ", "helsinki"]):
            name, flag = "Финляндия", "🇫🇮"
        elif any(x in low for x in ["germany", "германия", "de ", "frankfurt"]):
            name, flag = "Германия", "🇩🇪"
        elif any(x in low for x in ["sweden", "швеция", "se "]):
            name, flag = "Швеция", "🇸🇪"
        elif any(x in low for x in ["latvia", "латвия", "lv "]):
            name, flag = "Латвия", "🇱🇻"
        elif any(x in low for x in ["france", "франция", "fr ", "paris"]):
            name, flag = "Франция", "🇫🇷"
        elif any(x in low for x in ["usa", "сша", "us ", "america"]):
            name, flag = "США", "🇺🇸"
        elif any(x in low for x in ["canada", "канада", "ca "]):
            name, flag = "Канада", "🇨🇦"
        elif any(x in low for x in ["turkey", "турция", "tr "]):
            name, flag = "Турция", "🇹🇷"
        elif any(x in low for x in ["czechia", "czech", "чехия", "prague"]):
            name, flag = "Чехия", "🇨🇿"
        elif any(x in low for x in ["romania", "румыния"]):
            name, flag = "Румыния", "🇷🇴"
        elif any(x in low for x in ["malaysia", "малайзия"]):
            name, flag = "Малайзия", "🇲🇾"

    return name, flag

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

    random.shuffle(working)
    print(f"Живых (tcp): {len(working)}")

    if name == "vpnserver":
        by_country = defaultdict(list)
        for item in working:
            uri, lat, host = item
            cname, _ = get_country_info(uri, host)
            by_country[cname].append(item)

        selected = []
        other_countries = [c for c in by_country.keys() if c != "Россия"]
        random.shuffle(other_countries)
        for cname in other_countries:
            items = by_country[cname]
            random.shuffle(items)
            selected.extend(items[:MAX_PER_COUNTRY])

        if "Россия" in by_country:
            ru_items = by_country["Россия"]
            random.shuffle(ru_items)
            selected.extend(ru_items[:MAX_PER_COUNTRY])

        working = selected[:KEEP_TOP["vpnserver"]]
    else:
        working = working[:KEEP_TOP.get(name, 10)]

    print(f"Выбрано: {len(working)}")

    groups = defaultdict(list)
    for uri, lat, host in working:
        base = uri.split("#")[0] if "#" in uri else uri
        country_name, flag = get_country_info(uri, host)

        if name == "whitelist":
            nice = "🇪🇺 Обход LTE"
            groups["__white__"].append(f"{base}#{nice}")
        elif name == "auto":
            nice = "🇪🇺 Авто-Обход LTE"
            groups["__auto__"].append(f"{base}#{nice}")
        else:
            groups[country_name].append((flag, country_name, base))

    result = []
    if name == "vpnserver":
        country_order = list(groups.keys())
        random.shuffle(country_order)
        for cname in country_order:
            items = groups[cname]
            for i, (flag, country_name, base) in enumerate(items, 1):
                if i == 1:
                    nice = f"{flag} {country_name}"
                else:
                    nice = f"{flag} {country_name} #{i}"
                result.append(f"{base}#{nice}")
    else:
        for key in groups:
            result.extend(groups[key])

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

    vpn = process_list("vpnserver", SOURCES["vpnserver"])
    white = process_list("whitelist", SOURCES["whitelist"])
    auto = process_list("auto", SOURCES["auto"])

    now = datetime.now(EKB).strftime("%Y-%m-%d %H:%M ЕКБ")

    files = {
        "vpn.txt": (
            f"# vpn.txt Mixed\n# updated: {now}\n\n"
            + "\n".join(vpn)
            + "\n\n# === ОБХОД ===\n"
            + "\n".join(white)
            + "\n\n# === АВТО-ОБХОД ===\n"
            + "\n".join(auto)
        ),
        "config.txt": (
            f"# ---\n#profile-title: МАРУСЯ VPN\n"
            f"#profile-update-interval: 1\n"
            f"#support-url: https://t.me/@litiru\n"
            f"#announce: 🏳️ {now} | Обновление каждые 30 мин 🏳️\n\n"
            f"# ========== VPN ==========\n"
            + "\n".join(vpn)
            + "\n\n# ========== ОБХОД LTE ==========\n"
            + "\n".join(white)
            + "\n\n# ========== АВТО-ОБХОД LTE ==========\n"
            + "\n".join(auto)
            + "\n"
        ),
        "whitelist.txt": f"# whitelist.txt\n# Обход LTE\n# updated: {now}\n# working: {len(white)}\n\n" + "\n".join(white),
    }
    push_to_github(files)
    print(f"\nГотово. VPN: {len(vpn)} | Обход: {len(white)} | Авто: {len(auto)}")

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
