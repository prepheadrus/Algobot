"""
Test Runner Script
Testleri doğrudan Python'dan çalıştırır.
"""

import sys
import asyncio

# Testleri import et
sys.path.insert(0, 'f:/Crypto Bot')

async def run_double_close_tests():
    """Double-close testlerini çalıştır"""
    print("=" * 60)
    print("🧪 DOUBLE-CLOSE TESTLERİ BAŞLIYOR")
    print("=" * 60)
    
    from tests.test_double_close import (
        test_no_duplicate_position_close,
        test_closed_bot_ids_prevents_second_close,
        test_concurrent_close_attempts
    )
    
    tests = [
        ("test_no_duplicate_position_close", test_no_duplicate_position_close),
        ("test_closed_bot_ids_prevents_second_close", test_closed_bot_ids_prevents_second_close),
        ("test_concurrent_close_attempts", test_concurrent_close_attempts),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n▶️  {test_name}...")
            await test_func()
            print(f"✅ {test_name} - PASSED")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name} - FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"SONUÇ: {passed} PASSED, {failed} FAILED")
    print(f"{'=' * 60}\n")
    
    return failed == 0


async def run_zombie_tests():
    """Zombie position testlerini çalıştır"""
    print("=" * 60)
    print("🧟 ZOMBIE POSITION TESTLERİ BAŞLIYOR")
    print("=" * 60)
    
    from tests.test_zombie_position import (
        test_zombie_prevention_on_db_error,
        test_zombie_prevention_on_remove_error,
        test_retry_after_zombie_unlock,
        test_finally_block_resets_lock
    )
    
    tests = [
        ("test_zombie_prevention_on_db_error", test_zombie_prevention_on_db_error),
        ("test_zombie_prevention_on_remove_error", test_zombie_prevention_on_remove_error),
        ("test_retry_after_zombie_unlock", test_retry_after_zombie_unlock),
        ("test_finally_block_resets_lock", test_finally_block_resets_lock),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n▶️  {test_name}...")
            await test_func()
            print(f"✅ {test_name} - PASSED")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name} - FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"SONUÇ: {passed} PASSED, {failed} FAILED")
    print(f"{'=' * 60}\n")
    
    return failed == 0


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 KRİTİK BUG TESTLERİ BAŞLIYOR")
    print("=" * 60 + "\n")
    
    # Double-close testleri
    dc_passed = asyncio.run(run_double_close_tests())
    
    # Zombie position testleri
    zb_passed = asyncio.run(run_zombie_tests())
    
    # Final rapor
    print("\n" + "=" * 60)
    print("📊 FINAL RAPOR")
    print("=" * 60)
    
    if dc_passed and zb_passed:
        print("\n✅✅✅ KRİTİK BUG TESTLERİ BAŞARILI! ✅✅✅\n")
        print("Tüm race condition ve zombie position testleri PASSED!")
        print("Sistem production-ready! 🚀\n")
    else:
        print("\n❌ BAZI TESTLER FAILED!")
        if not dc_passed:
            print("  - Double-close testleri başarısız")
        if not zb_passed:
            print("  - Zombie position testleri başarısız")
        print("\nLütfen hataları düzeltin ve tekrar deneyin.\n")
    
    print("=" * 60 + "\n")
