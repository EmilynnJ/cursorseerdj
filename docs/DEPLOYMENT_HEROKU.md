# SoulSeer Deployment Guide - Heroku / Railway / Render

**IMPORTANT NOTE**: SoulSeer is a Django monolith that **cannot be deployed to Vercel** (serverless). Vercel is for static sites and serverless functions. Django requires a traditional application server like Heroku, Railway, or Render.

## Quick Start: Deploy to Heroku (Recommended for Beginners)

### Prerequisites
- Heroku CLI installed ([heroku-cli](https://devcenter.heroku.com/articles/heroku-cli))
- Git repository initialized
- All environment variables ready

### Step 1: Create Heroku App
```bash
heroku create soulseer-app
```

### Step 2: Provision Resources
```bash
# PostgreSQL database (Heroku Postgres)
heroku addons:create heroku-postgresql:standard-0 --app=soulseer-app

# Redis for Celery (Heroku Redis)
heroku addons:create heroku-redis:premium-0 --app=soulseer-app
```

### Step 3: Set Environment Variables
```bash
heroku config:set \
  SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" \
  DEBUG=False \
  ALLOWED_HOSTS=soulseer-app.herokuapp.com \
  AUTH0_DOMAIN=your-tenant.auth0.com \
  AUTH0_APP_ID=your-app-id \
  AUTH0_CLIENT_SECRET=your-secret \
  AGORA_APP_ID=your-agora-id \
  AGORA_SECURITY_CERTIFICATE=your-cert \
  STRIPE_SECRET_KEY=sk_live_xxx \
  STRIPE_WEBHOOK_SIGNING_SECRET=whsec_xxx \
  --app=soulseer-app
```

### Step 4: Deploy
```bash
git push heroku main  # or your main branch
heroku logs --tail  # monitor deployment
```

### Step 5: Run Migrations
```bash
heroku run python manage.py migrate --app=soulseer-app
heroku run python manage.py createsuperuser --app=soulseer-app
```

### Step 6: Configure Dyno Types
```bash
# Scale web dyno (API/views)
heroku dyno:scale web=1:standard-2x --app=soulseer-app

# Scale worker dyno (Celery worker)
heroku dyno:scale worker=1:standard-2x --app=soulseer-app

# Scale beat dyno (Celery scheduler)
heroku dyno:scale beat=1:standard-1x --app=soulseer-app
```

---

## Alternative: Railway.app (Easier Setup)

### Step 1: Connect Repository
1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub"
3. Select the SoulSeer repository

### Step 2: Add Services
- Railway auto-detects Python/Django
- Add **PostgreSQL** service
- Add **Redis** service

### Step 3: Configure Environment
In Railway UI:
```
PROJECT_ID → Variables:
DEBUG=False
SECRET_KEY=your-secret
AUTH0_DOMAIN=...
STRIPE_SECRET_KEY=...
(copy all from .env.example)
```

### Step 4: Deploy
Push to main branch → Railway auto-deploys

---

## Database Setup (Both Heroku & Railway)

### Option 1: Neon PostgreSQL (Recommended)
1. Sign up at [neon.tech](https://neon.tech)
2. Create project → copy connection string
3. Set `DATABASE_URL` env var (includes SSL by default)

```bash
# Test connection
psql "your-database-url"
```

### Option 2: Heroku Postgres
```bash
heroku addons:create heroku-postgresql:standard-0
# DATABASE_URL auto-populated
```

### Verify Database
```bash
python manage.py dbshell  # connects using DATABASE_URL
```

### Run Migrations
```bash
python manage.py migrate
python manage.py migrate --run-syncdb  # if needed
```

---

## Redis Setup (Celery Broker)

### Heroku Redis
```bash
heroku addons:create heroku-redis:premium-0
# REDIS_URL auto-populated
```

### External Redis (Redis Cloud, Upstash, etc.)
```bash
# Set manually
heroku config:set REDIS_URL=redis://:password@host:port/0
```

### Test Connection
```bash
# From Django shell
python manage.py shell
>>> import redis
>>> r = redis.from_url('redis://localhost:6379/0')
>>> r.ping()
True
```

---

## Celery Configuration

### Background Workers
Procfile defines 3 process types:

1. **web**: Django app server (handles requests)
2. **worker**: Celery worker (executes tasks)
3. **beat**: Celery beat scheduler (runs `billing_tick` every 60s)

### Scaling
```bash
# More workers for high concurrency
heroku dyno:scale worker=2 --app=soulseer-app

# More beat schedulers (only 1 needed)
heroku dyno:scale beat=1 --app=soulseer-app
```

### Monitor Tasks
```bash
heroku logs --dyno worker --tail --app=soulseer-app
heroku logs --dyno beat --tail --app=soulseer-app
```

### Common Issues
- **Tasks not running**: Check Redis connection, verify REDIS_URL set
- **Billing not charging**: Check beat process is running, check logs for errors
- **Task hangs**: Increase worker timeout in settings.py (CELERY_TASK_TIME_LIMIT)

---

## Third-Party Integration Setup

### Auth0
1. Create OAuth app at [auth0.com](https://auth0.com)
2. Set **Allowed Callback URLs**:
   ```
   https://soulseer-app.herokuapp.com/accounts/callback/
   ```
3. Set **Allowed Logout URLs**:
   ```
   https://soulseer-app.herokuapp.com/
   ```
4. Copy credentials to environment:
   ```bash
   heroku config:set AUTH0_DOMAIN=your-tenant.auth0.com \
     AUTH0_APP_ID=your-app-id \
     AUTH0_CLIENT_SECRET=your-secret
   ```

### Stripe
1. Create Stripe account at [stripe.com](https://stripe.com)
2. Get keys from Dashboard → API Keys
3. Configure webhook endpoint:
   - **URL**: `https://soulseer-app.herokuapp.com/stripe/webhook/`
   - **Events**: `charge.succeeded`, `charge.refunded`, `payment_intent.succeeded`
4. Copy signing secret to environment:
   ```bash
   heroku config:set STRIPE_WEBHOOK_SIGNING_SECRET=whsec_xxx
   ```

### Agora (Voice/Video)
1. Create account at [agora.io](https://agora.io)
2. Create project → enable RTC & RTM
3. Get App ID & Certificate
4. Set environment:
   ```bash
   heroku config:set AGORA_APP_ID=xxx AGORA_SECURITY_CERTIFICATE=yyy
   ```

### R2 / S3 (Digital Delivery)
1. For R2: Create bucket at [dash.cloudflare.com](https://dash.cloudflare.com)
2. Create API token → copy credentials
3. Set environment:
   ```bash
   heroku config:set AWS_ACCESS_KEY_ID=xxx AWS_SECRET_ACCESS_KEY=yyy
   ```

---

## Monitoring & Logging

### Heroku Logs
```bash
# View recent logs
heroku logs --tail --app=soulseer-app

# Filter by dyno
heroku logs --dyno web --app=soulseer-app
heroku logs --dyno worker --app=soulseer-app

# Search for errors
heroku logs --source app --tail | grep ERROR
```

### Sentry (Error Tracking)
1. Create account at [sentry.io](https://sentry.io)
2. Create Django project → copy DSN
3. Set environment:
   ```bash
   heroku config:set SENTRY_DSN=https://xxx@sentry.io/project-id
   ```
4. Logs automatically sent on errors

### UptimeRobot (Monitoring)
1. Set up at [uptimerobot.com](https://uptimerobot.com)
2. Monitor endpoint: `https://soulseer-app.herokuapp.com/`
3. Alerts on downtime

---

## Production Checklist

- [ ] DEBUG=False in all environments
- [ ] ALLOWED_HOSTS set to production domain
- [ ] SECRET_KEY is cryptographically strong (50+ chars)
- [ ] HTTPS enforced (Django settings + Heroku)
- [ ] Database backups enabled
- [ ] Redis backups enabled
- [ ] Stripe webhooks configured
- [ ] Auth0 callback URLs updated
- [ ] Agora credentials set
- [ ] Celery workers running (check `heroku ps`)
- [ ] Celery beat running (check `heroku ps`)
- [ ] Migrations applied successfully
- [ ] Static files collected (`whitenoise` auto-handles this)
- [ ] Sentry DSN set
- [ ] Email provider configured (SendGrid/etc.)
- [ ] Monitor services set up (UptimeRobot, Sentry)
- [ ] SSL/TLS certificate valid
- [ ] Rate limiting middleware enabled
- [ ] CORS headers configured if frontend is separate
- [ ] Admin accessible at `/admin/`

---

## Troubleshooting

### 502 Bad Gateway
```bash
# Check web dyno logs
heroku logs --dyno web --tail

# Common causes:
# - Database connection failed (check DATABASE_URL)
# - Static files not collected (whitenoise should auto-handle)
# - Unhandled exception in app (check Sentry)
```

### Celery Tasks Not Running
```bash
# Verify beat is running
heroku ps
# Should show: beat (1x standard-1x) up

# Verify worker is running
# Should show: worker (1x standard-2x) up

# Check Redis connection
heroku run redis-cli --app=soulseer-app

# Check task queue
heroku run python manage.py shell
>>> from celery import current_app
>>> current_app.control.inspect().active()
```

### Billing Not Charging
```bash
# Check if billing_tick is running
heroku logs --dyno beat --tail --grep "billing_tick"

# Check if tasks are executing
heroku logs --dyno worker --tail --grep "billing_tick"

# Manually trigger (for testing)
heroku run python manage.py shell
>>> from readings.tasks import billing_tick
>>> billing_tick()
```

### Database Connection Issues
```bash
# Test connection directly
heroku run python manage.py dbshell

# Check DATABASE_URL is set
heroku config | grep DATABASE_URL

# Reset database (CAUTION: deletes all data)
heroku addons:destroy heroku-postgresql --confirm=soulseer-app
heroku addons:create heroku-postgresql:standard-0
heroku run python manage.py migrate
```

### Static Files Not Loading
```bash
# Collect static files
heroku run python manage.py collectstatic --noinput

# Verify staticfiles directory exists
heroku run ls staticfiles/

# Note: whitenoise middleware auto-serves from STATIC_ROOT
```

---

## Disaster Recovery

### Backup Database
```bash
# Heroku automatic backups (7-day retention with standard-0+)
heroku pg:backups:scheduled --app=soulseer-app

# Manual backup
heroku pg:backups:capture --app=soulseer-app

# Download backup
heroku pg:backups:download --app=soulseer-app
```

### Restore from Backup
```bash
# List backups
heroku pg:backups --app=soulseer-app

# Restore
heroku pg:backups:restore b010 DATABASE --app=soulseer-app --confirm=soulseer-app
```

### Scale Down (Cost Reduction)
```bash
# Heroku free tier only supports 1 free dyno per app (web)
# Minimum paid: web (standard-1x ~$50/mo) + worker + beat

# For smaller deployments:
heroku dyno:scale worker=0 beat=0 --app=soulseer-app
# (disables background jobs - NOT recommended for production)
```

---

## Cost Estimation (Heroku Monthly)

- **Web dyno**: $50 (standard-1x minimum)
- **Worker dyno**: $50 (for Celery tasks)
- **Beat dyno**: $50 (for Celery scheduler) - can share with worker
- **PostgreSQL**: $50-200 (depending on DB size)
- **Redis**: $30-100 (depending on usage)
- **Total**: ~$200-350/month

**Cost Reduction Options**:
1. Use **Railway** instead (usage-based pricing, usually $20-50/mo)
2. Use external databases (**Neon** for Postgres, **Upstash** for Redis) - can reduce to $100/mo
3. Auto-scale dynos during off-hours (Heroku Autoscaling - extra cost)

---

## Testing After Deploy

```bash
# Test authentication
curl https://soulseer-app.herokuapp.com/accounts/login/

# Test API
curl https://soulseer-app.herokuapp.com/api/sessions/1/rtc-token/

# Test admin
open https://soulseer-app.herokuapp.com/admin/

# Test Stripe webhook
curl -X POST https://soulseer-app.herokuapp.com/stripe/webhook/ \
  -H "stripe-signature: test" \
  -d '{"type": "charge.succeeded"}'

# Monitor logs
heroku logs --tail --app=soulseer-app
```

---

## Next Steps

1. ✅ Deploy to Heroku/Railway
2. ✅ Configure all 3rd party integrations
3. ✅ Run migrations & create admin user
4. ✅ Test end-to-end user flows
5. ✅ Monitor production logs (Sentry, UptimeRobot)
6. ✅ Enable daily backups
7. ✅ Set up team access in Heroku/Railway
8. ✅ Document deployment runbook for team

For questions, see [docs/README.md](docs/README.md) or Django docs at [docs.djangoproject.com](https://docs.djangoproject.com).
