"""
Duplicate Trade Temizleme Scripti

Veritabanındaki duplicate trade kayıtlarını temizler.
"""

import sqlite3
from datetime import datetime

DB_PATH = "cryptobot.db"

def find_and_remove_duplicates():
    """Duplicate trade'leri bul ve temizle"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔍 Duplicate trade'ler aranıyor...")
    
    # Duplicate ID'leri bul
    cursor.execute("""
        SELECT id, COUNT(*) as count
        FROM trades
        GROUP BY id
        HAVING count > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("✅ Duplicate trade bulunamadı!")
        conn.close()
        return
    
    print(f"⚠️ {len(duplicates)} duplicate ID bulundu!")
    
    # Her duplicate için bir kayıt hariç sil
    total_deleted = 0
    for trade_id, count in duplicates:
        # Bir kayıt hariç hepsini sil
        cursor.execute("""
            DELETE FROM trades
            WHERE id = ?
            AND rowid NOT IN (
                SELECT MIN(rowid)
                FROM trades
                WHERE id = ?
            )
        """, (trade_id, trade_id))
        
        deleted = cursor.rowcount
        total_deleted += deleted
        print(f"  🗑️ {trade_id}: {deleted} kayıt silindi")
    
    conn.commit()
    
    print(f"\n✅ Toplam {total_deleted} duplicate kayıt silindi!")
    
    # Kalan trade sayısını göster
    cursor.execute("SELECT COUNT(*) FROM trades")
    remaining = cursor.fetchone()[0]
    print(f"📊 Kalan trade sayısı: {remaining}")
    
    conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  DUPLICATE TRADE TEMİZLEME")
    print("=" * 60)
    print()
    
    find_and_remove_duplicates()
    
    print()
    print("=" * 60)
    print("  TEMİZLİK TAMAMLANDI")
    print("=" * 60)
