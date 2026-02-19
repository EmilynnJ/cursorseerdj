# SoulSeer Fly.io Deployment Guide

## Prerequisites

1. Install Fly.io CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Ensure you have all required API keys:
   - Neon Database connection string
   - Upstash Redis URL
   - Auth0 credentials
   - Stripe API keys
   - Agora App ID and Certificate

## Initial Setup

### 1. Create Fly.io App

```bash
fly apps create soulseer
```

### 2. Set Environment Variables

```bash
# Django
fly secrets set SECRET_KEY="your-secure-secret-key"
fly secrets set DEBUG="False"
fly secrets set ALLOWED_HOSTS="soulseer.fly.dev"

# Database (Neon)
fly secrets set DATABASE_URL="postgresql://..."

# Redis (Upstash)
fly secrets set REDIS_URL="rediss://..."

# Auth0
fly secrets set AUTH0_DOMAIN="your-domain.auth0.com"
fly secrets set AUTH0_APP_ID="your-app-id"
fly secrets set AUTH0_CLIENT_SECRET="your-client-secret"
fly secrets set AUTH0_AUDIENCE="your-api-identifier"

# Agora
fly secrets set AGORA_APP_ID="your-agora-app-id"
fly secrets set AGORA_SECURITY_CERTIFICATE="your-certificate"

# Stripe
fly secrets set STRIPE_SECRET_KEY="sk_..."
fly secrets set STRIPE_PUBLISHABLE_KEY="pk_..."
fly secrets set STRIPE_WEBHOOK_SIGNING_SECRET="whsec_..."

# Optional: R2/S3 for digital downloads
fly secrets set AWS_ACCESS_KEY_ID="..."
fly secrets set AWS_SECRET_ACCESS_KEY="..."
fly secrets set R2_BUCKET="soulseer-downloads"
fly secrets set R2_ENDPOINT="https://..."

# Optional: Sentry
fly secrets set SENTRY_DSN="..."
```

### 3. Deploy

```bash
fly deploy
```

## Architecture

### Processes

The app runs three processes:

1. **web**: Gunicorn WSGI server (handles HTTP requests)
2. **worker**: Celery worker (processes background tasks)
3. **beat**: Celery beat scheduler (triggers periodic tasks)

### Celery Tasks

- **billing-tick**: Every 60s - charges active sessions per minute
- **finalize-sessions**: Every 5min - finalizes ended sessions
- **reconnect-timeout**: Every 30s - ends sessions past grace period

### Database

Uses Neon Postgres with connection pooling (conn_max_age=600).

### Static Files

WhiteNoise serves static files with compression and manifest file handling.

## Scaling

### Scale Web Workers

```bash
fly scale count 2 --process-group web
```

### Scale Celery Workers

```bash
fly scale count 2 --process-group worker
```

## Monitoring

### Logs

```bash
fly logs
```

### Status

```bash
fly status
```

### Health Check

```bash
curl https://soulseer.fly.dev/health/
```

## Stripe Webhook Setup

Configure Stripe webhook endpoint:

```
https://soulseer.fly.dev/stripe/webhook/
```

Events to subscribe:
- `checkout.session.completed`
- `payment_intent.succeeded`

## Post-Deployment Verification

1. Check health endpoint: `curl https://soulseer.fly.dev/health/`
2. Test authentication flow
3. Create a test session
4. Verify Celery tasks are running (check logs)
5. Test wallet top-up flow
6. Test session billing

## Troubleshooting

### Database Connection Issues

If you see connection errors, the DATABASE_URL may need to include sslmode:
```
postgresql://user:pass@host/db?sslmode=require
```

### Static Files Not Loading

Run:
```bash
fly ssh console -C "python manage.py collectstatic --noinput"
```

### Celery Tasks Not Running

Check worker logs:
```bash
fly logs --process-group worker
```

Ensure Redis URL is correct and accessible.

## Maintenance

### Database Migrations

Migrations run automatically on deploy via `release_command` in fly.toml.

### Backup Strategy

Neon provides automatic backups. For additional safety, periodically export:
```bash
fly ssh console -C "python manage.py dumpdata > backup.json"
```

## Security Checklist

- [ ] SECRET_KEY is strong and unique
- [ ] DEBUG is False in production
- [ ] Stripe webhook secret is set
- [ ] Auth0 configuration is correct
- [ ] HTTPS is enforced
- [ ] Database uses SSL
- [ ] Redis uses SSL (rediss://)