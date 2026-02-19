# SoulSeer Feature Acceptance Criteria

**Last Updated**: February 2026 | **Build Status**: Feature-Complete Production Build

## 1. On-Demand Readings (Pay Per Minute)

### Feature Description
Clients pay per minute for live readings from readers via text, voice, or video.

### Acceptance Criteria
- [ ] Client can select reader and modality (text/voice/video)
- [ ] Client wallet must have balance ≥ rate_per_minute before session starts
- [ ] Session state machine: created → waiting → active → paused → reconnecting → ended → finalized
- [ ] Billing: Auto-deduct every 60s via `billing_tick()` Celery task (idempotent)
- [ ] Low balance handling: Auto-transition to 'paused' if balance < rate during billing
- [ ] Grace window: 5-minute reconnection grace period prevents rapid disconnect/reconnect loops
- [ ] Session summary recorded on finalization
- [ ] Session ledger entries include: amount, timestamp, idempotency_key, session FK
- [ ] Client can view session history and notes

### Implementation Status
- ✅ Session model with state machine
- ✅ ReaderRate model (per modality)
- ✅ Wallet ledger with idempotent debit_wallet()
- ✅ Celery billing_tick() task
- ✅ Grace period (grace_until field)
- ✅ SessionNote model

### Gap Items
- [ ] Full reconnection fraud handling (rapid disconnect loops)
- [ ] Session summary UI display
- [ ] Agora RTC token generation on active transition

---

## 2. Scheduled Readings (Flat Rate)

### Feature Description
Readers set weekly availability; clients book 15/30/45/60-minute slots at flat rate.

### Acceptance Criteria
- [ ] Reader can set weekly availability (repeating per day of week)
- [ ] Slots auto-generate or manual creation from availability
- [ ] Client can browse available slots (filtered by time, duration, specialty)
- [ ] Client books slot: charges wallet with flat rate (calculated from duration × rate/min)
- [ ] Booking creates ScheduledSlot with status='booked' and Booking record
- [ ] Cancellation: Client can cancel up to 24h before; refund issued
- [ ] Cancellation rule: After 24h, refund reduced or denied
- [ ] Reader receives payment split (after platform fees)
- [ ] Client can view booking history

### Implementation Status
- ✅ ReaderAvailability model (weekly slots)
- ✅ ScheduledSlot model with status tracking
- ✅ Booking model with ledger_entry FK
- ✅ Reader availability UI view
- ✅ Slot booking flow (debit_wallet)

### Gap Items
- [ ] Slot auto-generation from ReaderAvailability
- [ ] Cancellation rule enforcement (24h window)
- [ ] Refund auto-trigger on cancellation
- [ ] Duration-based rate calculation UI

---

## 3. Live Streaming + Gifting

### Feature Description
Readers host public/private/premium live streams; clients send gifts (70/30 split).

### Acceptance Criteria
- [ ] Reader can start livestream (public/private/premium visibility)
- [ ] Livestream uses Agora RTC (channel managed server-side)
- [ ] Premium streams: Access gated; verify client subscription or ticket purchase
- [ ] Viewers can send gifts from gift catalog
- [ ] Gift purchase: Debit sender wallet, create LedgerEntry type='gift' (debit)
- [ ] 70/30 split: Create LedgerEntry type='commission' for reader (credit = 70% of gift price)
- [ ] Gift animations display on stream
- [ ] Reader earnings visible in dashboard (session + commission)
- [ ] Chat via Agora RTM (presence + messaging)

### Implementation Status
- ✅ Livestream model with visibility
- ✅ Gift model with price/animation_id
- ✅ GiftPurchase model with ledger_entry
- ✅ Agora RTM integration

### Gap Items
- [ ] Premium gating logic (subscription/ticket verification)
- [ ] 70/30 split commission creation (currently gift only)
- [ ] Gift animation UI display
- [ ] Livestream Agora RTC token generation
- [ ] Viewer list and presence tracking

---

## 4. Messaging (Free + Paid Reply)

### Feature Description
Clients message readers for free; readers choose to reply for free or $1 charge.

### Acceptance Criteria
- [ ] Client can message reader (unlimited free messages)
- [ ] Reader notified of new messages
- [ ] Reader can reply free or set paid reply ($1)
- [ ] Paid reply: Charge client wallet $1, create LedgerEntry type='paid_reply'
- [ ] Paid reply cannot deliver without successful debit
- [ ] Message history viewable by both parties
- [ ] Audit trail: Link each paid reply to LedgerEntry

### Implementation Status
- ✅ DirectMessage model
- ✅ PaidReply model with ledger_entry
- ✅ Wallet debit on paid reply

### Gap Items
- [ ] Notification system (email/push)
- [ ] Paid reply UI toggle
- [ ] Message search/filtering
- [ ] Rate limiting for message spam

---

## 5. Community (Forums + Moderation)

### Feature Description
Public forums with discussions; admin moderation queue for flags.

### Acceptance Criteria
- [ ] Users can create forum categories (admin-only)
- [ ] Users can create threads in categories
- [ ] Users can post replies to threads
- [ ] Posts support text + file attachments (R2/S3)
- [ ] Any user can flag content (reason required)
- [ ] Flag status: pending → resolved/dismissed
- [ ] Admin moderation queue shows pending flags
- [ ] Admin can resolve (take action) or dismiss (false flag)
- [ ] Flagged content hidden/warned until resolved

### Implementation Status
- ✅ ForumCategory, ForumThread, ForumPost models
- ✅ PostAttachment model (R2 key)
- ✅ Flag model with status tracking
- ✅ Admin moderation_queue view

### Gap Items
- [ ] User-facing flagging UI
- [ ] Content hiding logic (pending flags)
- [ ] Flag resolution actions (post deletion, user warning)
- [ ] File attachment upload to R2

---

## 6. Shop (Stripe-Synced Products)

### Feature Description
Digital and physical products synced with Stripe; digital delivery via signed URLs.

### Acceptance Criteria
- [ ] Products synced from Stripe catalog (automated or manual)
- [ ] Product types: digital (file) / physical (shipping)
- [ ] Inventory tracked and updated from Stripe
- [ ] Coupons/discounts applied at checkout
- [ ] Order creation: charge wallet or Stripe
- [ ] Digital delivery: Generate signed R2 URLs (time-limited, user-specific)
- [ ] Delivery links expire after configured time (e.g., 24h)
- [ ] Order status tracking: pending → paid → shipped/delivered
- [ ] Client can re-download digital items (expiring links)

### Implementation Status
- ✅ Product model with stripe_product_id
- ✅ Order and OrderItem models
- ✅ delivery_url field for signed URLs

### Gap Items
- [ ] Stripe product sync (cron or webhook)
- [ ] Coupon/Discount model and logic
- [ ] R2 signed URL generation with TTL
- [ ] Order status workflow (pending → paid → delivered)
- [ ] Physical product shipping integration

---

## 7. Role-Based Dashboards

### Client Dashboard
- [ ] Wallet balance and top-up button
- [ ] Transaction history (last 10 entries)
- [ ] Upcoming scheduled sessions
- [ ] Past session notes and summaries
- [ ] Favorite readers list
- [ ] Quick stats (total spent, active sessions)

### Reader Dashboard
- [ ] Earnings breakdown (session charges + commissions)
- [ ] Session history with client names
- [ ] Upcoming scheduled bookings
- [ ] Rate settings (text/voice/video rates)
- [ ] Availability calendar (weekly)
- [ ] Recent reviews and average rating
- [ ] Analytics (basic: session count, earnings trend)

### Admin Dashboard
- [ ] Pending reader onboarding (is_verified=False)
- [ ] KYC flags (reader background check status)
- [ ] Moderation queue (pending flags)
- [ ] Recent refunds and adjustments
- [ ] Stripe Connect payout control
- [ ] Platform stats: users, readers, sessions, revenue
- [ ] Analytics: session count, top readers, revenue trend

### Implementation Status
- ✅ core/dashboard_views.py with all three dashboards
- ✅ Role-based routing (redirect to appropriate dashboard)

---

## 8. Security & Compliance

### GDPR/CCPA Data Export
- [ ] Client can request data export (JSON)
- [ ] Export includes: user profile, sessions, bookings, messages, transactions
- [ ] Export delivered as download within 24h
- [ ] Route: `/accounts/export/`

### Account Deletion
- [ ] Client can request account deletion
- [ ] Deletion flow: request → confirmation email → verify → delete
- [ ] After deletion: anonymize user data (null email, delete PII)
- [ ] Keep ledger entries for accounting (FK → null)
- [ ] Route: `/accounts/delete-account/`

### Rate Limiting
- [ ] Auth endpoints (login/signup): 5 requests per 5 min per IP
- [ ] Messaging (send message): 10 messages per 60s per user
- [ ] Message flag reports: 5 reports per 60s per user

### Audit Logging
- [ ] AuditLog created for: payouts, refunds, adjustments, admin actions
- [ ] Fields: user, action, model_name, object_id, details (JSON), created_at

### Implementation Status
- ✅ data_export view
- ✅ delete_account view
- ✅ AuditLog model

### Gap Items
- [ ] Rate limiting middleware
- [ ] Audit logging integration (wire into views/tasks)
- [ ] Email verification for data deletion
- [ ] Anonymization logic

---

## 9. Wallet & Payments

### Wallet Top-Up
- [ ] Client enters amount and card via Stripe Checkout
- [ ] Stripe charges card, webhook calls `/stripe/webhook/`
- [ ] Webhook: credit_wallet() creates LedgerEntry type='top_up' (idempotent)
- [ ] Wallet balance updates in real-time

### Wallet Refunds
- [ ] Admin initiates refund via `/admin/refunds/`
- [ ] Refund: debit_wallet() creates LedgerEntry type='refund'
- [ ] Refund is auditable and logged

### Stripe Reconciliation
- [ ] ProcessedStripeEvent prevents webhook replay (stored event_ids)
- [ ] LedgerEntry.stripe_event_id matches Stripe webhook event_id
- [ ] Monthly reconciliation: sum(ledger.amount where entry_type='top_up') = Stripe charges

### Implementation Status
- ✅ Wallet model with balance
- ✅ LedgerEntry with idempotency_key, stripe_event_id
- ✅ ProcessedStripeEvent model
- ✅ debit_wallet/credit_wallet functions
- ✅ Stripe services integration

---

## 10. Agora Integration

### RTC (Voice/Video)
- [ ] Session.transition('active') generates Agora RTC token
- [ ] Token includes channel_name, user_id, 20-min TTL
- [ ] Client and reader join Agora channel
- [ ] Disconnect handled: transition to 'paused' with grace_until
- [ ] Reconnect within grace period: resume session
- [ ] After grace period: transition to 'ended'

### RTM (Chat + Gifting)
- [ ] Livestream chat uses Agora RTM (separate from RTC)
- [ ] Gift purchase triggers RTM event to stream viewers
- [ ] Presence tracking (who is watching)

### Implementation Status
- ✅ Agora token generation (agora_views.py)
- ✅ Session RTC channel management

### Gap Items
- [ ] Token refresh logic (tokens expire after 20 min)
- [ ] RTM event publishing for gifts
- [ ] Presence list UI

---

## 11. External Integrations

### Auth0
- [ ] User signup/login via Auth0 OAuth2
- [ ] UserProfile created on first login with role='client'
- [ ] Role change handled manually (admin promotes readers)

### Stripe (Payments)
- [ ] Wallet top-ups via Checkout
- [ ] Webhook idempotency (ProcessedStripeEvent)
- [ ] Refunds via admin panel

### Stripe Connect (Future)
- [ ] Reader payout via Stripe Connect (TODO)

### R2/S3 (Storage)
- [ ] Digital product files stored in R2
- [ ] Signed URLs for time-limited download (TODO)

### Sentry (Error Tracking)
- [ ] Configured in settings.py
- [ ] Exceptions logged to Sentry dashboard

---

## Build Order (Priority)

1. ✅ Auth + roles + dashboards
2. ✅ Wallet ledger + Stripe
3. ✅ Reader profiles + rates
4. ✅ On-demand session + billing
5. ⏳ Agora RTC tokens + reconnection
6. ⏳ Messaging (free + paid)
7. ⏳ Scheduling (booking + availability)
8. ⏳ Livestream + gifting (70/30)
9. ⏳ Shop + digital delivery
10. ⏳ Community forums + moderation
11. ⏳ Admin analytics + payout control

---

## Notes

- All money amounts use Decimal(max_digits=10, decimal_places=2)
- All async tasks use idempotency_key to prevent duplicates
- All state transitions validated via Session.transition()
- No hardcoded User model; always use settings.AUTH_USER_MODEL
