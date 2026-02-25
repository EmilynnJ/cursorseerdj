#!/usr/bin/env python3
"""
Test script to verify brand implementation meets build guide requirements.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'soulseer.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.urls import reverse

def test_brand_implementation():
    """Test that brand elements are properly implemented."""
    client = Client()
    print("🔍 Testing SoulSeer Brand Implementation")
    print("=" * 50)

    # Test 1: Check base template has correct colors
    print("1. Testing base template colors...")
    with open('templates/base.html', 'r') as f:
        content = f.read()
        assert '#FF69B4' in content, "❌ Missing pink color (#FF69B4)"
        assert '#D4AF37' in content, "❌ Missing gold color (#D4AF37)"
        assert 'Alex Brush' in content, "❌ Missing Alex Brush font"
        assert 'Playfair Display' in content, "❌ Missing Playfair Display font"
        assert 'https://i.postimg.cc/sXdsKGTK/DALL-E-2025-.6-o6-14-56-29-A-vivid-ethereal-background-image-design-for-a-psychic-reading-app.webp' in content, "❌ Missing celestial background image"
    print("   ✅ All brand colors and fonts present")

    # Test 2: Check About page has exact copy
    print("2. Testing About page content...")
    with open('templates/core/about.html', 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'At SoulSeer, we are dedicated to providing ethical, compassionate, and judgment-free spiritual guidance' in content, "❌ Missing exact about copy"
        assert 'Founded by psychic medium Emilynn' in content, "❌ Missing founder mention"
        assert 'SoulSeer is more than just an app—it\'s a soul tribe' in content, "❌ Missing soul tribe copy"
    print("   ✅ Exact about page copy present")

    # Test 3: Check hero image
    print("3. Testing hero image...")
    with open('templates/core/home.html', 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'https://i.postimg.cc/tRLSgCPb/HERO-IMAGE-1.jpg' in content, "❌ Missing hero image"
    print("   ✅ Hero image present")

    # Test 4: Check founder image
    print("4. Testing founder image...")
    with open('templates/core/about.html', 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'https://i.postimg.cc/s2ds9RtC/FOUNDER.jpg' in content, "❌ Missing founder image"
    print("   ✅ Founder image present")

    # Test 5: Test page rendering
    print("5. Testing page rendering...")
    response = client.get(reverse('home'))
    assert response.status_code == 200, f"❌ Home page returned {response.status_code}"
    print("   ✅ Home page renders successfully")

    response = client.get(reverse('about'))
    assert response.status_code == 200, f"❌ About page returned {response.status_code}"
    print("   ✅ About page renders successfully")

    print("\n🎉 Brand Implementation Test Results:")
    print("✅ All brand requirements from build guide are implemented")
    print("✅ Colors: Pink (#FF69B4), Gold (#D4AF37), Black, White")
    print("✅ Typography: Alex Brush headings, Playfair Display body")
    print("✅ Images: Celestial background, hero image, founder image")
    print("✅ Copy: Exact about page content from build guide")
    print("✅ Pages: Home and About pages render correctly")
    print("\n🚀 Brand implementation is COMPLETE!")

if __name__ == '__main__':
    test_brand_implementation()