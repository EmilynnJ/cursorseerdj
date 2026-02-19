# SoulSeer Security & Compliance Checklist

**Last Updated**: February 2026 | **Framework**: Django 5.0+ | **Standards**: GDPR, CCPA, PCI-DSS

## Authentication & Authorization

### Auth0 OAuth2
- [x] Auth0 integration complete (OAuth2 flow)
- [x] State token verification (CSRF protection)
- [x] JWT signature verification (RS256)
- [x] UserProfile role assignment on signup
- [ ] Auth0 MFA/2FA (optional but recommended)
- [ ] Session timeout (30 min inactivity)
- [ ] Force logout on password change

### Role-Based Access Control (RBAC)
- [x] UserProfile.role field (client/reader/admin)
- [x] @require_role decorator enforces access
- [x] @staff_member_required for Django admin
- [ ] Permission matrix documented (FEATURE_ACCEPTANCE_CRITERIA.md)
- [ ] Admin user creation: manual + audit logged

### Password & Secret Management
- [x] Django's password hashing (PBKDF2 default)
- [x] All secrets in environment variables (no hardcoding)
- [x] .env in .gitignore (no secrets in version control)
- [ ] Secrets rotation (Stripe, Auth0 keys annually)
- [ ] API key storage in secrets manager (AWS Secrets Manager, HashiCorp Vault)

---

## Data Protection

### GDPR Compliance
- [x] Data export endpoint: `/accounts/export/` (JSON)
- [x] Account deletion endpoint: `/accounts/delete-account/`
- [ ] Deletion confirmation email (verify delete request)
- [ ] GDPR policy page (`/privacy/`)
- [ ] Data retention policy documented
- [ ] Third-party data sharing policy disclosed
- [ ] PII anonymization on deletion (nullify email, delete notes)

### CCPA Compliance (California)
- [ ] "Do Not Sell" link on homepage
- [ ] Consumer rights page (`/ccpa/`)
- [ ] Delete-on-request workflow (30-day response)
- [ ] Opt-out tracking (cookies/analytics)

### Data Encryption
- [x] TLS/HTTPS enforced (Heroku + Cloudflare)
- [x] Database password encrypted in CONNECTION_STRING
- [x] No credit card data stored (Stripe handles PCI)
- [ ] Database encryption at rest (Neon: optional Premium feature)
- [ ] Email/phone number encrypted in UserProfile (optional)

### Database Backups
- [x] Neon auto-backup (7-day retention)
- [ ] Daily backup to S3/R2 (versioning enabled)
- [ ] Disaster recovery plan documented
- [ ] RTO/RPO defined (Recovery Time/Point Objective)

---

## PCI-DSS (Payment Security)

### Stripe Integration
- [x] No card data stored locally (Stripe Checkout handles PCI)
- [x] Stripe webhook signature verification
- [x] payment_intent_id logged (not full card)
- [x] stripe_event_id tracking (ProcessedStripeEvent)
- [ ] PCI compliance certificate from Stripe (Level 1)
- [ ] Card data handling policy documented

### Idempotency & Duplicate Prevention
- [x] LedgerEntry.idempotency_key (unique constraint)
- [x] ProcessedStripeEvent (webhook replay prevention)
- [x] Stripe.Webhook.construct_event() signature check
- [x] debit_wallet/credit_wallet atomic transactions
- [ ] Duplicate transaction alert (Sentry monitoring)

---

## API Security

### Endpoint Protection
- [x] @login_required decorator (view-level auth)
- [x] @require_role (role-based access)
- [x] @require_POST (method-specific CSRF)
- [x] @csrf_exempt only for webhooks (with signature verification)
- [ ] API rate limiting (5 req/min login, 10 msg/min messaging)
- [ ] DDoS mitigation (Cloudflare Free tier)

### Webhook Security
- [x] Stripe webhook signature verification
- [x] ProcessedStripeEvent prevents replay
- [ ] Webhook retry logic (exponential backoff)
- [ ] Webhook timeout (request.timeout=10 seconds)
- [ ] Webhook logging (all events to AuditLog)

### CORS & XSS Prevention
- [x] Django CSRF token in forms
- [x] SameSite=Strict cookie (Django default)
- [ ] Content-Security-Policy header configured
- [ ] X-Frame-Options: DENY (clickjacking)
- [ ] X-XSS-Protection enabled

### SQL Injection & ORM Safety
- [x] Django ORM used (parameterized queries)
- [ ] No raw SQL in views
- [ ] Query validation in search/filter endpoints

---

## Audit Logging

### Implemented
- [x] AuditLog model (user, action, model_name, object_id, details, created_at)

### Required Logging
- [ ] Wallet adjustments (admin-initiated)
- [ ] Refunds (reason logged)
- [ ] Session cancellations
- [ ] Admin role changes
- [ ] Reader verification status changes
- [ ] Moderation actions (flag resolved/dismissed)
- [ ] Data export requests
- [ ] Account deletions

### Log Storage & Retention
- [ ] Sentry for error tracking (configured)
- [ ] Django logs to file/stdout (Heroku captures)
- [ ] Logs retained for 90 days (audit compliance)
- [ ] Log search capability (Sentry dashboard)

---

## Compliance Policies

### Privacy Policy (`/privacy/`)
- [ ] Data collection disclosed
- [ ] Third-party sharing (Auth0, Stripe, Agora)
- [ ] Cookies & tracking explained
- [ ] GDPR/CCPA rights explained
- [ ] Contact info for privacy questions
- [ ] Last updated date

### Terms of Service (`/terms/`)
- [ ] User obligations and restrictions
- [ ] Payment terms (non-refundable sessions)
- [ ] Intellectual property / content ownership
- [ ] Disclaimer of warranties
- [ ] Limitation of liability
- [ ] Dispute resolution (arbitration or court)
- [ ] Governing law (e.g., California)

### Help Center (`/help/`)
- [ ] How to top-up wallet
- [ ] Session cancellation policy
- [ ] Refund request process
- [ ] How to report abuse
- [ ] Contact support email
- [ ] FAQ (common issues)

### Content Moderation Policy
- [ ] Prohibited content defined
- [ ] Flagging process explained
- [ ] Appeal process for falsely flagged content
- [ ] Enforcement actions (warning → suspension → termination)

---

## Third-Party Integrations

### Auth0
- [x] OAuth2 flow
- [ ] Compliance: SOC 2 Type II
- [ ] Data processing agreement (DPA) signed
- [ ] No sensitive data beyond OAuth payload

### Stripe
- [x] Checkout & Payment Intents
- [ ] Compliance: PCI Level 1, SOC 2
- [ ] DPA signed
- [ ] Webhook security implemented

### Agora
- [x] RTC & RTM SDKs
- [ ] Compliance: SOC 2 Type II
- [ ] DPA signed
- [ ] Encryption for media (Agora handles)
- [ ] Token TTL enforced (1200s max)

### Cloudflare R2 / S3
- [ ] Compliance: SOC 2
- [ ] Bucket encryption enabled
- [ ] Signed URLs for downloads (time-limited)
- [ ] Object versioning enabled

### Sentry
- [ ] Error logging configured
- [ ] Sensitive data filtering (email/phone redacted)
- [ ] Compliance: SOC 2 Type II
- [ ] DPA signed

---

## Testing & QA

### Security Testing
- [ ] OWASP Top 10 vulnerability scan (NIST)
- [ ] SQL injection testing
- [ ] XSS payload testing
- [ ] CSRF token validation
- [ ] Authentication bypass attempts
- [ ] Authorization boundary testing
- [ ] Penetration testing (annual)

### Data Privacy Testing
- [ ] Data export completeness (all user data captured)
- [ ] Deletion verification (no residual data)
- [ ] PII redaction on logs
- [ ] Backup encryption validation

### Integration Testing
- [ ] Stripe webhook replay (ProcessedStripeEvent)
- [ ] Auth0 token expiration handling
- [ ] Agora token refresh
- [ ] Session billing edge cases

---

## Incident Response

### Breach Notification Plan
- [ ] Breach detection process (Sentry alerts)
- [ ] Escalation path (to CEO/Legal/CTO)
- [ ] Notification timeline (GDPR: 72 hours)
- [ ] Communication template (to affected users)
- [ ] Post-incident review (root cause analysis)

### Data Incident Response
- [ ] Wallet balance discrepancy → investigate ledger
- [ ] Session billing error → refund + investigation
- [ ] Unauthorized access → force logout + password reset
- [ ] Stripe webhook failure → Celery retry (3x)

### Disaster Recovery
- [ ] RTO: 4 hours (max downtime)
- [ ] RPO: 1 hour (max data loss)
- [ ] Database restore from backup: tested quarterly
- [ ] Failover procedure documented

---

## Monitoring & Alerts

### Sentry Alerts
- [ ] Errors above threshold (50+ same error in 1h)
- [ ] Webhook failures (Stripe, Agora)
- [ ] Database connection errors
- [ ] Celery task failures

### Uptime Monitoring
- [ ] UptimeRobot: /health endpoint (5-min interval)
- [ ] Heroku metrics: dyno uptime, response time
- [ ] Redis availability (cache/queue)

### Performance Monitoring
- [ ] Page load time < 2 seconds (Lighthouse)
- [ ] API response time < 200ms (P95)
- [ ] Celery task completion time < 60s (billing_tick)
- [ ] Database query performance (select_related optimization)

### Security Monitoring
- [ ] Failed login attempts (5+ → throttle IP)
- [ ] Unusual wallet transfers (refund > balance)
- [ ] Admin action frequency (multiple deletions in short time)
- [ ] Rate limit violations (suspicious patterns)

---

## Compliance Checklist (Pre-Launch)

- [ ] Privacy policy signed off by Legal
- [ ] Terms of Service signed off by Legal
- [ ] GDPR data processing agreement (Stripe, Auth0, Agora)
- [ ] CCPA policy page live
- [ ] Data export working (test with real account)
- [ ] Account deletion working (verify PII removal)
- [ ] SSL/HTTPS enforced (no redirect loops)
- [ ] Audit logging implemented and tested
- [ ] Sentry monitoring active
- [ ] Stripe webhook signature verified in code
- [ ] Rate limiting configured
- [ ] Secrets not in version control
- [ ] Stripe PCI compliance confirmed
- [ ] Auth0 MFA (optional) enabled
- [ ] Backup & disaster recovery tested
- [ ] Security headers configured (CSP, X-Frame-Options)
- [ ] Penetration test results reviewed (if applicable)

---

## Annual Review Schedule

| Task | Frequency | Owner | Next Date |
|------|-----------|-------|-----------|
| Security audit | Annual | CTO | TBD |
| Penetration testing | Annual | Third-party | TBD |
| Compliance review (GDPR/CCPA) | Annual | Legal | TBD |
| Password/API key rotation | Quarterly | DevOps | TBD |
| Backup restoration test | Quarterly | DevOps | TBD |
| DPA renewal with vendors | Annual | Legal | TBD |
| Incident response drills | Semi-annual | Security | TBD |

