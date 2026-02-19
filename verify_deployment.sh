#!/bin/bash
# SoulSeer Production Build - Final Deployment Checklist

echo "🚀 SoulSeer Production Build - Final Verification"
echo "=================================================="
echo ""

# Check Python
echo "✓ Python Version Check"
python --version
echo ""

# Check Django
echo "✓ Django Setup Check"
python manage.py check
echo ""

# Run migrations
echo "✓ Database Migration Check"
python manage.py migrate --plan
echo ""

# Collect static
echo "✓ Static Files Collection"
python manage.py collectstatic --noinput
echo ""

# Run tests
echo "✓ Running Integration Tests"
python manage.py test tests.test_integration -v 2
TEST_RESULT=$?
echo ""

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ ALL TESTS PASSED"
else
    echo "❌ TESTS FAILED - FIX BEFORE DEPLOYMENT"
    exit 1
fi

echo ""
echo "=================================================="
echo "✅ DEPLOYMENT READY!"
echo "=================================================="
echo ""
echo "Next steps for Heroku deployment:"
echo "  heroku create soulseer"
echo "  heroku addons:create heroku-postgresql:standard-0"
echo "  heroku addons:create heroku-redis:premium-0"
echo "  heroku config:set \$(cat .env)"
echo "  git push heroku main"
echo "  heroku run python manage.py migrate"
echo "  heroku logs -t"
echo ""
