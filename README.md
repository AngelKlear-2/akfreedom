# akfreedom / МАРУСЯ VPN

Авто-обновляемые рабочие конфиги для России (МТС + Ростелеком).

## Подписки

- **Основная (mixed)**: https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/vpn.txt
- **Black lists** (обычные): https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/blacklist.txt
- **White lists** (обход БС / CIDR): https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/whitelist.txt
- **config.txt** (для клиентов): https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/config.txt

## Авто-обновление 24/7

**GitHub Actions** крутится каждые **30 минут**:
1. Качает свежие списки с Igareck и кучи других источников
2. Проверяет TCP + latency
3. Оставляет только рабочие
4. Пушит в `blacklist.txt`, `whitelist.txt`, `vpn.txt`, `config.txt`

Workflow: `.github/workflows/update-configs.yml`

Можно запустить вручную: Actions → Update VPN Configs → Run workflow

## Локальный запуск

```bash
pip install requests PyGithub
export GITHUB_TOKEN=ghp_ваш_токен
python checker.py          # один раз
python checker.py --loop 30  # каждые 30 мин
```

## Шаблон

- Обычные VPN сверху
- Обход белых списков снизу
- Русские названия + ⚡ / 🎮
