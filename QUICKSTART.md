# SoulSeer Quick Start Guide

Get SoulSeer running locally in 10 minutes.

## Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Git

## Local Setup

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/soulseer.git
cd soulseer
```

### 2. Create Virtual Environment
```bash
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```dotenv
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:password@localhost:5432/soulseer
REDIS_URL=redis://localhost:6379/0
```

### 5. Database Setup
```bash
# Create database (if using local PostgreSQL)
createdb soulseer

# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

### 6. Run Server
```bash
# Terminal 1: Django development server
python manage.py runserver

# Terminal 2: Celery worker
celery -A soulseer worker -l info

# Terminal 3: Celery beat scheduler
celery -A soulseer beat -l info
```

Visit:
- App: http://localhost:8000
- Admin: http://localhost:8000/admin

---

## Development Workflow

### Running Tests
```bash
# All tests
python manage.py test

# Specific app
python manage.py test readings

# With coverage
coverage run --source='.' manage.py test
coverage report
```

### Database Migrations
```bash
# Create migration
python manage.py makemigrations --name descriptive_name

# Apply migration
python manage.py migrate

# Check status
python manage.py showmigrations
```

### Django Shell
```bash
python manage.py shell

# Examples:
>>> from accounts.models import UserProfile
>>> from readings.models import Session
>>> Session.objects.filter(state='active').count()
5
>>> # Create test data
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> u = User.objects.create(username='test')
>>> u.profile.role = 'client'
>>> u.save()
```

### Reset Database (Development Only)
```bash
# DELETE all data
python manage.py flush --no-input
python manage.py migrate
python manage.py createsuperuser
```

---

## Code Quality

### Formatting (Black)
```bash
# Format all Python files
black .

# Check formatting
black --check .
```

### Linting (Flake8)
```bash
pip install flake8
flake8 .
```

### Type Checking (mypy)
```bash
pip install mypy
mypy .
```

---

## Common Tasks

### Add App
```bash
python manage.py startapp myapp
# Then add to INSTALLED_APPS in settings.py
```

### Generate Secret Key
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### Check Deployment Readiness
```bash
python manage.py check --deploy
```

### Collect Static Files
```bash
python manage.py collectstatic --noinput
```

---

## Troubleshooting

### Database Connection Error
```
Error: could not connect to server
```
- Ensure PostgreSQL is running: `psql --version`
- Check DATABASE_URL is correct: `echo $DATABASE_URL`
- Create database: `createdb soulseer`

### Redis Connection Error
```
Error: Connection refused
```
- Start Redis: `redis-server` (macOS: `brew services start redis`)
- Check REDIS_URL: should be `redis://localhost:6379/0`

### Celery Tasks Not Running
- Verify worker is running in separate terminal
- Check logs: `celery -A soulseer worker -l debug`
- Test task: `python manage.py shell` then `from readings.tasks import billing_tick; billing_tick()`

### Static Files Not Loading
```bash
python manage.py collectstatic --noinput
```

### Port Already in Use (8000)
```bash
python manage.py runserver 8001
```

---

## Next Steps

1. ✅ Read [.github/copilot-instructions.md](../.github/copilot-instructions.md) for architecture
2. ✅ Check [docs/README.md](docs/README.md) for full documentation
3. ✅ Review [docs/DATA_MODEL.md](docs/DATA_MODEL.md) for schema
4. ✅ Look at [docs/TESTING.md](docs/TESTING.md) for test examples
5. ✅ Deploy to production with [docs/DEPLOYMENT_HEROKU.md](docs/DEPLOYMENT_HEROKU.md)

---

## File Structure

```
soulseer/
├── manage.py                 # Django CLI
├── requirements.txt          # Dependencies
├── Procfile                  # Heroku/production
├── .env.example              # Environment template
├── soulseer/                 # Main config
│   ├── settings.py           # Django settings
│   ├── urls.py               # URL routing
│   ├── wsgi.py               # WSGI app
│   └── celery.py             # Celery config
├── accounts/                 # Auth + User profiles
├── readings/                 # Session + Billing
├── wallets/                  # Stripe + Ledger
├── readers/                  # Reader profiles + rates
├── scheduling/               # Bookings
├── live/                     # Livestreams
├── messaging/                # Direct messages
├── community/                # Forums + moderation
├── shop/                     # Products + orders
├── core/                     # Dashboards + admin
├── static/                   # CSS, JS, images
├── templates/                # HTML templates
├── docs/                     # Documentation
│   ├── README.md             # Docs navigation
│   ├── DEPLOYMENT_HEROKU.md  # Production deploy
│   ├── SECURITY_COMPLIANCE.md
│   ├── TESTING.md
│   └── DATA_MODEL.md
└── .github/
    ├── copilot-instructions.md   # AI agent guide
    └── workflows/
        └── ci-cd.yml             # GitHub Actions
```

---

## Key Files to Know

| File | Purpose |
|------|---------|
| [soulseer/settings.py](soulseer/settings.py) | All Django config |
| [accounts/models.py](accounts/models.py) | User + Auth0 integration |
| [readings/models.py](readings/models.py) | Session state machine |
| [wallets/models.py](wallets/models.py) | Wallet ledger + Stripe |
| [readings/tasks.py](readings/tasks.py) | Celery tasks (billing) |
| [readings/agora_views.py](readings/agora_views.py) | RTC token generation |
| [core/dashboard_views.py](core/dashboard_views.py) | User dashboards |
| [wallets/webhooks.py](wallets/webhooks.py) | Stripe webhooks |

---

## Environment Variables Reference

| Variable | Default | Example |
|----------|---------|---------|
| DEBUG | False | True (local only) |
| SECRET_KEY | None | 50+ char random string |
| DATABASE_URL | None | postgresql://user:pass@host/db |
| REDIS_URL | redis://localhost:6379/0 | redis://:pass@host:6379 |
| AUTH0_DOMAIN | None | tenant.auth0.com |
| AUTH0_APP_ID | None | app-id |
| AGORA_APP_ID | None | agora-app-id |
| STRIPE_SECRET_KEY | None | sk_live_xxx |

Full list in `.env.example`

---

## Support

- **Architecture**: See `.github/copilot-instructions.md`
- **Deployment**: See `docs/DEPLOYMENT_HEROKU.md`
- **Testing**: See `docs/TESTING.md`
- **Models**: See `docs/DATA_MODEL.md`
- **Troubleshooting**: See this file's "Troubleshooting" section

Happy coding! 🚀
