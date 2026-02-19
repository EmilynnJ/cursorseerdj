# SoulSeer

Production-ready spiritual reading platform. Django monolith with Auth0, Stripe, Agora RTC/RTM, Celery, Neon Postgres.

## Setup

1. Create virtualenv and install deps:
   ```
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your secrets (Neon DB, Auth0, Stripe, Agora).

3. Run migrations:
   ```
   python manage.py migrate
   ```

4. Create superuser:
   ```
   python manage.py createsuperuser
   ```

5. Run dev server:
   ```
   python manage.py runserver
   ```

6. For Celery (billing tick):
   ```
   celery -A soulseer worker -l info
   celery -A soulseer beat -l info
   ```

## Stripe Webhook

Point Stripe webhook to: `https://your-domain.com/stripe/webhook/`

## Auth0

Configure Auth0 Application:
- Application Type: Regular Web Application
- Allowed Callback URLs: `http://localhost:8000/accounts/callback/`
- Allowed Logout URLs: `http://localhost:8000/`
