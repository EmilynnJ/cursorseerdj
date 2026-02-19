# SoulSeer Documentation

Welcome to the SoulSeer codebase documentation. This directory contains comprehensive guides for developers, DevOps engineers, QA teams, and other stakeholders.

**Last Updated**: February 2026 | **Build Status**: Feature-Complete Production Build

---

## Quick Navigation

### For New Developers
1. **Start Here**: [Copilot Instructions](.github/copilot-instructions.md) - Architecture, patterns, and key conventions
2. **Data Model**: [DATA_MODEL.md](DATA_MODEL.md) - Full schema, relationships, and constraints
3. **Development Setup**: [DEPLOYMENT.md](DEPLOYMENT.md#local-development-setup) - How to run locally
4. **Testing**: [TESTING.md](TESTING.md) - Writing and running tests

### For DevOps / Deployment
1. **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md) - Heroku, Neon, Redis setup
2. **Environment Variables**: [DEPLOYMENT.md](DEPLOYMENT.md#environment-variables-env-file) - All required configs
3. **Monitoring**: [DEPLOYMENT.md](DEPLOYMENT.md#monitoring--maintenance) - Logs, alerts, troubleshooting

### For Security / Compliance
1. **Security Checklist**: [SECURITY_COMPLIANCE.md](SECURITY_COMPLIANCE.md) - GDPR, CCPA, PCI-DSS
2. **Feature Acceptance Criteria**: [FEATURE_ACCEPTANCE_CRITERIA.md](FEATURE_ACCEPTANCE_CRITERIA.md) - What's implemented vs. gaps

### For Product / QA
1. **Feature Acceptance Criteria**: [FEATURE_ACCEPTANCE_CRITERIA.md](FEATURE_ACCEPTANCE_CRITERIA.md) - Full feature list with acceptance criteria
2. **Manual Testing Checklist**: [TESTING.md](TESTING.md#manual-testing-checklist) - Test cases
3. **Data Model**: [DATA_MODEL.md](DATA_MODEL.md) - Understanding workflows and relationships

---

## Document Overview

### [`FEATURE_ACCEPTANCE_CRITERIA.md`](FEATURE_ACCEPTANCE_CRITERIA.md)
Comprehensive list of all features in SoulSeer with acceptance criteria, implementation status, and gaps.

**Covers**:
- On-Demand Readings (pay-per-minute)
- Scheduled Readings (flat-rate booking)
- Live Streaming + Gifting (70/30 split)
- Messaging (free + paid reply)
- Community (forums + moderation)
- Shop (Stripe-synced products)
- Role-based Dashboards (client/reader/admin)
- Wallet & Payments
- Agora Integration (RTC + RTM)
- External Integrations (Auth0, Stripe, etc.)

**Use When**: Planning development sprints, onboarding new developers, tracking build progress.

---

### [`DATA_MODEL.md`](DATA_MODEL.md)
Complete data model reference with ERDs, field definitions, constraints, and optimization guidelines.

**Covers**:
- Full schema relationships (Conceptual ERD)
- Model field definitions and constraints
- Key invariants (e.g., wallet.balance = sum(ledger))
- Idempotency patterns
- Database indexes and query optimization
- Data integrity rules

**Use When**: Understanding how data flows, designing migrations, optimizing queries.

---

### [`DEPLOYMENT.md`](DEPLOYMENT.md)
Step-by-step deployment and environment configuration guide.

**Covers**:
- Environment variables (.env template)
- Heroku deployment (Procfile, scaling, dyno types)
- Local development setup
- Database setup (Neon Postgres)
- Redis configuration
- Stripe webhook configuration
- Auth0 setup
- Agora configuration
- Monitoring and troubleshooting
- Scaling & performance

**Use When**: Deploying to production, configuring staging environments, troubleshooting deployment issues.

---

### [`SECURITY_COMPLIANCE.md`](SECURITY_COMPLIANCE.md)
Security and compliance checklist covering GDPR, CCPA, PCI-DSS, and operational security.

**Covers**:
- Authentication & Authorization (Auth0, RBAC, secrets)
- Data Protection (GDPR, CCPA, encryption, backups)
- PCI-DSS (Stripe integration, idempotency)
- API Security (rate limiting, webhooks, CORS)
- Audit Logging
- Compliance Policies (Privacy, ToS, Help Center)
- Third-party Integrations (compliance notes)
- Incident Response
- Monitoring & Alerts
- Pre-launch checklist

**Use When**: Security reviews, compliance audits, planning security improvements.

---

### [`TESTING.md`](TESTING.md)
Comprehensive testing guide with unit, integration, and E2E test examples.

**Covers**:
- Unit Tests (Wallet, Session state machine, Reader profile)
- Integration Tests (Billing tick, Auth0 callback, Stripe webhooks)
- End-to-End Tests (Booking flow)
- Test execution commands
- Manual testing checklist
- Performance testing (load testing, query optimization)
- CI/CD setup (GitHub Actions example)

**Use When**: Writing tests, setting up CI/CD, QA test planning.

---

### [`.github/copilot-instructions.md`](.github/copilot-instructions.md)
AI coding agent instructions and project conventions (20-50 lines, very focused).

**Covers**:
- Architecture overview
- Critical workflows (Session, Payment, Auth0)
- URL routing
- Model reference
- Project-specific conventions
- Common pitfalls & fixes
- Development commands
- Key files by feature

**Use When**: Onboarding AI agents, code generation, architecture clarification.

---

## Key Architecture Principles

### 1. **Django Monolith** (Not Microservices)
- Single codebase with clear app separation
- Each app handles one domain (accounts, readings, wallets, etc.)
- Shared database, no service-to-service calls

### 2. **Idempotency First**
- All async operations (billing, payments, webhooks) use idempotency_key
- Prevents double-charging on retry or webhook replay
- Example: `f"session_{session_id}_min_{billing_minutes + 1}"`

### 3. **Ledger-Based Accounting**
- All money movements are immutable LedgerEntry rows
- Wallet.balance = sum(ledger.amount)
- Enables auditability and prevents balance corruption

### 4. **State Machine for Sessions**
- Sessions follow strict state machine: created → waiting → active → paused → reconnecting → ended → finalized
- Enforced via Session.transition() method
- Prevents invalid state combinations

### 5. **Role-Based Access Control**
- UserProfile.role: client/reader/admin
- @require_role decorator enforces access
- Dashboard routes based on role
- All sensitive actions logged

### 6. **Auth0 OAuth2** (Not Django's Built-in)
- Users come from Auth0 only
- JWT signature verified against JWKS
- State token prevents CSRF on callback
- UserProfile created on first login with role='client'

### 7. **Stripe for Payments** (PCI Compliance)
- No card data stored locally (Stripe Checkout handles it)
- Webhooks idempotent via ProcessedStripeEvent
- All charges tracked in LedgerEntry with stripe_event_id

### 8. **Celery for Background Jobs**
- billing_tick() runs every 60s (CELERY_BEAT_SCHEDULE)
- Uses idempotency_key to prevent duplicate charges
- Runs on separate worker dyno in production

### 9. **Agora for Real-Time Media**
- RTC (voice/video): dynamic channel tokens, 20-min TTL
- RTM (chat): separate connection for livestream chat + gifting
- Tokens server-generated, short-lived

### 10. **Environment-Based Configuration**
- All secrets in .env (DATABASE_URL, STRIPE_SECRET_KEY, etc.)
- Never hardcoded, never in git
- Loaded via django-environ

---

## Development Workflow

### 1. Clone & Setup
```bash
git clone <repo>
cd cursorseerdj
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure .env
```bash
cp .env.example .env
# Fill in: DATABASE_URL, AUTH0_DOMAIN, STRIPE_SECRET_KEY, etc.
```

### 3. Migrate Database
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Locally
```bash
# Terminal 1: Web server
python manage.py runserver

# Terminal 2: Celery worker
celery -A soulseer worker -l info

# Terminal 3: Celery beat
celery -A soulseer beat -l info
```

### 5. Make Changes & Test
```bash
python manage.py test tests/
coverage run --source='.' manage.py test
coverage report
```

### 6. Deploy to Production
```bash
git push heroku main
heroku run python manage.py migrate
heroku ps:scale worker=1 beat=1
```

---

## Common Tasks

### Add a New Feature
1. **Plan**: Create migration with `python manage.py makemigrations --name feature_name`
2. **Implement**: Add view, URL route, template
3. **Secure**: Add @require_role if needed, audit logging
4. **Test**: Write unit + integration tests
5. **Document**: Update FEATURE_ACCEPTANCE_CRITERIA.md and copilot-instructions.md

### Add a Payment Operation
1. **Pattern**: Use `debit_wallet(wallet, amount, entry_type, idempotency_key, ...)`
2. **Idempotency**: Ensure idempotency_key is unique (use UUID if not tied to specific entity)
3. **Audit**: Log in AuditLog if admin action
4. **Test**: Test insufficient balance case

### Add a Webhook Handler
1. **Verify Signature**: Use Stripe.Webhook.construct_event() or equivalent
2. **Idempotency**: Check ProcessedStripeEvent before processing
3. **Store Event ID**: Create ProcessedStripeEvent record
4. **Retry Logic**: Return 200 on success to prevent re-delivery

### Deploy to Production
1. **Prepare**: Update .env, test migrations on staging
2. **Deploy**: `git push heroku main`
3. **Migrate**: `heroku run python manage.py migrate`
4. **Scale**: `heroku ps:scale web=2 worker=1 beat=1`
5. **Monitor**: Check Sentry, Heroku logs, UptimeRobot

---

## Troubleshooting

### Session Billing Not Working
- Check Celery beat is running: `celery -A soulseer beat -l info`
- Check Redis connection: `redis-cli ping`
- Check logs: `heroku logs --tail -p worker`
- Check database: `Session.objects.filter(state='active').count()`

### Stripe Webhook Not Processing
- Verify webhook endpoint in Stripe dashboard: `https://soulseer.com/stripe/webhook/`
- Check STRIPE_WEBHOOK_SIGNING_SECRET env var
- Review Sentry for webhook errors
- Test locally: `stripe listen --forward-to localhost:8000/stripe/webhook/`

### Auth0 Login Redirect Loop
- Verify AUTH0_DOMAIN and AUTH0_AUDIENCE env vars
- Check callback URL in Auth0 dashboard matches deployed URL
- Check state token generation: look for 'auth0_state' in session

### Database Connection Error
- Verify DATABASE_URL or PGHOST/PGUSER/PGPASSWORD
- Ensure SSL: sslmode=require (Neon requirement)
- Test: `psql $DATABASE_URL -c "SELECT 1"`

---

## Contact & Support

For questions or issues:
- **Security Issues**: Contact security@soulseer.com
- **Bug Reports**: Open GitHub issue with reproducible steps
- **Feature Requests**: Submit via feedback form or GitHub discussions

---

## License

Proprietary - SoulSeer Platform © 2026

---

## Changelog

**February 2026**:
- Initial documentation complete
- Feature-complete production build
- All 11 pillars implemented

**Previous Versions**: [See CHANGELOG.md](../CHANGELOG.md) if exists

