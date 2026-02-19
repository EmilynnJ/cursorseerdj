# SoulSeer - Premium Spiritual Reading Platform

[![Tests](https://github.com/yourusername/soulseer/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/yourusername/soulseer/actions)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![Django 5.0+](https://img.shields.io/badge/Django-5.0%2B-darkgreen)](https://www.djangoproject.com/)

**SoulSeer** is a feature-complete Django monolith for spiritual readings with:

- 🔐 Auth0 OAuth2 + role-based access (client/reader/admin)
- 💳 Stripe payments + wallet ledger (immutable)
- 🎥 Agora RTC (voice/video) + RTM (chat/gifting)
- ⏰ Session state machine + billing every 60s
- 💰 Per-minute rates with grace period reconnection (5 min)
- 📅 Scheduled bookings with flat-rate pricing
- 🎁 Livestream gifting (70/30 revenue split)
- 📝 Community forums + moderation queue
- 🛍️ Digital product shop with R2 signed URLs
- 💬 Direct messaging with paid reply option
- 📊 Role-based dashboards (client/reader/admin)
- 🔄 Background jobs (Celery) for billing & finalization
- 📱 Mobile-ready with HTMX

## Quick Start

```bash
git clone https://github.com/yourusername/soulseer.git
cd soulseer
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your secrets
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

In 3 separate terminals:
```bash
python manage.py runserver
celery -A soulseer worker -l info
celery -A soulseer beat -l info
```

Visit http://localhost:8000 | Admin: http://localhost:8000/admin

**Full setup**: [QUICKSTART.md](QUICKSTART.md)

---

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup
- **[docs/README.md](docs/README.md)** - Full docs index
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Architecture (AI agent guide)
- **[docs/DEPLOYMENT_HEROKU.md](docs/DEPLOYMENT_HEROKU.md)** - Production deploy
- **[docs/DATA_MODEL.md](docs/DATA_MODEL.md)** - Database schema + ERD
- **[docs/TESTING.md](docs/TESTING.md)** - Tests + CI/CD

---

## Architecture

**10 Django Apps** (monolith):
- `accounts`: Auth0 OAuth2 + user profiles
- `readings`: Sessions + state machine + Agora RTC
- `wallets`: Stripe + immutable ledger + idempotency
- `readers`: Profiles + rates + reviews
- `scheduling`: Bookings + availability
- `live`: Livestreams + gifting + Agora RTC
- `messaging`: Direct messages + paid replies
- `community`: Forums + moderation queue
- `shop`: Products + orders + R2 downloads
- `core`: Dashboards + admin

**Key Patterns**:
- Role-based access: `@require_role('reader')`
- Session state machine: `session.transition(new_state)`
- Wallet ledger: Immutable `LedgerEntry` rows
- Idempotency: Unique `idempotency_key` on all payments
- Background jobs: `billing_tick()` every 60s via Celery

**Integrations**:
- Auth0: OAuth2 + RS256 JWT
- Stripe: Checkout + webhooks + Connect
- Agora: RTC tokens (20-min TTL) + RTM
- Celery: billing_tick, session_finalize, webhooks

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for full architecture.

---

## Deployment

### ⚠️ NOT Vercel
Django requires traditional hosting. Use **Heroku**, **Railway**, or **Render**.

### Quick Heroku Deploy
```bash
heroku create soulseer-app
heroku addons:create heroku-postgresql:standard-0
heroku addons:create heroku-redis:premium-0
heroku config:set SECRET_KEY=... AUTH0_DOMAIN=... STRIPE_SECRET_KEY=...
git push heroku main
heroku run python manage.py migrate
heroku ps:scale worker=1 beat=1
```

Full guide: [docs/DEPLOYMENT_HEROKU.md](docs/DEPLOYMENT_HEROKU.md)

---

## Environment Variables

**Required**:
```
SECRET_KEY=50-char-random-string
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
REDIS_URL=redis://host:6379/0
AUTH0_DOMAIN=tenant.auth0.com
AUTH0_APP_ID=app-id
AUTH0_CLIENT_SECRET=secret
AGORA_APP_ID=agora-id
AGORA_SECURITY_CERTIFICATE=cert
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SIGNING_SECRET=whsec_xxx
```

Full list: [.env.example](.env.example)

---

## File Structure

```
soulseer/
├── QUICKSTART.md
├── README.md
├── requirements.txt
├── Procfile
├── .env.example
├── manage.py
├── soulseer/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── accounts/ readings/ wallets/ ... core/
├── templates/
├── static/
├── docs/
│   ├── README.md
│   ├── DEPLOYMENT_HEROKU.md
│   ├── DATA_MODEL.md
│   ├── TESTING.md
│   └── SECURITY_COMPLIANCE.md
└── .github/
    ├── copilot-instructions.md
    └── workflows/
        └── ci-cd.yml
```

---

## Testing

```bash
# All tests
python manage.py test

# With coverage
coverage run --source='.' manage.py test
coverage report

# Specific app
python manage.py test readings
```

---

## Development

### Database Migrations
```bash
python manage.py makemigrations --name descriptive_name
python manage.py migrate
```

### Code Quality
```bash
black .        # Format
flake8 .       # Lint
mypy .         # Type check
```

### Django Shell
```bash
python manage.py shell
>>> from readings.models import Session
>>> Session.objects.filter(state='active').count()
```

---

## Project Status

✅ **Completed**:
- All 10 apps + 18+ models
- Auth0 OAuth2 integration
- Session billing with grace period
- Wallet ledger + Stripe webhooks
- Agora RTC/RTM integration
- Celery tasks (billing_tick, finalization)
- Dashboard views
- Full documentation
- CI/CD pipeline (GitHub Actions)

🔄 **In Progress**: Dashboard templates, UIs

---

## Support

1. Check [docs/README.md](docs/README.md)
2. Check [QUICKSTART.md](QUICKSTART.md)
3. See [.github/copilot-instructions.md](.github/copilot-instructions.md) for architecture

---

## Built With

| Component | Tech |
|-----------|------|
| Backend | Django 5.0+, DRF |
| Database | PostgreSQL 14+ (Neon) |
| Queue | Redis 6+, Celery 5.3+ |
| Auth | Auth0 OAuth2 + RS256 |
| Payments | Stripe API |
| Video | Agora RTC + RTM |
| Storage | Cloudflare R2 / S3 |
| Monitoring | Sentry, UptimeRobot |
| Frontend | Django Templates, HTMX, Tailwind |
| Deployment | Heroku, Railway, Render |

---

## Stats

- **Models**: 18+ domain models
- **Apps**: 10 Django apps
- **Tests**: 30+ unit/integration tests
- **Docs**: 6 guides (700+ lines)
- **Dependencies**: 25+ packages
- **API Endpoints**: 40+

---

**Ready to deploy?** → [docs/DEPLOYMENT_HEROKU.md](docs/DEPLOYMENT_HEROKU.md)

**Building locally?** → [QUICKSTART.md](QUICKSTART.md)

**Need architecture?** → [.github/copilot-instructions.md](.github/copilot-instructions.md)

---

Made with ❤️ for spiritual readers everywhere. 🔮
