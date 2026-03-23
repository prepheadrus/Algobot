#!/usr/bin/env python3
"""
Auto-Doc Bot - Otomatik Dokümantasyon Güncelleme Scripti

Her git commit'tan sonra çalışır ve docs/architecture/ klasöründeki
3 ana dokümanı otomatik günceller.

Kullanım:
    python scripts/auto_doc_bot.py
"""

import subprocess
import re
from pathlib import Path
from datetime import datetime

# Renkli terminal çıktıları
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'

def log(message: str, color: str = Colors.BLUE):
    print(f"{color}{message}{Colors.END}")

def get_last_commit_info():
    """Son commit bilgilerini al."""
    try:
        # Son commit mesajı
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=%s'],
            capture_output=True, text=True, check=True
        )
        commit_message = result.stdout.strip()
        
        # Değişen dosyalar
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD'],
            capture_output=True, text=True, check=True
        )
        changed_files = result.stdout.strip().split('\n')
        
        return commit_message, changed_files
    except subprocess.CalledProcessError as e:
        log(f"❌ Git komut hatası: {e}", Colors.RED)
        return None, []

def analyze_changes(changed_files: list):
    """Değişiklikleri analiz et ve hangi dokümanın güncelleneceğini belirle."""
    
    doc_updates = {
        'MASTER_PROJE_DESTANI.md': [],
        'TASKS_AND_TRACEABILITY.md': [],
        'TRADING_RULES_AND_RISK.md': []
    }
    
    for file in changed_files:
        # Mimari değişiklikler
        if any(x in file for x in ['core/', 'shared/events/', 'bot_manager.py', 'position_manager.py']):
            doc_updates['MASTER_PROJE_DESTANI.md'].append(f"- `{file}` güncellendi")
        
        # API/Endpoint değişiklikleri
        if 'api/routers/' in file or 'api/services/' in file:
            doc_updates['TASKS_AND_TRACEABILITY.md'].append(f"- API Endpoint: `{file}`")
        
        # ML değişiklikleri
        if 'ml/' in file:
            doc_updates['TASKS_AND_TRACEABILITY.md'].append(f"- ML: `{file}`")
        
        # Risk/Komisyon değişiklikleri
        if 'risk_engine.py' in file or 'config.yaml' in file:
            doc_updates['TRADING_RULES_AND_RISK.md'].append(f"- Risk Parametresi: `{file}`")
        
        # Frontend değişiklikleri
        if 'frontend/' in file:
            doc_updates['TASKS_AND_TRACEABILITY.md'].append(f"- UI: `{file}`")
        
        # Strategy değişiklikleri
        if 'strategy/' in file:
            doc_updates['MASTER_PROJE_DESTANI.md'].append(f"- Strateji: `{file}`")
    
    return doc_updates

def update_version_in_doc(filepath: Path):
    """Dokümandaki versiyon numarasını güncelle."""
    if not filepath.exists():
        return False
    
    content = filepath.read_text(encoding='utf-8')
    
    # Versiyon satırını bul ve güncelle
    today = datetime.now().strftime('%d %B %Y')
    
    # **Versiyon:** v4.0 → v4.1
    content = re.sub(
        r'\*\*Versiyon:\*\* v(\d+)\.(\d+)',
        lambda m: f'**Versiyon:** v{m.group(1)}.{int(m.group(2))+1}',
        content
    )
    
    # **Son Güncelleme:** Mart 2026 → 17 Mart 2026
    content = re.sub(
        r'\*\*Son Güncelleme:\*\* .+',
        f'**Son Güncelleme:** {today}',
        content
    )
    
    filepath.write_text(content, encoding='utf-8')
    return True

def append_update_to_doc(filepath: Path, updates: list, commit_message: str):
    """Dokümanın sonuna güncelleme notu ekle."""
    if not updates:
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    update_section = f"""

---

## 🔄 Otomatik Güncelleme ({today})

**Commit:** {commit_message}

**Değişiklikler:**
"""
    
    for update in updates:
        update_section += f"{update}\n"
    
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(update_section)
    
    log(f"✅ {filepath.name} güncellendi", Colors.GREEN)

def update_docs_directory():
    """docs/architecture/ klasöründeki tüm dokümanları güncelle."""
    docs_dir = Path('docs/architecture')
    
    if not docs_dir.exists():
        log(f"❌ {docs_dir} klasörü bulunamadı!", Colors.RED)
        return False
    
    log("🔍 Son commit analizi yapılıyor...", Colors.BLUE)
    commit_message, changed_files = get_last_commit_info()
    
    if not commit_message:
        return False
    
    log(f"📝 Commit mesajı: {commit_message}", Colors.BLUE)
    log(f"📁 Değişen dosyalar: {len(changed_files)}", Colors.BLUE)
    
    # Değişiklikleri analiz et
    doc_updates = analyze_changes(changed_files)
    
    # Her dokümanı güncelle
    for doc_name, updates in doc_updates.items():
        doc_path = docs_dir / doc_name
        
        if updates:
            log(f"📄 {doc_name} güncelleniyor...", Colors.YELLOW)
            update_version_in_doc(doc_path)
            append_update_to_doc(doc_path, updates, commit_message)
        else:
            log(f"⏭️ {doc_name} için değişiklik yok", Colors.BLUE)
    
    log("\n✅ Otomatik dokümantasyon güncelleme tamamlandı!", Colors.GREEN)
    return True

if __name__ == '__main__':
    log("=" * 70, Colors.BLUE)
    log("🤖 AUTO-DOC BOT - Otomatik Dokümantasyon Güncelleme", Colors.BLUE)
    log("=" * 70, Colors.BLUE)
    
    success = update_docs_directory()
    
    if success:
        log("\n💡 İpucu: Güncellenen dokümanları git'e eklemeyi unutma!", Colors.YELLOW)
        log("   git add docs/architecture/", Colors.YELLOW)
    else:
        log("\n❌ Dokümantasyon güncelleme başarısız!", Colors.RED)
