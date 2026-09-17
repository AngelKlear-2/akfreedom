# akfreedom / МАРУСЯ VPN

Авто-обновляемые рабочие конфиги для России (МТС + Ростелеком).

## Подписки

- **Основная (mixed)**: https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/vpn.txt
- **Black lists** (обычные): https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/blacklist.txt
- **White lists** (обход БС / CIDR): https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/whitelist.txt
- **config.txt** (для клиентов): https://raw.githubusercontent.com/AngelKlear-2/akfreedom/main/config.txt

## Скрипт проверки

`checker.py` — каждые N минут:
1. Качает свежие списки с Igareck и др.
2. Проверяет TCP + latency
3. Оставляет только рабочие
4. Пушит обратно в этот репозиторий

### Как запустить

```bash
pip install requests PyGithub
export GITHUB_TOKEN=ghp_ваш_токен
python checker.py
```

Можно повесить на cron, GitHub Actions или Vercel Cron.

## Шаблон

- Обычные VPN сверху
- Обход белых списков снизу
- Русские названия + ⚡ / 🎮
