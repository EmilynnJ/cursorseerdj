# SoulSeer Deployment & Environment Configuration Guide

**Last Updated**: February 2026 | **Platform**: Heroku (Docker-free) + Neon Postgres + Redis

## Environment Variables (.env file)

### Database (Neon Postgres)
```
DATABASE_URL=postgresql://user:password@host:port/db?sslmode=require
# OR individual vars:
PGHOST=ec2-xxx.compute-1.amazonaws.com
PGPORT=5432
PGUSER=neondb_owner
PGPASSWORD=your_password
PGDATABASE=neondb
PGSSLMODE=require
```

### Django
```
SECRET_KEY=generate-strong-random-string-here
DEBUG=False  # NEVER True in production
ALLOWED_HOSTS=soulseer.com,www.soulseer.com,soulseer-staging.herokuapp.com
```

### Auth0
```
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_AUDIENCE=https://soulseer-api.com
AUTH0_APP_ID=your_app_id_from_auth0
AUTH0_CLIENT_SECRET=your_client_secret_from_auth0
```

### Stripe
```
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SIGNING_SECRET=whsec_xxx
```

### Agora
```
AGORA_APP_ID=your_agora_app_id
AGORA_SECURITY_CERTIFICATE=your_agora_certificate
AGORA_CHAT_APP_ID=your_agora_chat_app_id
AGORA_CHAT_WEBSOCKET_ADDRESS=ws://your-agora-chat-api.com
AGORA_CHAT_REST_API=https://your-agora-chat-api.com
```

### Redis / Celery
```
REDIS_URL=redis://:password@host:port/0
CELERY_BROKER_URL=redis://:password@host:port/0
```

### AWS / Cloudflare R2
```
AWS_ACCESS_KEY_ID=your_r2_access_key
AWS_SECRET_ACCESS_KEY=your_r2_secret_key
AWS_STORAGE_BUCKET_NAME=soulseer-downloads
AWS_S3_REGION_NAME=auto
AWS_S3_ENDPOINT_URL=https://your-bucket.s3.cf.net  # Cloudflare R2
```

### Sentry
```
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### Email (optional, for GDPR deletion confirmation)
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=sg_live_xxx
DEFAULT_FROM_EMAIL=noreply@soulseer.com
```

---

## Heroku Deployment

### Prerequisites
- Heroku CLI installed
- Neon Postgres database created
- Redis add-on provisioned
- Auth0, Stripe, Agora accounts configured

### Step 1: Create Heroku App
```bash
heroku create soulseer-prod
# OR use existing app:
heroku apps:info soulseer-prod
```

### Step 2: Add Buildpacks
```bash
heroku buildpacks:add heroku/python
heroku buildpacks:add heroku/redis  # if using add-on
```

### Step 3: Set Environment Variables
```bash
heroku config:set \
  SECRET_KEY="your-secret-key" \
  DEBUG=False \
  DATABASE_URL="postgresql://..." \
  REDIS_URL="redis://..." \
  STRIPE_SECRET_KEY="sk_live_xxx" \
  # ... add all others
```

Or use a .env file:
```bash
heroku config:push -e .env.production
```

### Step 4: Create Heroku Procfile
```procfile
web: gunicorn soulseer.wsgi --log-file -
worker: celery -A soulseer worker -l info
beat: celery -A soulseer beat -l info
```

### Step 5: Deploy
```bash
git push heroku main
```

### Step 6: Run Migrations
```bash
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### Step 7: Scale Dynos
```bash
heroku ps:scale web=2 worker=1 beat=1
# or use:
heroku ps:type web=standard-2x  # production-grade dyno
```

---

## Local Development Setup

### 1. Create Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Create .env File
Copy `.env.example` to `.env` and fill in:
- Development DATABASE_URL (local or Neon)
- Auth0 credentials (dev Auth0 app)
- Stripe test keys (sk_test_xxx, pk_test_xxx)
- Agora test credentials

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Create Superuser
```bash
python manage.py createsuperuser
```

### 6. Start Dev Server
```bash
python manage.py runserver
# Visit http://localhost:8000
```

### 7. Start Celery (separate terminal)
```bash
celery -A soulseer worker -l info
```

### 8. Start Celery Beat (separate terminal)
```bash
celery -A soulseer beat -l info
```

---

## Database Setup (Neon Postgres)

### 1. Create Neon Project
- Go to neon.tech
- Create project (free tier available)
- Copy connection string

### 2. Verify SSL Connection
```bash
DATABASE_URL should include ?sslmode=require
psql postgresql://user:pass@host/db?sslmode=require  # Test connection
```

### 3. Run Migrations
```bash
python manage.py migrate
python manage.py migrate --database=default
```

---

## Redis Setup (for Celery & Cache)

### Heroku Redis Add-On
```bash
heroku addons:create heroku-redis:premium-0
# Auto-sets REDIS_URL env var
```

### Local Redis (Development)
```bash
# macOS
brew install redis
redis-server

# Windows (via WSL or docker)
docker run -d -p 6379:6379 redis:latest
```

### Test Redis Connection
```python
import redis
r = redis.from_url('redis://localhost:6379/0')
r.set('test', 'value')
r.get('test')  # Should return b'value'
```

---

## Stripe Webhook Configuration

### 1. Get Webhook Endpoint
```bash
# From Stripe Dashboard > Webhooks
# Create endpoint: POST https://soulseer.com/stripe/webhook/
```

### 2. Subscribe to Events
- `charge.succeeded`
- `charge.failed`
- `charge.refunded`
- `customer.subscription.deleted`

### 3. Local Testing (Stripe CLI)
```bash
stripe login
stripe listen --forward-to localhost:8000/stripe/webhook/
# Copy signing secret → STRIPE_WEBHOOK_SIGNING_SECRET
```

### 4. Verify Signature (in code)
```python
import stripe
event = stripe.Webhook.construct_event(
    payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
)
```

---

## Auth0 Configuration

### 1. Create Auth0 Application
- Tenant: your-tenant.auth0.com
- Application Type: Regular Web Application

### 2. Set Allowed Callbacks
```
http://localhost:8000/accounts/callback/
https://soulseer.com/accounts/callback/
```

### 3. Set Allowed Logout URLs
```
http://localhost:8000/
https://soulseer.com/
```

### 4. Copy Credentials
- Domain: your-tenant.auth0.com
- Client ID → AUTH0_APP_ID
- Client Secret → AUTH0_CLIENT_SECRET
- API Identifier → AUTH0_AUDIENCE

### 5. Enable Social Connections (optional)
- Google OAuth
- Facebook Login
- etc.

---

## Agora Setup

### 1. Get App ID & Certificate
- Agora Console: console.agora.io
- Create project
- Copy App ID → AGORA_APP_ID
- Copy Security Certificate (if using Token) → AGORA_CERTIFICATE

### 2. RTC Channel Configuration
- Use dynamic channel names (session_id based)
- Token TTL: 1200 seconds (20 min)
- Roles: Host (reader), Audience (client)

### 3. RTM (Chat) Configuration
- App ID → AGORA_CHAT_APP_ID
- WebSocket Address → AGORA_CHAT_WEBSOCKET_ADDRESS
- Use for livestream chat + gifting events

### 4. Test Token Generation
```python
from agora_token_builder import RtcTokenBuilder
token = RtcTokenBuilder.build_token_with_uid(
    app_id=settings.AGORA_APP_ID,
    app_certificate=settings.AGORA_CERTIFICATE,
    channel_name="test_channel",
    uid=123,
    expire_seconds=1200
)
```

---

## Monitoring & Maintenance

### Heroku Logs
```bash
heroku logs --tail  # Stream logs
heroku logs -n 100  # Last 100 lines
```

### Database Backups (Neon)
- Neon provides automatic backups (7-day retention free)
- Manual backup: `pg_dump` to local file

### Celery Monitoring
```bash
celery -A soulseer inspect active  # Running tasks
celery -A soulseer inspect stats   # Worker stats
```

### Sentry Monitoring
- Errors logged automatically
- Review in Sentry dashboard
- Set up alerts for critical errors

### Uptime Monitoring (optional)
- UptimeRobot: Monitor /health endpoint
- PagerDuty: Alert on errors from Sentry

---

## Scaling & Performance

### Database
- Neon: Scale via connection pooling for Celery
- Index fields: state (Session), modality (ReaderRate), status (ScheduledSlot)

### Redis
- Use separate Redis databases: 0 (Celery), 1 (Cache)
- Monitor memory usage

### Celery
- Worker dynos: Start with 1, scale to 2+ for production
- Beat dyno: 1 (single)

### CDN (optional)
- Cloudflare: Cache static assets
- R2: Edge-cached file downloads

---

## Security Checklist

- [ ] SECRET_KEY is strong random string (32+ chars)
- [ ] DEBUG=False in production
- [ ] ALLOWED_HOSTS correctly configured
- [ ] HTTPS enforced (Heroku provides free cert)
- [ ] Secrets NOT in version control (.env in .gitignore)
- [ ] CORS configured for API endpoints
- [ ] Rate limiting enabled (optional but recommended)
- [ ] Sentry DSN configured
- [ ] Staff user created (for admin access)
- [ ] Stripe webhook secret verified in code

---

## Troubleshooting

### 502 Bad Gateway
- Check Heroku logs: `heroku logs --tail`
- Verify database connection (DATABASE_URL correct)
- Check if web dyno is running: `heroku ps`

### Celery Tasks Not Running
- Verify worker dyno is active: `heroku ps`
- Check Redis connection: `heroku redis:info`
- Inspect tasks: `celery -A soulseer inspect active`

### Auth0 Redirect Loop
- Verify AUTH0_DOMAIN and AUTH0_AUDIENCE
- Check callback URL in Auth0 dashboard matches deployed URL

### Stripe Webhook Not Working
- Verify webhook endpoint URL in Stripe dashboard
- Check STRIPE_WEBHOOK_SIGNING_SECRET env var
- Review Stripe webhook logs for errors

---

## Disaster Recovery

### Full Database Backup
```bash
pg_dump $(heroku config:get DATABASE_URL) > backup.sql
# Restore:
psql $(heroku config:get DATABASE_URL) < backup.sql
```

### Rebuild from Scratch
```bash
heroku destroy --app soulseer-prod
# Create new app, set env vars, deploy, migrate, done
```
