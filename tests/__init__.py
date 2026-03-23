"""
CryptoAlgoBot Test Suite

E2E testler, birim testleri ve entegrasyon testleri.
"""

# Test package marker
# Bu dosya tests/ klasörünün bir Python paketi olduğunu belirtir

# Pytest configuration
import sys
import os

# Proje kökünü Python path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
