import streamlit as st
import os
import re
import socket
import time
import concurrent.futures
from datetime import datetime, timezone
import requests
from github import Github

st.set_page_config(page_title="МАРУСЯ VPN Checker", page_icon="🏳️", layout="wide")

st.title("🏳️ МАРУСЯ VPN — Auto Checker")
st.caption("Проверяет сервера → пушит рабочие в GitHub (AngelKlear-2/akfreedom)")

REPO_NAME = "AngelKlear-2/akfreedom"
BRANCH = "main"

SOURCES = {
    "blacklist": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS_mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt",
        "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/vless.txt",
        "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/protocols/hysteria2.txt",
        "https://raw.githubusercontent.com/0xRadikal/Free-v2ray-Configs/main/top100.txt",
        "https://raw.githubusercontent.com/Epodonios/v2ray-configs/main/Splitted-By-Protocol/vless.txt",
        "https://raw.githubusercontent.com/3inker/v2ray-subscription/main/all_not_ru.txt",
        "https://raw.githubusercontent.com/aviamastersgh/vpn-free-russia/main/verified_configs.txt",
        "https://raw.githubusercontent.com/nikita29a/FreeProxyList/main/mirror/1.txt",
    ],
    "whitelist": [
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-checked.txt",
        "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/WHITE-CIDR-RU-all.txt",
        "https://raw.githubusercontent.com/Subzio/subzio/main/WHITE_LIST_PROXY_COLLECTION.txt",
        "https://raw.githubusercontent.com/Subzio/subzio/main/HYSTERIA2.txt",
    ],
}

TIMEOUT = 2.5
MAX_WORKERS = 40
MAX_LATENCY_MS = 6500
KEEP_TOP = {"blacklist": 80, "whitelist": 40}

def get_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

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
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
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
    except Exception:
        return []

def check_uri(uri: str):
    host, port = extract_host_port(uri)
    if not host or not port:
        return None
    lat = tcp_ping(host, port)
    if lat is None or lat > MAX_LATENCY_MS:
        return None
    return (uri, lat)

def process_list(name: str, urls: list, progress_bar, status_text) -> list:
    status_text.text(f"Качаю источники для {name}...")
    all_uris = []
    for u in urls:
        all_uris.extend(fetch_source(u))
    all_uris = list(dict.fromkeys(all_uris))
    status_text.text(f"{name}: {len(all_uris)} уникальных, проверяю...")

    working = []
    total = len(all_uris)
    if total == 0:
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(check_uri, uri): uri for uri in all_uris}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            res = fut.result()
            if res:
                working.append(res)
            done += 1
            if done % 20 == 0 or done == total:
                progress_bar.progress(min(done / total, 1.0))

    working.sort(key=lambda x: x[1])
    top = KEEP_TOP.get(name, 50)
    working = working[:top]

    result = []
    for uri, lat in working:
        if "#" in uri:
            base, remark = uri.rsplit("#", 1)
            result.append(f"{base}#{remark} | {lat}ms")
        else:
            result.append(f"{uri}#{lat}ms")
    return result

def push_to_github(token: str, files: dict):
    g = Github(token)
    repo = g.get_repo(REPO_NAME)
    now = datetime.now(timezone.utc).isoformat()
    results = []
    for path, content in files.items():
        try:
            contents = repo.get_contents(path, ref=BRANCH)
            repo.update_file(path, f"auto-update {path} {now}", content, contents.sha, branch=BRANCH)
            results.append(f"✅ updated `{path}`")
        except Exception:
            repo.create_file(path, f"create {path}", content, branch=BRANCH)
            results.append(f"✅ created `{path}`")
    return results

token = get_token()
if not token:
    st.error("Нет GITHUB_TOKEN!\n\nНа Streamlit Cloud: Settings → Secrets → добавь:\n\nGITHUB_TOKEN = \"ghp_твой_токен\"")
    st.stop()

st.success("Токен найден. Можно запускать проверку.")

col1, col2 = st.columns(2)
with col1:
    run_btn = st.button("🚀 Проверить сервера и запушить в GitHub", type="primary", use_container_width=True)
with col2:
    st.link_button("📂 Открыть репозиторий", "https://github.com/AngelKlear-2/akfreedom")

if run_btn:
    progress = st.progress(0.0)
    status = st.empty()

    try:
        black = process_list("blacklist", SOURCES["blacklist"], progress, status)
        white = process_list("whitelist", SOURCES["whitelist"], progress, status)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        files = {
            "blacklist.txt": f"# blacklist.txt\n# BLACK LISTS\n# updated: {now}\n# working: {len(black)}\n\n" + "\n".join(black),
            "whitelist.txt": f"# whitelist.txt\n# WHITE LISTS / CIDR / Обход БС\n# updated: {now}\n# working: {len(white)}\n\n" + "\n".join(white),
            "vpn.txt": f"# vpn.txt Mixed\n# updated: {now}\n\n" + "\n".join(black[:60] + ["", "# === WHITE ===", ""] + white),
            "config.txt": (
                f"# ---\n#profile-title: МАРУСЯ VPN (AKfreedom)\n"
                f"#profile-update-interval: 15\n"
                f"#support-url: https://t.me/@litiru\n"
                f"#announce: 🏳️ Auto {now} | МТС+Ростелеком 🏳️\n\n"
                f"# ========== ОБЫЧНЫЕ ВПН ==========\n"
                + "\n".join(black[:40])
                + "\n\n# ========== ОБХОД БЕЛЫХ СПИСКОВ ==========\n"
                + "\n".join(white)
                + "\n"
            ),
        }

        status.text("Пушу в GitHub...")
        results = push_to_github(token, files)
        progress.progress(1.0)

        st.success(f"Готово! Black: **{len(black)}** | White: **{len(white)}**")
        for r in results:
            st.write(r)

        st.markdown("### Подписки обновлены:")
        st.code("https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/config.txt")
        st.code("https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/whitelist.txt")

    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.exception(e)

st.divider()
st.markdown("""
### Как это работает
1. Нажимаешь кнопку
2. Скрипт качает свежие списки с кучи источников
3. Проверяет TCP + latency
4. Оставляет только рабочие
5. Коммитит в твой репозиторий `AngelKlear-2/akfreedom`

### Важно
- Streamlit Cloud **не крутится 24/7 в фоне**. Когда никто не открывает приложение — оно спит.
- Для настоящего 24/7 лучше потом перенести на **GitHub Actions** (бесплатный cron).
- Сейчас это удобный ручной + полуавтоматический вариант.
""")
