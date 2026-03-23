"""
Ubuntu Balance Fix Script

Run this on Ubuntu machine to fix negative balance issue:
    python fix_balance.py
"""

import asyncio
import sqlite3
from pathlib import Path

DB_PATH = Path("cryptobot.db")

def check_database():
    """Check database integrity"""
    print("\n" + "="*60)
    print("🔍 DATABASE INTEGRITY CHECK")
    print("="*60 + "\n")
    
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Bot hasn't been started yet or DB was deleted")
        return False
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"📊 Tables found: {[t[0] for t in tables]}")
    
    # Check trades count
    try:
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        print(f"📝 Total trades: {trade_count}")
    except Exception as e:
        print(f"❌ Error counting trades: {e}")
        trade_count = 0
    
    # Check trade PnL values
    if trade_count > 0:
        print("\n📈 Trade PnL Analysis:")
        cursor.execute("""
            SELECT 
                symbol,
                direction,
                pnl_usd,
                pnl_percent,
                reason,
                closed_at
            FROM trades 
            ORDER BY closed_at DESC 
            LIMIT 10
        """)
        
        trades = cursor.fetchall()
        for t in trades:
            symbol, direction, pnl_usd, pnl_percent, reason, closed_at = t
            print(f"  {symbol} | {direction} | PnL: ${pnl_usd:.2f} ({pnl_percent:.2f}%) | {reason}")
            
            # Check for absurd values
            if abs(pnl_usd) > 1000000:  # More than 1 million
                print(f"    ⚠️  WARNING: Absurd PnL value detected!")
    
    # Check for duplicate trades
    print("\n🔍 Checking for duplicate trades...")
    cursor.execute("""
        SELECT id, COUNT(*) as cnt
        FROM trades
        GROUP BY id
        HING cnt > 1
    """)
    duplicates = cursor.fetchall()
    if duplicates:
        print(f"  ⚠️  Found {len(duplicates)} duplicate trade IDs!")
        for d in duplicates:
            print(f"     Duplicate ID: {d[0]}")
    else:
        print("  ✅ No duplicates found")
    
    conn.close()
    return True

def fix_balance():
    """Reset balance to initial value"""
    print("\n" + "="*60)
    print("🔧 BALANCE FIX OPTIONS")
    print("="*60 + "\n")
    
    print("Choose fix option:")
    print("  1. Clear all trades (safe)")
    print("  2. Reset database completely (destructive)")
    print("  3. Just check, don't modify")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("\n🗑️  Clearing all trades...")
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trades")
        conn.commit()
        conn.close()
        print("✅ All trades cleared")
        print("   Restart bot to reset balance to $10,000")
        
    elif choice == "2":
        print("\n🗑️  Deleting database...")
        DB_PATH.unlink()
        print("✅ Database deleted")
        print("   Bot will create new DB on next start")
        
    elif choice == "3":
        print("\nℹ️  No changes made")
    
    else:
        print("\n❌ Invalid choice")

if __name__ == "__main__":
    try:
        if check_database():
            fix_balance()
    except KeyboardInterrupt:
        print("\n\n🛑 Script interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
