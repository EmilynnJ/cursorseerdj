# SoulSeer Copilot Instructions

**Project**: Premium spiritual reading platform (Django monolith + Agora RTC/RTM + Stripe + Auth0)

**Last Updated**: February 2026 | **Build Status**: Feature-Complete Production Build

## Architecture Overview

SoulSeer is a **Django 5.0+ monolith** with clear app separation (not microservices):

- **accounts**: Auth0 OAuth2 integration, user profiles (UserProfile with roles: client/reader/admin), data export/deletion (GDPR)
- **readings**: Core session model (text/voice/video, state machine), billing state machine, Agora RTC integration, session notes/summaries
- **wallets**: Stripe payment integration, ledger-based balance tracking (immutable), idempotency keys, refund/chargeback handling
- **readers**: Reader profiles, rates (per-modality), availability (weekly slots), reviews (1-5 rating), favorites
- **live**: Livestream channels (public/private/premium), gifting (70/30 revenue split tracked in ledger)
- **messaging**: Direct user messaging, paid reply option ($1 charge)
- **community**: Forums/discussions, flagging system, moderation queue
- **scheduling**: Scheduled sessions (15/30/45/60 min flat-rate), booking flow, cancellation rules
- **shop**: Digital + physical products, Stripe product sync, coupons, R2 signed URL delivery
- **core**: Role-based dashboards (client/reader/admin), audit logs, moderation queue UI

**Key Integration Points**:
- Auth0 (OAuth2 + JWT validation) → User creation/login, role assignment
- Stripe webhooks → Wallet balance updates (idempotent via event_id tracking)
- Stripe Connect → Reader payouts (future)
- Agora RTC (voice/video) → Session channel tokens (20-min TTL)
- Agora RTM (presence/messaging) → Live chat + gifting events
- Celery beat (Redis) → `billing_tick()` every 60s charges active sessions, handles low-balance auto-pause
- PostgreSQL (Neon) → All persistent data, sslmode=require

## Critical Workflows & Implementation Patterns

### Session Lifecycle (readings app)
```
created → waiting → active ⇄ paused → reconnecting → ended → finalized
                      ↓ (charges every minute via Celery)
```
- **Session model**: `Session(client, reader, modality, state, rate_per_minute, billing_minutes, grace_until, reconnect_count, summary)`
- `rate_per_minute` is set from ReaderRate(reader, modality, rate_per_minute)
- Client wallet must have balance ≥ rate before session starts
- `billing_tick()` charges every 60s: creates LedgerEntry with idempotency_key `f"session_{session_id}_min_{billing_minutes+1}"`
- If balance < rate during tick, auto-transitions to 'paused'
- `grace_until` timestamp (set on disconnect) prevents rapid reconnect loops → must wait or transition to 'ended'
- Session summary recorded in `summary` field on finalization

### Role-Based Access Pattern
```python
from accounts.decorators import require_role

@login_required
@require_role('reader')  # or 'admin' or ('reader', 'admin')
def reader_only_view(request):
    profile = request.user.profile  # UserProfile(role='reader|client|admin')
    return render(request, 'template.html')
```
- **UserProfile** has role field (client/reader/admin), created on Auth0 signup
- Decorator checks `request.user.profile.role` and redirects to dashboard if no match
- All dashboards role-aware: `/dashboard/` routes to client/reader/admin based on role

### Dashboard Views
- **Client Dashboard** (`core/client_dashboard.html`): wallet balance, transaction history, upcoming bookings, favorites, session notes
- **Reader Dashboard** (`core/reader_dashboard.html`): earnings (session + gifts), session history, scheduled bookings, rates/availability management, reviews/rating
- **Admin Dashboard** (`core/admin_dashboard.html`): pending reader onboarding, moderation queue, recent refunds, platform stats (users, sessions, revenue)

### Payment Flow (wallets app)
1. **Wallet Creation**: Auto-created for every user on signup
2. **Top-up**: Client uses Stripe Checkout → webhook → `credit_wallet(wallet, amount, 'top_up', idempotency_key)` (idempotent)
3. **Session Charge**: `billing_tick()` calls `debit_wallet(wallet, rate, 'session_charge', idempotency_key, session=session)`
4. **Other Charges**: booking (`booking`), paid reply (`paid_reply`), gift (`gift`)
5. **Ledger Immutability**: All changes via LedgerEntry; wallet.balance = sum(ledger.amount)
6. **Stripe Reconciliation**: Store `stripe_event_id` in LedgerEntry; ProcessedStripeEvent tracks webhook processing to prevent re-processing

### Scheduled Readings Flow
1. **Reader Sets Availability**: `ReaderAvailability(reader, day_of_week, start_time, end_time)` → weekly repeating
2. **Slots Generated**: `ScheduledSlot(reader, start, end, duration_minutes, client, status)` created from availability or manually
3. **Client Books**: POST to `/scheduling/book/<slot_id>/` → charges wallet with flat rate based on duration
4. **Cancellation**: `Booking.cancelled_at` set; refund issued; slot status → 'cancelled'

### Reader Profile & Reviews
- **ReaderProfile**: `slug` (unique), `bio`, `avatar_url`, `specialties`, `is_verified`, `stripe_connect_account_id`
- **ReaderRate**: `(reader, modality, rate_per_minute)` unique_together; modalities: text/voice/video
- **Review**: `(reader, client, session, rating 1-5, body, created_at)`; avg rating calculated via ORM
- **Favorite**: `(client, reader)` unique_together; fast lookup for client's favorites

### Livestream & Gifting (70/30 split)
- **Livestream**: visibility (public/private/premium), agora_channel, started_at, ended_at
- **Gift**: name, price, animation_id
- **GiftPurchase**: `(livestream, sender, gift, amount, ledger_entry)`
  - Charge sender wallet with gift.price
  - Create LedgerEntry type='gift' on sender side (debit)
  - Create LedgerEntry type='commission' on reader side (credit = 70% of price) ← reader earnings source
- **Premium Gating**: If visibility='premium', verify client has active subscription before joining

### Agora Integration (readings/agora_views.py & live/agora_views.py)
- **RTC Tokens**: `agora_token_builder.build_token_with_uid(AGORA_APP_ID, AGORA_CERTIFICATE, channel_name, uid, expire_seconds=1200)`
  - Called when session transitions to 'active' or livestream starts
  - Include user_id in uid; channel_name from session or livestream
  - TTL: 1200s (20 min); refresh before expiry
- **RTM (Chat)**: Separate Agora Chat SDK for livestream chat, gifting events, notifications
  - Initialize with AGORA_CHAT_APP_ID + AGORA_CHAT_WEBSOCKET_ADDRESS
  - Send gift event via RTM when purchase completes

### Auth0 Flow (accounts/views.py + accounts/auth_backend.py)
1. **Login/Signup**: User clicks → `_auth0_redirect(request, screen='login'|'signup')` → generates state token, redirects to Auth0
2. **Callback**: Auth0 → `/accounts/callback/?code=...&state=...`
   - Verify state against session (CSRF protection)
   - Exchange code for ID token via Auth0 token endpoint
   - `verify_auth0_token(id_token)` checks RS256 signature against Auth0 JWKS endpoint
3. **User Creation**: `get_or_create_user_from_token(payload)` → creates Django User + UserProfile with role='client'
4. **Django Login**: `login(request, user, backend='django.contrib.auth.backends.ModelBackend')`

## URL Routing Architecture

All URLs follow this pattern:

| Prefix | Module | Key Routes |
|--------|--------|-----------|
| `/` | core | home, about, privacy, terms, help, dashboard (role-based) |
| `/accounts/` | accounts | login, signup, logout, callback, profile, profile/edit, settings, export, delete-account |
| `/readers/` | readers | list (filterable), me/availability, me/rates, `<slug>/`, `<slug>/favorite/`, `<slug>/book/` |
| `/sessions/` | readings | list, create, detail, join, leave, notes, api/* (for Agora tokens) |
| `/scheduling/` | scheduling | schedule, book/`<slot_id>/`, cancel, history |
| `/live/` | live | streams, detail, chat, gift |
| `/shop/` | shop | products, detail, cart, checkout |
| `/messages/` | messaging | inbox, compose, detail, send-reply |
| `/community/` | community | forums, threads, posts, flag, admin/moderation-queue |
| `/wallets/` | wallets | dashboard, top-up, history, stripe/webhook/ |
| `/admin/` | core + admin | dashboard, moderation, reader-onboarding, refunds, analytics |

## Model Reference

**accounts.models**:
- `UserProfile(user, auth0_sub, role, display_name, phone)` - roles: client/reader/admin

**readers.models**:
- `ReaderProfile(user, slug, bio, avatar_url, specialties, is_verified, stripe_connect_account_id)`
- `ReaderRate(reader, modality, rate_per_minute)` - modalities: text/voice/video
- `ReaderAvailability(reader, day_of_week 0-6, start_time, end_time)` - weekly repeating
- `Review(reader, client, session, rating 1-5, body)`
- `Favorite(client, reader)` unique_together

**readings.models**:
- `Session(client, reader, modality, state, channel_name, rate_per_minute, billing_minutes, started_at, ended_at, last_billing_at, grace_until, reconnect_count, summary)`
  - states: created, waiting, active, paused, reconnecting, ended, finalized
  - `transition(new_state)` validates state machine
- `SessionNote(client, session, reader, body)` - client notes about session/reader

**wallets.models**:
- `Wallet(user, balance, stripe_customer_id)` - balance always = sum(ledger entries)
- `LedgerEntry(wallet, amount signed, entry_type, idempotency_key unique, session, stripe_payment_intent_id, stripe_event_id, reference_type, reference_id)`
  - entry_types: top_up, session_charge, booking, paid_reply, gift, refund, adjustment, payout, commission
- `ProcessedStripeEvent(stripe_event_id unique)` - prevents webhook replay
- **Functions**: `debit_wallet(wallet, amount, type, idempotency_key, ...)`, `credit_wallet(...)`

**scheduling.models**:
- `ScheduledSlot(reader, start, end, duration_minutes, client, status)` - status: available/booked/completed/cancelled
- `Booking(slot OneToOne, client, amount, ledger_entry, cancelled_at)`

**live.models**:
- `Livestream(reader, title, visibility, agora_channel, started_at, ended_at)` - visibility: public/private/premium
- `Gift(name, price, animation_id)`
- `GiftPurchase(livestream, sender, gift, amount, ledger_entry)`

**messaging.models**:
- `DirectMessage(sender, recipient, body, created_at)`
- `PaidReply(message, replier, amount, ledger_entry)` - $1 default charge

**community.models**:
- `ForumCategory(name, slug, order)`
- `ForumThread(category, author, title)`
- `ForumPost(thread, author, body)`
- `PostAttachment(post, file)`
- `Flag(content_type, object_id, content_object GenericFK, reporter, reason, status)` - status: pending/resolved/dismissed

**shop.models**:
- `Product(stripe_product_id, name, type, price, file R2-key)` - type: digital/physical
- `Order(user, stripe_checkout_session_id, status)`
- `OrderItem(order, product, quantity, delivery_url signed)`

**core.models**:
- `AuditLog(user, action, model_name, object_id, details JSON)`

## Project-Specific Conventions & Patterns

### Models & Database
- **Always use `settings.AUTH_USER_MODEL`** for FK to User (not hardcoded)
- **Timestamps**: `created_at` (auto_now_add), `updated_at` (auto_now), `last_billing_at` (manual)
- **Status fields**: Use CharField with choices (e.g., SESSION_STATES) + db_index=True for filters
- **Decimal fields**: Use Decimal(max_digits=8, decimal_places=2) for money (not float)
- **GenericForeignKey**: Used for Flag model to point to any content (forum post, comment, etc.)
- **select_related/prefetch_related**: Always use in views for N+1 prevention (e.g., `Session.objects.select_related('reader').prefetch_related('notes')`)

### Idempotency Pattern (critical for async operations)
```python
# Prevent duplicate charges on webhook replay or retry
idempotency_key = f"session_{session.pk}_min_{session.billing_minutes + 1}"
if LedgerEntry.objects.filter(idempotency_key=idempotency_key).exists():
    return  # Already processed, skip

# For admin actions: use uuid to ensure uniqueness
import uuid
idem_key = f"admin_refund_{uuid.uuid4()}"
```
Apply to wallet debits, refunds, gifts, and all Stripe/Agora interactions.

### Environment Variables (settings.py)
- **Database**: DATABASE_URL or PGHOST/PGUSER/PGPASSWORD (sslmode=require for Neon)
- **Auth0**: AUTH0_DOMAIN, AUTH0_AUDIENCE, AUTH0_APP_ID, AUTH0_CLIENT_SECRET
- **Agora**: AGORA_APP_ID, AGORA_CERTIFICATE, AGORA_CHAT_APP_ID, AGORA_CHAT_WEBSOCKET_ADDRESS
- **Stripe**: STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, STRIPE_WEBHOOK_SECRET
- **Celery**: REDIS_URL (default: redis://localhost:6379/0)
- **AWS/R2**: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

### Celery Async Tasks (readings/tasks.py)
```python
from celery import shared_task

@shared_task
def billing_tick():
    # Runs every 60s from CELERY_BEAT_SCHEDULE
    # Charges active sessions, uses idempotency_key to prevent double-charge
    for session in Session.objects.filter(state='active'):
        idempotency_key = f"session_{session.pk}_min_{session.billing_minutes + 1}"
        if LedgerEntry.objects.filter(idempotency_key=idempotency_key).exists():
            continue  # Already charged, skip
```
- **idempotency_key pattern** must be used to avoid duplicate processing
- **Scheduled**: `billing_tick` runs every 60s (see CELERY_BEAT_SCHEDULE in settings.py)
- Use `@shared_task` decorator, not @task

### View Patterns & Decorators
```python
from django.contrib.auth.decorators import login_required
from accounts.decorators import require_role

# Single role check
@login_required
@require_role('reader')
def reader_view(request):
    rp = getattr(request.user, 'reader_profile', None)
    if not rp:
        return redirect('profile')  # Reader not onboarded yet
    return render(request, 'template.html', {})

# Multiple roles allowed
@require_role('reader', 'admin')
def sensitive_view(request):
    pass
```
- **@login_required** → redirect to login if not authenticated
- **@require_role(...)** → includes @login_required, checks profile.role, redirects to dashboard if no match
- **@staff_member_required** → for admin views; uses Django's staff flag, not role
- **@require_POST** → ensures method is POST, prevents CSRF
- **@csrf_exempt** → only for webhook endpoints; always verify signature server-side

### Wallet & Payment Pattern
```python
from wallets.models import Wallet, debit_wallet, credit_wallet
from decimal import Decimal

# Always use debit_wallet/credit_wallet, never manipulate balance directly
wallet = Wallet.objects.get_or_create(user=user, defaults={})[0]
try:
    debit_wallet(
        wallet,
        Decimal('10.00'),
        'session_charge',  # entry_type from ENTRY_TYPES
        f"session_{session.pk}_min_{session.billing_minutes + 1}",  # idempotency_key
        session=session,
        reference_type='session',
        reference_id=str(session.pk),
    )
except ValueError:
    # Insufficient balance
    session.transition('paused')
```
- Always use Decimal for money, never float
- **debit_wallet** uses transaction.atomic() with select_for_update() for consistency
- **credit_wallet** is idempotent; re-running same idempotency_key returns False
- Check balance BEFORE debit to handle insufficient funds gracefully

### Stripe Webhook Pattern
```python
# In webhooks.py, always:
# 1. Verify signature
# 2. Check if event already processed
# 3. Create idempotent ledger entry

from wallets.models import ProcessedStripeEvent, credit_wallet

event_id = data['id']
if ProcessedStripeEvent.objects.filter(stripe_event_id=event_id).exists():
    return HttpResponse(status=200)  # Already processed

# ... process event ...

ProcessedStripeEvent.objects.create(stripe_event_id=event_id)
```

### Reading Sessions Pattern
```python
# Session state machine always uses transition()
session = Session.objects.get(pk=1)
if session.transition('active'):
    # Valid transition succeeded
    session.channel_name = generate_agora_channel()
    session.save()
else:
    # Invalid state transition, log error
    pass
```
- State transitions validated in `Session.transition()` method
- Never set state directly; always use `transition()` to enforce rules
- On 'active', generate Agora channel name and store it
- On 'ended', record session summary and final ledger reconciliation
- On 'paused', set `grace_until = now + 5_minutes` to prevent reconnect loops

## Common Pitfalls & Fixes

1. **Forgot idempotency key?** → Duplicate charges on retry. Every payment/debit must have unique idempotency_key.
2. **Hardcoded User model?** → Fails with custom user models. Always use `settings.AUTH_USER_MODEL`.
3. **Float for money?** → Precision loss. Use Decimal(max_digits=8, decimal_places=2).
4. **No Agora token TTL check?** → Expired tokens fail mid-session. Tokens expire after ~20 min; refresh before expiry.
5. **Stripe event re-processing?** → Double crediting. Always check ProcessedStripeEvent before processing.
6. **N+1 queries?** → Use select_related('fk') and prefetch_related('reverse_fk') in all list views.
7. **Balance gone negative?** → select_for_update() in debit_wallet ensures consistency; catch ValueError.
8. **Webhook timing issues?** → Session may transition during webhook; check state before acting.

## Development Commands

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
python manage.py migrate

# Run local server
python manage.py runserver

# Celery (in separate terminals)
celery -A soulseer worker -l info
celery -A soulseer beat -l info

# Admin
python manage.py createsuperuser
# Access: http://localhost:8000/admin/

# Stripe Webhook (local testing)
stripe listen --forward-to localhost:8000/stripe/webhook/

# Generate migrations
python manage.py makemigrations --name descriptive_name

# Interactive shell
python manage.py shell
# >>> from readers.models import ReaderProfile
# >>> ReaderProfile.objects.all()
```

## Key Files by Feature

| Feature | Key Files |
|---------|-----------|
| Auth0 integration | [accounts/auth_backend.py](accounts/auth_backend.py), [accounts/views.py](accounts/views.py) |
| User roles & dashboard routing | [accounts/models.py](accounts/models.py), [core/views.py](core/views.py), [accounts/decorators.py](accounts/decorators.py) |
| Session billing | [readings/models.py](readings/models.py), [readings/tasks.py](readings/tasks.py) |
| Wallet & idempotency | [wallets/models.py](wallets/models.py), [wallets/stripe_services.py](wallets/stripe_services.py) |
| Agora RTC/RTM | [readings/agora_views.py](readings/agora_views.py), [live/views.py](live/views.py) |
| Stripe webhooks | [wallets/webhooks.py](wallets/webhooks.py), [wallets/webhook_urls.py](wallets/webhook_urls.py) |
| Admin dashboard | [core/admin_views.py](core/admin_views.py), [core/dashboard_views.py](core/dashboard_views.py) |
| Reader profiles & availability | [readers/models.py](readers/models.py), [readers/views.py](readers/views.py) |
| Scheduled readings | [scheduling/models.py](scheduling/models.py), [scheduling/views.py](scheduling/views.py) |
| Moderation queue | [community/models.py](community/models.py), [core/admin_views.py](core/admin_views.py) |

## When Adding Features

- **New payment flow?** → Always use `debit_wallet()` or `credit_wallet()` with unique idempotency_key
- **New real-time feature?** → Use Agora RTM (not websockets; already integrated)
- **New user workflow?** → Integrate with Auth0 OAuth2 (users come from Auth0 only)
- **New status tracking?** → Use CharField with choices tuple + db_index=True; consider state machine pattern
- **Database change?** → Create migration: `python manage.py makemigrations --name feature_description`
- **New async task?** → Add to [readings/tasks.py](readings/tasks.py), register in CELERY_BEAT_SCHEDULE if scheduled
- **New list view?** → Always use select_related/prefetch_related to prevent N+1; add filters to GET params
- **New ledger operation?** → Document entry_type in wallets.models.ENTRY_TYPES; update ENTRY_TYPES list if needed
