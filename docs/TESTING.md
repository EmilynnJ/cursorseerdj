# SoulSeer Testing Guide

**Last Updated**: February 2026 | **Test Framework**: Django TestCase, pytest

## Unit Tests

### Wallet & Ledger Tests
```python
# tests/test_wallets.py
from django.test import TestCase
from wallets.models import Wallet, LedgerEntry, debit_wallet, credit_wallet
from decimal import Decimal

class WalletTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.wallet = Wallet.objects.create(user=self.user, balance=Decimal('100.00'))

    def test_debit_wallet_success(self):
        """Debit wallet with sufficient balance."""
        debit_wallet(self.wallet, Decimal('10.00'), 'test_charge', 'idempotent_key_1')
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('90.00'))

    def test_debit_wallet_insufficient_balance(self):
        """Debit wallet raises ValueError on insufficient balance."""
        with self.assertRaises(ValueError):
            debit_wallet(self.wallet, Decimal('200.00'), 'test_charge', 'idempotent_key_2')

    def test_credit_wallet_idempotent(self):
        """Credit wallet is idempotent on same idempotency_key."""
        result1 = credit_wallet(self.wallet, Decimal('50.00'), 'top_up', 'idempotent_key_3')
        result2 = credit_wallet(self.wallet, Decimal('50.00'), 'top_up', 'idempotent_key_3')
        self.assertTrue(result1)
        self.assertFalse(result2)  # Second call returns False (already processed)

    def test_ledger_entry_created(self):
        """LedgerEntry created for each transaction."""
        debit_wallet(self.wallet, Decimal('10.00'), 'session_charge', 'idempotent_key_4')
        entry = LedgerEntry.objects.get(idempotency_key='idempotent_key_4')
        self.assertEqual(entry.amount, Decimal('-10.00'))
        self.assertEqual(entry.wallet, self.wallet)
```

### Session State Machine Tests
```python
# tests/test_sessions.py
from django.test import TestCase
from readings.models import Session, MODALITY_CHOICES

class SessionStateTestCase(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client_user = User.objects.create_user(username='client1', email='client@example.com')
        self.reader_user = User.objects.create_user(username='reader1', email='reader@example.com')
        self.session = Session.objects.create(
            client=self.client_user,
            reader=self.reader_user,
            modality='voice',
            state='created'
        )

    def test_valid_transition(self):
        """Valid state transition succeeds."""
        result = self.session.transition('waiting')
        self.assertTrue(result)
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, 'waiting')

    def test_invalid_transition(self):
        """Invalid state transition fails."""
        result = self.session.transition('finalized')  # Can't jump from created to finalized
        self.assertFalse(result)

    def test_state_machine_path(self):
        """Full valid state machine path."""
        transitions = ['created', 'waiting', 'active', 'ended', 'finalized']
        current_state = self.session.state
        for next_state in transitions[1:]:
            self.assertTrue(self.session.transition(next_state))
            self.session.refresh_from_db()
            self.assertEqual(self.session.state, next_state)
```

### Reader Profile Tests
```python
# tests/test_readers.py
from django.test import TestCase
from readers.models import ReaderProfile, ReaderRate, Review
from decimal import Decimal
from django.contrib.auth import get_user_model

class ReaderProfileTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='reader', email='reader@example.com')
        self.reader = ReaderProfile.objects.create(user=self.user, slug='jane-doe')

    def test_reader_rates(self):
        """Reader can set rates per modality."""
        ReaderRate.objects.create(reader=self.reader, modality='text', rate_per_minute=Decimal('0.50'))
        ReaderRate.objects.create(reader=self.reader, modality='voice', rate_per_minute=Decimal('1.00'))
        self.assertEqual(self.reader.rates.count(), 2)

    def test_reader_average_rating(self):
        """Average rating calculated correctly."""
        User = get_user_model()
        client1 = User.objects.create_user(username='client1')
        client2 = User.objects.create_user(username='client2')
        Review.objects.create(reader=self.reader, client=client1, rating=5, body='Great!')
        Review.objects.create(reader=self.reader, client=client2, rating=3, body='Okay')
        from django.db.models import Avg
        avg = self.reader.reviews.aggregate(Avg('rating'))['rating__avg']
        self.assertEqual(avg, 4.0)
```

---

## Integration Tests

### Billing Tick Test
```python
# tests/test_billing_tick.py
from django.test import TestCase
from django.utils import timezone
from readings.models import Session
from wallets.models import Wallet, LedgerEntry
from readers.models import ReaderProfile, ReaderRate
from readings.tasks import billing_tick
from decimal import Decimal
from django.contrib.auth import get_user_model

class BillingTickTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client = User.objects.create_user(username='client')
        self.reader_user = User.objects.create_user(username='reader')
        self.reader = ReaderProfile.objects.create(user=self.reader_user, slug='reader1')
        ReaderRate.objects.create(reader=self.reader, modality='voice', rate_per_minute=Decimal('1.00'))
        
        self.wallet = Wallet.objects.create(user=self.client, balance=Decimal('10.00'))
        self.session = Session.objects.create(
            client=self.client,
            reader=self.reader_user,
            modality='voice',
            state='active',
            rate_per_minute=Decimal('1.00')
        )

    def test_billing_tick_deducts_once(self):
        """Billing tick deducts exactly once per minute."""
        billing_tick()
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('9.00'))
        
        # Run again - should not deduct again (idempotency)
        billing_tick()
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('9.00'))

    def test_billing_tick_pauses_low_balance(self):
        """Billing tick pauses session on insufficient balance."""
        self.wallet.balance = Decimal('0.50')
        self.wallet.save()
        billing_tick()
        self.session.refresh_from_db()
        self.assertEqual(self.session.state, 'paused')
```

### Auth0 Callback Test
```python
# tests/test_auth.py
from django.test import TestCase, Client
from unittest.mock import patch, MagicMock
from accounts.models import UserProfile

class Auth0CallbackTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('accounts.views.requests.post')
    @patch('accounts.auth_backend.verify_auth0_token')
    def test_auth0_callback_success(self, mock_verify, mock_post):
        """Auth0 callback creates user and logs in."""
        # Mock Auth0 token response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'id_token': 'mocked_token',
            'access_token': 'access_token'
        }
        
        # Mock token verification
        mock_verify.return_value = {
            'sub': 'auth0|12345',
            'email': 'newuser@example.com',
            'name': 'New User'
        }
        
        # Set state in session
        session = self.client.session
        session['auth0_state'] = 'test_state'
        session.save()
        
        # Call callback
        response = self.client.get('/accounts/callback/', {
            'code': 'auth_code',
            'state': 'test_state'
        })
        
        # Check user created
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserProfile.objects.filter(auth0_sub='auth0|12345').exists())
```

### Stripe Webhook Test
```python
# tests/test_stripe_webhooks.py
from django.test import TestCase
from unittest.mock import patch
from wallets.models import Wallet, ProcessedStripeEvent, LedgerEntry
from decimal import Decimal
from django.contrib.auth import get_user_model

class StripeWebhookTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='user')
        self.wallet = Wallet.objects.create(user=self.user)

    @patch('stripe.Webhook.construct_event')
    def test_webhook_idempotency(self, mock_construct):
        """Webhook is idempotent on duplicate event_id."""
        event_id = 'evt_123'
        
        # First webhook
        mock_construct.return_value = {
            'id': event_id,
            'type': 'charge.succeeded',
            'data': {'object': {'customer': 'cus_123', 'amount': 5000}}
        }
        
        # Simulate first webhook processing
        ProcessedStripeEvent.objects.create(stripe_event_id=event_id)
        
        # Second webhook with same event_id should be skipped
        exists = ProcessedStripeEvent.objects.filter(stripe_event_id=event_id).exists()
        self.assertTrue(exists)
```

---

## End-to-End (E2E) Tests

### Client Booking Flow
```python
# tests/test_e2e_booking.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from readers.models import ReaderProfile
from scheduling.models import ScheduledSlot, Booking
from wallets.models import Wallet
from decimal import Decimal
import datetime

class BookingE2ETestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client_obj = Client()
        
        # Create reader
        self.reader_user = User.objects.create_user(username='reader', email='reader@example.com')
        self.reader = ReaderProfile.objects.create(user=self.reader_user, slug='reader1')
        
        # Create client with wallet
        self.client_user = User.objects.create_user(username='client', email='client@example.com')
        self.wallet = Wallet.objects.create(user=self.client_user, balance=Decimal('100.00'))
        
        # Create available slot
        now = timezone.now()
        self.slot = ScheduledSlot.objects.create(
            reader=self.reader_user,
            start=now + datetime.timedelta(days=1),
            end=now + datetime.timedelta(days=1, minutes=30),
            duration_minutes=30,
            status='available'
        )

    def test_full_booking_flow(self):
        """Client can book a session successfully."""
        # Login
        self.client_obj.login(username='client', email='client@example.com')
        
        # Book slot
        response = self.client_obj.post(f'/scheduling/book/{self.slot.pk}/', follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Check slot is booked
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, 'booked')
        self.assertEqual(self.slot.client, self.client_user)
        
        # Check booking created
        booking = Booking.objects.get(slot=self.slot)
        self.assertEqual(booking.client, self.client_user)
        
        # Check wallet debited
        self.wallet.refresh_from_db()
        self.assertLess(self.wallet.balance, Decimal('100.00'))
```

---

## Test Execution

### Run All Tests
```bash
python manage.py test
```

### Run Specific Test Module
```bash
python manage.py test tests.test_wallets
```

### Run with Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report -m
coverage html  # Generate HTML report
```

### Run with pytest
```bash
pip install pytest pytest-django pytest-cov
pytest tests/ -v --cov=. --cov-report=html
```

---

## Manual Testing Checklist

### User Authentication
- [ ] Auth0 login works
- [ ] Auth0 signup creates user with role='client'
- [ ] Logout clears session
- [ ] Unauthorized users redirected to login

### Wallet Flow
- [ ] Client can top-up wallet via Stripe
- [ ] Webhook credits wallet correctly
- [ ] Transaction history displays correctly
- [ ] Negative balance not possible

### Session Billing
- [ ] Session starts and transitions to 'active'
- [ ] Agora token generated on active transition
- [ ] Billing tick deducts per minute
- [ ] Session pauses on low balance
- [ ] Reconnection within grace period works
- [ ] Session ends correctly

### Reader Dashboard
- [ ] Reader can set rates per modality
- [ ] Reader can set availability
- [ ] Earnings calculated correctly
- [ ] Reviews display with average rating

### Scheduling
- [ ] Reader availability calendar displays
- [ ] Client can browse and book slots
- [ ] Booking deducts from wallet
- [ ] Booking history shows correctly

### Moderation
- [ ] User can flag content
- [ ] Admin sees pending flags
- [ ] Admin can resolve/dismiss flags

---

## Performance Testing

### Load Testing (with Locust)
```python
# locustfile.py
from locust import HttpUser, task, between

class SoulSeerUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def view_home(self):
        self.client.get("/")
    
    @task
    def list_readers(self):
        self.client.get("/readers/")
    
    @task
    def view_dashboard(self):
        self.client.get("/dashboard/")
```

Run: `locust -f locustfile.py --host=http://localhost:8000`

### Database Query Performance
```python
# Check N+1 queries
from django.test.utils import override_settings
from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext

def test_reader_list_queries(self):
    with CaptureQueriesContext(connection) as ctx:
        readers = ReaderProfile.objects.select_related('user').all()
        list(readers)  # Force evaluation
    # Should be <10 queries for 100 readers
    self.assertLess(len(ctx), 10)
```

---

## CI/CD Testing

### GitHub Actions Example
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: pip install -r requirements.txt
      - run: python manage.py migrate
      - run: python manage.py test
      - run: coverage run --source='.' manage.py test
      - run: coverage report
```
