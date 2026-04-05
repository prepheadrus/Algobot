"""
Duplicate Trade Temizleme Scripti

Veritabanındaki duplicate trade kayıtlarını temizler.
"""

import sqlite3

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
    
    # Tüm duplicate'ler için toplu silme işlemi (Bulk Delete)
    cursor.execute("""
        DELETE FROM trades
        WHERE id IN (
            SELECT id
            FROM trades
            GROUP BY id
            HAVING COUNT(*) > 1
        )
        AND rowid NOT IN (
            SELECT MIN(rowid)
            FROM trades
            GROUP BY id
        )
    """)
    
    total_deleted = cursor.rowcount
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
