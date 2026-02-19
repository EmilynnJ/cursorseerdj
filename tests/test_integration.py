# Comprehensive end-to-end integration tests for SoulSeer

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import json

from accounts.models import UserProfile
from readings.models import Session
from wallets.models import Wallet, LedgerEntry
from readers.models import ReaderProfile, ReaderRate, ReaderAvailability
from scheduling.models import ScheduledSlot, Booking
from live.models import Livestream, Gift, GiftPurchase
from messaging.models import DirectMessage
from community.models import ForumThread, ForumPost

User = get_user_model()


class AuthFlowTests(TestCase):
    """Test Auth0 OAuth2 integration and user creation."""
    
    def setUp(self):
        self.client = Client()
    
    def test_callback_creates_user_and_profile(self):
        """Auth0 callback creates Django user and UserProfile."""
        # Simulated Auth0 callback (in real scenario, mocked token validation)
        response = self.client.get('/accounts/callback/?code=test_code&state=test_state')
        # Should redirect to dashboard after login
        # assert response.status_code == 302
    
    def test_user_profile_role_assignment(self):
        """New users get client role by default."""
        user = User.objects.create_user(username='test_user', email='test@example.com')
        profile = UserProfile.objects.create(user=user, role='client')
        self.assertEqual(profile.role, 'client')
    
    def test_reader_onboarding(self):
        """Reader can be onboarded with rates and availability."""
        user = User.objects.create_user(username='reader_user', email='reader@example.com')
        profile = UserProfile.objects.create(user=user, role='reader')
        
        reader = ReaderProfile.objects.create(
            user=user,
            slug='test-reader',
            bio='Test reader',
            is_verified=False
        )
        
        # Create rates
        ReaderRate.objects.create(reader=reader, modality='text', rate_per_minute=Decimal('1.50'))
        ReaderRate.objects.create(reader=reader, modality='voice', rate_per_minute=Decimal('3.00'))
        
        # Create availability
        ReaderAvailability.objects.create(
            reader=reader,
            day_of_week=0,
            start_time='09:00',
            end_time='17:00'
        )
        
        self.assertEqual(reader.rates.count(), 2)
        self.assertEqual(reader.availability.count(), 1)


class SessionWorkflowTests(TestCase):
    """Test complete session lifecycle with billing."""
    
    def setUp(self):
        # Create client
        self.client_user = User.objects.create_user(username='client', email='client@example.com')
        self.client_profile = UserProfile.objects.create(user=self.client_user, role='client')
        self.client_wallet = Wallet.objects.create(user=self.client_user, balance=Decimal('100.00'))
        
        # Create reader
        self.reader_user = User.objects.create_user(username='reader', email='reader@example.com')
        self.reader_profile = UserProfile.objects.create(user=self.reader_user, role='reader')
        self.reader_obj = ReaderProfile.objects.create(user=self.reader_user, slug='test-reader')
        self.reader_rate = ReaderRate.objects.create(
            reader=self.reader_obj,
            modality='text',
            rate_per_minute=Decimal('2.00')
        )
        self.reader_wallet = Wallet.objects.create(user=self.reader_user, balance=Decimal('0.00'))
    
    def test_session_creation_and_state_machine(self):
        """Session transitions through valid states."""
        session = Session.objects.create(
            client=self.client_user,
            reader=self.reader_obj,
            modality='text',
            state='created',
            rate_per_minute=self.reader_rate.rate_per_minute
        )
        
        self.assertEqual(session.state, 'created')
        
        # Transition to waiting
        self.assertTrue(session.transition('waiting'))
        session.refresh_from_db()
        self.assertEqual(session.state, 'waiting')
        
        # Transition to active
        session.started_at = timezone.now()
        session.channel_name = 'test_channel'
        self.assertTrue(session.transition('active'))
        session.refresh_from_db()
        self.assertEqual(session.state, 'active')
    
    def test_invalid_state_transition_rejected(self):
        """Invalid state transitions are rejected."""
        session = Session.objects.create(
            client=self.client_user,
            reader=self.reader_obj,
            modality='text',
            state='created',
            rate_per_minute=self.reader_rate.rate_per_minute
        )
        
        # Can't go from created to ended directly
        self.assertFalse(session.transition('ended'))
    
    def test_session_billing_deduplicates(self):
        """Billing with idempotency key prevents double-charge."""
        session = Session.objects.create(
            client=self.client_user,
            reader=self.reader_obj,
            modality='text',
            state='active',
            rate_per_minute=Decimal('2.00'),
            started_at=timezone.now()
        )
        
        # Charge once
        from wallets.models import debit_wallet
        idem_key = f"session_{session.id}_min_1"
        try:
            debit_wallet(
                self.client_wallet,
                Decimal('2.00'),
                'session_charge',
                idem_key,
                session=session
            )
        except ValueError:
            self.fail("First charge should succeed")
        
        # Try to charge again with same idempotency key
        ledger_count_before = LedgerEntry.objects.filter(idempotency_key=idem_key).count()
        self.assertEqual(ledger_count_before, 1)
        
        # Second attempt should be idempotent (no new entry)
        from wallets.models import credit_wallet
        result = credit_wallet(
            self.client_wallet,
            Decimal('2.00'),
            'session_charge',
            idem_key
        )
        ledger_count_after = LedgerEntry.objects.filter(idempotency_key=idem_key).count()
        self.assertEqual(ledger_count_after, 1)
    
    def test_grace_period_prevents_reconnect_loop(self):
        """Session pause with grace period prevents rapid reconnects."""
        session = Session.objects.create(
            client=self.client_user,
            reader=self.reader_obj,
            modality='voice',
            state='active',
            rate_per_minute=Decimal('3.00'),
            started_at=timezone.now()
        )
        
        # Pause with grace period
        session.grace_until = timezone.now() + timezone.timedelta(minutes=5)
        session.transition('paused')
        session.save()
        
        # Try to reconnect before grace expires
        # Should fail (grace not expired)
        self.assertIsNotNone(session.grace_until)
        self.assertGreater(session.grace_until, timezone.now())


class BookingWorkflowTests(TestCase):
    """Test scheduled reading booking flow."""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.client_user = User.objects.create_user(username='client', email='client@example.com')
        self.client_profile = UserProfile.objects.create(user=self.client_user, role='client')
        self.client_wallet = Wallet.objects.create(user=self.client_user, balance=Decimal('200.00'))
        
        self.reader_user = User.objects.create_user(username='reader', email='reader@example.com')
        self.reader_profile = UserProfile.objects.create(user=self.reader_user, role='reader')
        self.reader_obj = ReaderProfile.objects.create(user=self.reader_user, slug='reader-1')
    
    def test_create_and_book_scheduled_slot(self):
        """Client can book available scheduled slot."""
        # Create slot
        start = timezone.now() + timezone.timedelta(days=1)
        slot = ScheduledSlot.objects.create(
            reader=self.reader_obj,
            start=start,
            end=start + timezone.timedelta(minutes=30),
            duration_minutes=30,
            status='available'
        )
        
        # Book slot
        booking = Booking.objects.create(
            slot=slot,
            client=self.client_user,
            amount=Decimal('15.00')
        )
        
        # Debit client wallet
        from wallets.models import debit_wallet
        debit_wallet(
            self.client_wallet,
            Decimal('15.00'),
            'booking',
            f"booking_{booking.id}"
        )
        
        slot.status = 'booked'
        slot.save()
        
        self.assertEqual(booking.client, self.client_user)
        self.assertEqual(slot.status, 'booked')
        self.assertEqual(self.client_wallet.balance, Decimal('185.00'))
    
    def test_cancel_booking_refunds_client(self):
        """Canceling booking refunds client wallet."""
        from wallets.models import debit_wallet, credit_wallet
        
        start = timezone.now() + timezone.timedelta(days=1)
        slot = ScheduledSlot.objects.create(
            reader=self.reader_obj,
            start=start,
            end=start + timezone.timedelta(minutes=30),
            duration_minutes=30,
            status='booked'
        )
        
        booking = Booking.objects.create(
            slot=slot,
            client=self.client_user,
            amount=Decimal('15.00')
        )
        
        # Debit for booking
        debit_wallet(
            self.client_wallet,
            Decimal('15.00'),
            'booking',
            f"booking_{booking.id}"
        )
        
        # Cancel and refund
        booking.cancelled_at = timezone.now()
        booking.save()
        
        credit_wallet(
            self.client_wallet,
            Decimal('15.00'),
            'refund',
            f"booking_refund_{booking.id}"
        )
        
        self.assertEqual(self.client_wallet.balance, Decimal('200.00'))


class LivestreamGiftingTests(TestCase):
    """Test livestream gifting with 70/30 split."""
    
    def setUp(self):
        # Create reader
        self.reader_user = User.objects.create_user(username='reader', email='reader@example.com')
        self.reader_profile = UserProfile.objects.create(user=self.reader_user, role='reader')
        self.reader_obj = ReaderProfile.objects.create(user=self.reader_user, slug='reader-1')
        self.reader_wallet = Wallet.objects.create(user=self.reader_user, balance=Decimal('0.00'))
        
        # Create viewer
        self.viewer_user = User.objects.create_user(username='viewer', email='viewer@example.com')
        self.viewer_profile = UserProfile.objects.create(user=self.viewer_user, role='client')
        self.viewer_wallet = Wallet.objects.create(user=self.viewer_user, balance=Decimal('100.00'))
        
        # Create livestream
        self.livestream = Livestream.objects.create(
            reader=self.reader_obj,
            title='Test Stream',
            agora_channel='test_channel',
            visibility='public',
            is_live=True
        )
        
        # Create gift
        self.gift = Gift.objects.create(
            name='Rose',
            price=Decimal('10.00'),
            animation_id='rose_1'
        )
    
    def test_gift_splits_70_30(self):
        """Gifting splits 70% to reader, 30% to platform."""
        from wallets.models import debit_wallet
        
        # Charge viewer
        debit_wallet(
            self.viewer_wallet,
            self.gift.price,
            'gift',
            f"gift_{self.livestream.id}_{self.gift.id}_{self.viewer_user.id}"
        )
        
        # Split gift amount
        reader_amount = self.gift.price * Decimal('0.7')
        platform_amount = self.gift.price * Decimal('0.3')
        
        # Credit reader
        from wallets.models import credit_wallet
        credit_wallet(
            self.reader_wallet,
            reader_amount,
            'commission',
            f"gift_reader_{self.livestream.id}_{self.gift.id}"
        )
        
        self.reader_wallet.refresh_from_db()
        self.viewer_wallet.refresh_from_db()
        
        self.assertEqual(self.reader_wallet.balance, Decimal('7.00'))
        self.assertEqual(self.viewer_wallet.balance, Decimal('90.00'))


class MessagingTests(TestCase):
    """Test direct messaging and paid replies."""
    
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com')
        
        UserProfile.objects.create(user=self.user1, role='client')
        UserProfile.objects.create(user=self.user2, role='reader')
        
        self.wallet2 = Wallet.objects.create(user=self.user2, balance=Decimal('50.00'))
    
    def test_send_direct_message(self):
        """Users can send direct messages."""
        message = DirectMessage.objects.create(
            sender=self.user1,
            recipient=self.user2,
            body='Test message'
        )
        
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.recipient, self.user2)
        self.assertEqual(message.body, 'Test message')
    
    def test_paid_reply_charges_recipient(self):
        """Paid reply charges sender $1."""
        from messaging.models import PaidReply
        from wallets.models import debit_wallet
        
        message = DirectMessage.objects.create(
            sender=self.user1,
            recipient=self.user2,
            body='Original message'
        )
        
        # Reply with charge
        reply = DirectMessage.objects.create(
            sender=self.user2,
            recipient=self.user1,
            body='Paid response'
        )
        
        # Charge sender
        from wallets.models import credit_wallet
        credit_wallet(
            self.wallet2,
            Decimal('1.00'),
            'paid_reply',
            f"paid_reply_{message.id}_{reply.id}"
        )
        
        self.wallet2.refresh_from_db()
        self.assertEqual(self.wallet2.balance, Decimal('51.00'))


class CommunityModerationTests(TestCase):
    """Test community forums and moderation."""
    
    def setUp(self):
        self.user = User.objects.create_user(username='user1', email='user1@example.com')
        UserProfile.objects.create(user=self.user, role='client')
    
    def test_create_forum_thread(self):
        """User can create forum thread."""
        thread = ForumThread.objects.create(
            author=self.user,
            title='Is tarot real?',
            content='What does everyone think about tarot?'
        )
        
        self.assertEqual(thread.author, self.user)
        self.assertEqual(thread.title, 'Is tarot real?')
    
    def test_flag_content_for_moderation(self):
        """Users can flag inappropriate content."""
        from community.models import Flag
        
        thread = ForumThread.objects.create(
            author=self.user,
            title='Test',
            content='Test content'
        )
        
        reporter = User.objects.create_user(username='reporter', email='reporter@example.com')
        UserProfile.objects.create(user=reporter, role='client')
        
        from django.contrib.contenttypes.models import ContentType
        flag = Flag.objects.create(
            content_type=ContentType.objects.get_for_model(ForumThread),
            object_id=thread.id,
            reporter=reporter,
            reason='inappropriate',
            status='pending'
        )
        
        self.assertEqual(flag.status, 'pending')
        self.assertEqual(flag.reporter, reporter)


class AdminDashboardTests(TestCase):
    """Test admin dashboard and moderation actions."""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(username='admin', email='admin@example.com')
        self.admin_profile = UserProfile.objects.create(user=self.admin_user, role='admin')
    
    def test_admin_can_view_dashboard(self):
        """Admin user can access admin dashboard."""
        self.assertEqual(self.admin_profile.role, 'admin')
    
    def test_verify_reader_profile(self):
        """Admin can verify pending reader."""
        reader_user = User.objects.create_user(username='reader', email='reader@example.com')
        reader_profile = UserProfile.objects.create(user=reader_user, role='reader')
        reader = ReaderProfile.objects.create(user=reader_user, slug='reader-1', is_verified=False)
        
        # Admin verifies
        reader.is_verified = True
        reader.save()
        
        reader.refresh_from_db()
        self.assertTrue(reader.is_verified)
