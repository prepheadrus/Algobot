"""Test strategy auto-discovery"""
from strategy.manager import StrategyManager

print("🔍 Stratejiler yükleniyor...")
strategies = StrategyManager.get_all_strategies()

print(f"\n✅ Toplam {len(strategies)} strateji bulundu:\n")

for strategy_id, data in strategies.items():
    strategy_type = data.get('type', 'unknown')
    type_icon = "📦" if strategy_type == 'builtin' else "🎨" if strategy_type == 'custom' else "📝"
    print(f"  {type_icon} {strategy_id}: {data['name']} ({strategy_type})")

# Smart Money kontrol
if 'custom_smartmoney' in strategies:
    print("\n✅ Smart Money stratejisi OTOMATİK BULUNDU!")
    print(f"   Ad: {strategies['custom_smartmoney']['name']}")
    print(f"   Açıklama: {strategies['custom_smartmoney']['description']}")
    print(f"   Timeframe: {strategies['custom_smartmoney']['timeframe']}")
else:
    print("\n❌ Smart Money stratejisi bulunamadı!")
    print("   Aranan ID'ler:", [k for k in strategies.keys() if 'smart' in k.lower()])
