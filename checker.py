#!/usr/bin/env python3
"""
МАРУСЯ VPN
+ BEST — всегда первые, | Лучший
+ vpnserver / whitelist / auto — проверка TCP через check-host.net (ноды РФ)
+ hysteria → суффикс | HYSTERIA

Проверка идёт с российских нод (Москва + Питер), не из США.
"""

import os
import re
import sys
import time
import random
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

# Эти сервера ВСЕГДА в конфиге, всегда сверху
BEST_SERVERS = [
    "vless://b9e1971f-ba19-4c33-808f-7bc9d2eab835@91.108.242.126:47182?encryption=none&security=reality&sni=www.goo.gl&fp=firefox&pbk=3Qh9roHIRJtLEM-gV_hudQrY6wPK_Dc3ePVtWLGqYho&sid=ef7db38f625526f5&type=tcp&headerType=none#🇩🇪 Германия | Лучший",
    "vless://b9e1971f-ba19-4c33-808f-7bc9d2eab835@217.60.178.109:443?encryption=none&security=reality&sni=www.amazon.com&fp=firefox&pbk=GsnJz4Rh8mdgEwxB1l7XCsPT4-vwAl459pHNwCRsoyA&sid=8f2571eff71798d9&type=tcp&headerType=none#🇳🇱 Нидерланды | Лучший",
    "vless://b9e1971f-ba19-4c33-808f-7bc9d2eab835@179.198.49.84:47000?encryption=none&security=reality&sni=www.goo.gl&fp=firefox&pbk=EJrtmRT2Acb9nNj8Yc-nfPxRprxkF52zpDcnmJ0qNS0&sid=96bb9775a5&type=tcp&headerType=none#🇵🇱 Польша | Лучший",
    "vless://b9e1971f-ba19-4c33-808f-7bc9d2eab835@89.22.232.117:443?encryption=none&security=reality&sni=www.goo.gl&fp=firefox&pbk=3Qh9roHIRJtLEM-gV_hudQrY6wPK_Dc3ePVtWLGqYho&sid=ef7db38f625526f5&type=tcp&headerType=none#🇸🇪 Швеция | Лучший",
]

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

KEEP_TOP = {"vpnserver": 15, "whitelist": 12, "auto": 10}
MAX_PER_COUNTRY = 3
MAX_CHECK = 50
RU_NODES = [
    "ru1.node.check-host.net",
    "ru2.node.check-host.net",
    "ru3.node.check-host.net",
]
CHECK_HOST_HEADERS = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

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


def protocol_suffix(uri: str) -> str:
    u = uri.lower()
    if u.startswith(("hysteria2://", "hy2://", "hysteria://")):
        return " | HYSTERIA"
    return ""


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


def check_tcp_from_ru(host: str, port: int) -> bool:
    """TCP-проверка с российских нод check-host.net. True = хотя бы 1 нода ОК."""
    target = f"{host}:{port}"
    nodes_q = "&".join(f"node={n}" for n in RU_NODES)
    try:
        r = requests.get(
            f"https://check-host.net/check-tcp?host={target}&{nodes_q}",
            headers=CHECK_HOST_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        req_id = data.get("request_id")
        if not req_id:
            return False
    except Exception as e:
        print(f"    [ch] start fail {target}: {e}")
        return False

    for attempt in range(6):
        time.sleep(2)
        try:
            rr = requests.get(
                f"https://check-host.net/check-result/{req_id}",
                headers=CHECK_HOST_HEADERS,
                timeout=12,
            )
            rr.raise_for_status()
            results = rr.json()
        except Exception:
            continue

        if not isinstance(results, dict):
            continue

        ok_count = 0
        pending = 0
        for node, res in results.items():
            if res is None:
                pending += 1
                continue
            if isinstance(res, list) and res:
                item = res[0]
                if isinstance(item, dict) and "time" in item:
                    ok_count += 1

        if ok_count >= 1:
            return True
        if pending == 0:
            return False

    return False


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


def best_hosts() -> set:
    hosts = set()
    for uri in BEST_SERVERS:
        h, _ = extract_host_port(uri)
        if h:
            hosts.add(h.lower())
    return hosts


def process_list(name: str, urls: list) -> list:
    print(f"\n=== {name.upper()} ===")
    all_uris = []
    for u in urls:
        fetched = fetch_source(u)
        all_uris.extend(fetched)
        print(f"  +{len(fetched):4d}  {u.split('/')[-1]}")
    all_uris = list(dict.fromkeys(all_uris))
    print(f"Уникальных: {len(all_uris)}")

    skip_hosts = best_hosts() if name == "vpnserver" else set()

    candidates = []
    for uri in all_uris:
        host, port = extract_host_port(uri)
        if not host or not port:
            continue
        if host.lower() in skip_hosts:
            continue
        candidates.append(uri)

    random.shuffle(candidates)
    to_check = candidates[:MAX_CHECK]
    print(f"К проверке (check-host РФ): {len(to_check)}")

    working = []
    for i, uri in enumerate(to_check, 1):
        host, port = extract_host_port(uri)
        ok = check_tcp_from_ru(host, port)
        status = "OK" if ok else "fail"
        print(f"  [{i}/{len(to_check)}] {host}:{port} → {status}")
        if ok:
            working.append(uri)
        time.sleep(0.4)

    print(f"Живых из РФ: {len(working)}")
    random.shuffle(working)

    if name == "vpnserver":
        by_country = defaultdict(list)
        for uri in working:
            host, _ = extract_host_port(uri)
            cname, _ = get_country_info(uri, host)
            by_country[cname].append(uri)

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

        selected = selected[:KEEP_TOP["vpnserver"]]
    else:
        selected = working[:KEEP_TOP.get(name, 10)]

    print(f"Выбрано: {len(selected)}")

    groups = defaultdict(list)
    for uri in selected:
        base = uri.split("#")[0] if "#" in uri else uri
        host, _ = extract_host_port(uri)
        country_name, flag = get_country_info(uri, host)
        suf = protocol_suffix(uri)

        if name == "whitelist":
            nice = f"🇪🇺 Обход LTE{suf}"
            groups["__white__"].append(f"{base}#{nice}")
        elif name == "auto":
            nice = f"🇪🇺 Авто-Обход LTE{suf}"
            groups["__auto__"].append(f"{base}#{nice}")
        else:
            groups[country_name].append((flag, country_name, base, suf))

    result = []
    if name == "vpnserver":
        country_order = list(groups.keys())
        random.shuffle(country_order)
        for cname in country_order:
            items = groups[cname]
            for i, (flag, country_name, base, suf) in enumerate(items, 1):
                if i == 1:
                    nice = f"{flag} {country_name}{suf}"
                else:
                    nice = f"{flag} {country_name} #{i}{suf}"
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

    best = list(BEST_SERVERS)
    print(f"BEST (всегда): {len(best)}")

    vpn = process_list("vpnserver", SOURCES["vpnserver"])
    white = process_list("whitelist", SOURCES["whitelist"])
    auto = process_list("auto", SOURCES["auto"])

    now = datetime.now(EKB).strftime("%Y-%m-%d %H:%M ЕКБ")

    all_vpn = best + vpn

    files = {
        "vpn.txt": (
            f"# vpn.txt Mixed\n# updated: {now}\n# check: check-host.net RU nodes\n\n"
            + "\n".join(all_vpn)
            + "\n\n# === ОБХОД ===\n"
            + "\n".join(white)
            + "\n\n# === АВТО-ОБХОД ===\n"
            + "\n".join(auto)
        ),
        "config.txt": (
            f"# ---\n#profile-title: LOWTAB VPN\n"
            f"#profile-update-interval: 1\n"
            f"#support-url: https://t.me/@litiru\n"
            f"#announce: 🏳️ {now} 🏳️\n\n"
            f"# ========== ЛУЧШИЕ ==========\n"
            + "\n".join(best)
            + "\n\n# ========== VPN ==========\n"
            + "\n".join(vpn)
            + "\n\n# ========== ОБХОД LTE ==========\n"
            + "\n".join(white)
            + "\n\n# ========== АВТО-ОБХОД LTE ==========\n"
            + "\n".join(auto)
            + "\n"
        ),
        "whitelist.txt": f"# whitelist.txt\n# Обход LTE\n# updated: {now}\n# working(RU): {len(white)}\n\n" + "\n".join(white),
    }
    push_to_github(files)
    print(f"\nГотово. BEST: {len(best)} | VPN: {len(vpn)} | Обход: {len(white)} | Авто: {len(auto)}")


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
