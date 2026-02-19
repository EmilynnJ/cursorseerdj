# SoulSeer Data Model Reference & Architecture

**Last Updated**: February 2026 | **Database**: PostgreSQL (Neon)

## Entity Relationship Diagram (Conceptual)

```
User (Django auth_user)
├── UserProfile (1:1)
│   ├── role: client/reader/admin
│   └── display_name, phone
├── Wallet (1:1)
│   └── LedgerEntry (1:many)
│       ├── amount: signed Decimal
│       ├── entry_type: top_up, session_charge, booking, paid_reply, gift, refund, adjustment, payout, commission
│       ├── idempotency_key: unique
│       └── stripe_event_id: indexed
├── ReaderProfile (0:1) if role='reader'
│   ├── ReaderRate (1:many)
│   │   ├── modality: text, voice, video
│   │   └── rate_per_minute
│   ├── ReaderAvailability (1:many)
│   │   ├── day_of_week: 0-6
│   │   ├── start_time, end_time
│   │   └── repeating weekly
│   ├── Review (1:many)
│   │   ├── client: FK(User)
│   │   ├── session: FK(Session) optional
│   │   ├── rating: 1-5
│   │   └── body, created_at
│   ├── Livestream (1:many)
│   │   ├── visibility: public/private/premium
│   │   ├── agora_channel: indexed
│   │   ├── started_at, ended_at
│   │   └── GiftPurchase (1:many)
│   │       ├── sender: FK(User)
│   │       ├── gift: FK(Gift)
│   │       ├── amount
│   │       └── ledger_entry: FK(LedgerEntry)
│   └── ScheduledSlot (1:many)
│       ├── start, end: DateTimeField
│       ├── duration_minutes
│       ├── client: FK(User) optional
│       ├── status: available, booked, completed, cancelled
│       └── Booking (1:1)
│           ├── amount
│           ├── ledger_entry: FK(LedgerEntry)
│           └── cancelled_at optional
├── Session (1:many) as client
│   ├── reader: FK(User)
│   ├── modality: text, voice, video
│   ├── state: created, waiting, active, paused, reconnecting, ended, finalized
│   ├── rate_per_minute: Decimal
│   ├── billing_minutes: PositiveInt
│   ├── channel_name: indexed
│   ├── grace_until: optional (reconnect grace)
│   ├── reconnect_count
│   ├── summary: TextField
│   ├── SessionNote (1:many)
│   │   ├── client: FK(User)
│   │   ├── session: FK(Session) optional
│   │   ├── reader: FK(User) optional
│   │   └── body, created_at
│   └── Review (0:1)
│       └── (reverse from Review.session)
├── DirectMessage (1:many)
│   ├── sender: FK(User)
│   ├── recipient: FK(User)
│   ├── body, created_at
│   └── PaidReply (0:1)
│       ├── replier: FK(User)
│       ├── amount: Decimal
│       └── ledger_entry: FK(LedgerEntry)
├── Order (1:many)
│   ├── stripe_checkout_session_id: indexed
│   ├── status: pending, paid, shipped, delivered
│   ├── created_at
│   └── OrderItem (1:many)
│       ├── product: FK(Product)
│       ├── quantity
│       └── delivery_url: signed URL (R2)
├── ForumThread (1:many)
│   ├── category: FK(ForumCategory)
│   ├── title, created_at, updated_at
│   └── ForumPost (1:many)
│       ├── author: FK(User)
│       ├── body, created_at
│       └── PostAttachment (1:many)
│           └── file: R2 key
└── Flag (1:many)
    ├── content_type: GenericFK (ForumPost, etc.)
    ├── reporter: FK(User)
    ├── reason, status: pending/resolved/dismissed
    └── created_at

Gift
└── (many: GiftPurchase)

Product
├── stripe_product_id: indexed
├── name, type: digital/physical
├── price: Decimal
├── file: R2 key (digital)
└── (many: OrderItem)

ForumCategory
├── name, slug: unique
├── order
└── (many: ForumThread)

AuditLog
├── user: FK(User)
├── action: CharField
├── model_name, object_id: indexed
├── details: JSONField
└── created_at: indexed
```

---

## Key Models & Fields

### accounts.UserProfile
```python
class UserProfile(models.Model):
    user = OneToOneField(User)
    auth0_sub = CharField(max_length=255, unique=True, db_index=True)
    role = CharField(choices=[client/reader/admin], default='client')
    display_name = CharField(max_length=100, blank=True)
    phone = CharField(max_length=30, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Key Constraints**:
- ONE UserProfile per User
- auth0_sub is unique (Auth0 subject ID)
- role field determines dashboard routing

---

### wallets.Wallet & LedgerEntry
```python
class Wallet(models.Model):
    user = OneToOneField(User)
    balance = DecimalField(max_digits=12, decimal_places=2, default='0')
    stripe_customer_id = CharField(max_length=255, blank=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class LedgerEntry(models.Model):
    wallet = ForeignKey(Wallet)
    amount = DecimalField(max_digits=12, decimal_places=2)  # Signed: negative=debit, positive=credit
    entry_type = CharField(choices=[
        'top_up', 'session_charge', 'booking', 'paid_reply',
        'gift', 'refund', 'adjustment', 'payout', 'commission'
    ])
    idempotency_key = CharField(max_length=255, unique=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
    session = ForeignKey(Session, null=True, blank=True)
    stripe_payment_intent_id = CharField(max_length=255, blank=True, db_index=True)
    stripe_event_id = CharField(max_length=255, blank=True, db_index=True)
    reference_type = CharField(max_length=50, blank=True)
    reference_id = CharField(max_length=255, blank=True)
```

**Key Invariant**:
- wallet.balance = sum(ledger.amount where ledger.wallet_id = wallet.pk)

**idempotency_key Pattern**:
- Session charge: `f"session_{session_id}_min_{billing_minutes + 1}"`
- Admin refund: `f"admin_refund_{uuid.uuid4()}"`
- Webhook: `f"stripe_{stripe_event_id}"`

---

### readings.Session
```python
class Session(models.Model):
    client = ForeignKey(User)
    reader = ForeignKey(User)
    modality = CharField(choices=['text', 'voice', 'video'])
    state = CharField(choices=[
        'created', 'waiting', 'active', 'paused', 'reconnecting', 'ended', 'finalized'
    ], db_index=True)
    channel_name = CharField(max_length=255, blank=True, db_index=True)
    rate_per_minute = DecimalField(max_digits=8, decimal_places=2)
    billing_minutes = PositiveIntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    started_at = DateTimeField(null=True, blank=True)
    ended_at = DateTimeField(null=True, blank=True)
    last_billing_at = DateTimeField(null=True, blank=True)
    grace_until = DateTimeField(null=True, blank=True)  # Reconnect grace period
    reconnect_count = PositiveIntegerField(default=0)
    summary = TextField(blank=True)
```

**State Machine**:
```
created → waiting → active ⇄ paused → reconnecting → ended → finalized
                      ↓ (auto-charge every 60s)
```

**Grace Period Logic**:
- On disconnect during 'active': set grace_until = now + 5 min, transition to 'paused'
- On reconnect within grace_until: transition back to 'active'
- After grace_until expires: transition to 'ended'

---

### readers.ReaderProfile, ReaderRate, Review
```python
class ReaderProfile(models.Model):
    user = OneToOneField(User)
    slug = SlugField(unique=True, db_index=True)
    bio = TextField(blank=True)
    avatar_url = URLField(blank=True)
    specialties = CharField(max_length=500, blank=True)  # Comma-separated tags
    is_verified = BooleanField(default=False)
    stripe_connect_account_id = CharField(max_length=255, blank=True, db_index=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class ReaderRate(models.Model):
    reader = ForeignKey(ReaderProfile)
    modality = CharField(choices=['text', 'voice', 'video'])
    rate_per_minute = DecimalField(max_digits=8, decimal_places=2)
    
    class Meta:
        unique_together = [('reader', 'modality')]

class Review(models.Model):
    reader = ForeignKey(ReaderProfile)
    client = ForeignKey(User)
    session = ForeignKey(Session, null=True, blank=True)  # Optional, may not be session-based
    rating = PositiveSmallIntegerField()  # 1-5
    body = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
```

**Key Constraints**:
- ReaderProfile.slug is unique (URL-friendly identifier)
- ReaderRate unique constraint on (reader, modality) → one rate per modality per reader
- Review.rating must be 1-5 (validate in model clean() method)

---

### scheduling.ScheduledSlot & Booking
```python
class ScheduledSlot(models.Model):
    reader = ForeignKey(User)
    start = DateTimeField()
    end = DateTimeField()
    duration_minutes = PositiveSmallIntegerField(default=30)
    client = ForeignKey(User, null=True, blank=True)
    status = CharField(
        choices=['available', 'booked', 'completed', 'cancelled'],
        default='available',
        db_index=True
    )

class Booking(models.Model):
    slot = OneToOneField(ScheduledSlot)
    client = ForeignKey(User)
    amount = DecimalField(max_digits=10, decimal_places=2)
    ledger_entry = ForeignKey(LedgerEntry, null=True, blank=True)
    cancelled_at = DateTimeField(null=True, blank=True)
```

**Booking Flow**:
1. Client selects slot (status='available')
2. Wallet debited: create LedgerEntry
3. Slot status → 'booked', client set
4. Booking record created, ledger_entry linked
5. On cancellation: cancelled_at set, status → 'cancelled', refund issued

---

### live.Livestream, Gift, GiftPurchase
```python
class Livestream(models.Model):
    reader = ForeignKey(User)
    title = CharField(max_length=255)
    visibility = CharField(choices=['public', 'private', 'premium'], default='public')
    agora_channel = CharField(max_length=255, blank=True, db_index=True)
    started_at = DateTimeField(null=True, blank=True)
    ended_at = DateTimeField(null=True, blank=True)

class Gift(models.Model):
    name = CharField(max_length=100)
    price = DecimalField(max_digits=8, decimal_places=2)
    animation_id = CharField(max_length=100, blank=True)  # Agora RTM animation ID

class GiftPurchase(models.Model):
    livestream = ForeignKey(Livestream)
    sender = ForeignKey(User)  # Buyer
    gift = ForeignKey(Gift)
    amount = DecimalField(max_digits=10, decimal_places=2)
    ledger_entry = ForeignKey(LedgerEntry, null=True, blank=True)
```

**70/30 Split Logic**:
- GiftPurchase created
- Debit sender wallet: entry_type='gift'
- Credit reader wallet: entry_type='commission', amount = gift.price * 0.70
- (Refactored: track commission separately from gift price)

---

### messaging.DirectMessage, PaidReply
```python
class DirectMessage(models.Model):
    sender = ForeignKey(User)
    recipient = ForeignKey(User)
    body = TextField()
    created_at = DateTimeField(auto_now_add=True)

class PaidReply(models.Model):
    message = ForeignKey(DirectMessage)
    replier = ForeignKey(User)  # Who is charging for reply
    amount = DecimalField(max_digits=8, decimal_places=2, default='1.00')
    ledger_entry = ForeignKey(LedgerEntry, null=True, blank=True)
```

**Paid Reply Flow**:
1. Reader receives message
2. Reader chooses "reply with charge" ($1)
3. Debit sender wallet: entry_type='paid_reply'
4. PaidReply created, ledger_entry linked
5. Message delivered to sender

---

### community.ForumCategory, ForumThread, ForumPost, Flag
```python
class ForumCategory(models.Model):
    name = CharField(max_length=100)
    slug = SlugField(unique=True)
    order = PositiveSmallIntegerField(default=0)

class ForumThread(models.Model):
    category = ForeignKey(ForumCategory)
    author = ForeignKey(User)
    title = CharField(max_length=255)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class ForumPost(models.Model):
    thread = ForeignKey(ForumThread)
    author = ForeignKey(User)
    body = TextField()
    created_at = DateTimeField(auto_now_add=True)

class PostAttachment(models.Model):
    post = ForeignKey(ForumPost)
    file = CharField(max_length=500)  # R2 key

class Flag(models.Model):
    content_type = ForeignKey(ContentType)  # GenericFK
    object_id = PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    reporter = ForeignKey(User)
    reason = TextField()
    status = CharField(
        choices=['pending', 'resolved', 'dismissed'],
        default='pending'
    )
```

**Flag Usage**:
- Can flag ForumPost, ForumThread, DirectMessage, User profile
- Admin moderation queue shows pending flags
- Status updated: pending → resolved (content hidden) or dismissed (false report)

---

### shop.Product, Order, OrderItem
```python
class Product(models.Model):
    stripe_product_id = CharField(max_length=255, blank=True, db_index=True)
    name = CharField(max_length=255)
    type = CharField(choices=['digital', 'physical'], default='physical')
    price = DecimalField(max_digits=10, decimal_places=2)
    file = CharField(max_length=500, blank=True)  # R2 key (digital only)

class Order(models.Model):
    user = ForeignKey(User)
    stripe_checkout_session_id = CharField(max_length=255, blank=True, db_index=True)
    status = CharField(max_length=50, default='pending')  # pending, paid, shipped, delivered
    created_at = DateTimeField(auto_now_add=True)

class OrderItem(models.Model):
    order = ForeignKey(Order)
    product = ForeignKey(Product)
    quantity = PositiveIntegerField(default=1)
    delivery_url = URLField(blank=True)  # Signed R2 URL (digital) with TTL
```

**Digital Delivery**:
1. Client purchases digital product
2. OrderItem created
3. Signed R2 URL generated with 24h TTL: `f"https://bucket.s3.cf.net/{file}?expires_in=86400&signature=..."`
4. delivery_url stored
5. Client can download within 24h

---

### core.AuditLog
```python
class AuditLog(models.Model):
    user = ForeignKey(User, null=True)  # Who performed action
    action = CharField(max_length=100)  # e.g., 'refund_issued', 'reader_verified'
    model_name = CharField(max_length=100, blank=True)  # e.g., 'Wallet', 'ReaderProfile'
    object_id = CharField(max_length=100, blank=True)  # e.g., '12345'
    details = JSONField(default=dict, blank=True)  # Additional context: {amount, reason, etc}
    created_at = DateTimeField(auto_now_add=True, db_index=True)
```

**Usage Examples**:
- Refund issued: action='refund_issued', model_name='Wallet', details={'amount': '50.00', 'reason': 'user_complaint'}
- Reader verified: action='reader_verified', model_name='ReaderProfile', details={'reader_id': '123'}
- Admin adjustment: action='wallet_adjustment', model_name='Wallet', details={'amount': '-10.00', 'reason': 'error_correction'}

---

## Database Indexes

**Critical Indexes** (for performance):
```sql
-- Session lookups
CREATE INDEX idx_session_state ON readings_session(state);
CREATE INDEX idx_session_channel ON readings_session(channel_name);

-- Wallet & ledger
CREATE INDEX idx_ledger_idempotency ON wallets_ledgerentry(idempotency_key);
CREATE INDEX idx_ledger_stripe_event ON wallets_ledgerentry(stripe_event_id);
CREATE INDEX idx_ledger_wallet ON wallets_ledgerentry(wallet_id);

-- Reader profile
CREATE INDEX idx_reader_slug ON readers_readerprofile(slug);
CREATE INDEX idx_reader_verified ON readers_readerprofile(is_verified);

-- Scheduling
CREATE INDEX idx_slot_status ON scheduling_scheduledslot(status);
CREATE INDEX idx_slot_start ON scheduling_scheduledslot(start);

-- Community
CREATE INDEX idx_flag_status ON community_flag(status);

-- Audit
CREATE INDEX idx_audit_created ON core_auditlog(created_at);
```

---

## Query Optimization Guidelines

### N+1 Prevention
```python
# BAD: N+1 queries
sessions = Session.objects.filter(state='active')
for s in sessions:
    print(s.reader.user.email)  # N additional queries!

# GOOD: select_related
sessions = Session.objects.filter(state='active').select_related('reader__user')
for s in sessions:
    print(s.reader.user.email)  # No additional queries
```

### Bulk Operations
```python
# BAD: Multiple saves
for session in sessions:
    session.state = 'ended'
    session.save()  # N database calls

# GOOD: bulk_update
for session in sessions:
    session.state = 'ended'
Session.objects.bulk_update(sessions, ['state'], batch_size=1000)
```

### Aggregation
```python
# BAD: Python loop
total = 0
for entry in LedgerEntry.objects.filter(wallet=wallet):
    total += entry.amount

# GOOD: Database aggregation
from django.db.models import Sum
total = LedgerEntry.objects.filter(wallet=wallet).aggregate(Sum('amount'))['amount__sum']
```

---

## Data Integrity Constraints

1. **Wallet Balance**: Always = sum(ledger.amount)
2. **Idempotency**: idempotency_key is globally unique
3. **Session State**: Only valid transitions allowed (via transition() method)
4. **Reader Rate**: One rate per (reader, modality) pair
5. **Booking**: One booking per ScheduledSlot
6. **User Profile**: One profile per user, role must be client/reader/admin
7. **Decimal Precision**: All money fields are Decimal(max_digits=10, decimal_places=2)

