class RiskManagement:
    """
    Sermaye koruma (Risk Management) protokolleri ve matematiksel kaldıraç formüllerini yönetir.
    (Botun yaşam ömrünü uzun kılan hayatta kalma mekanizmasıdır)
    """

    @staticmethod
    def calculate_position_size(account_balance: float, risk_percentage: float, entry_price: float, stop_loss_price: float) -> float:
        """
        Ne kadar kazanıldığına değil ne kadar risk edildiğine odaklanan, raporda geçen formülize edilmiş boyut.
        Formül: Poz_Büyüklüğü = (Bakiye * %Risk) / |GirişFiyatı - StopFiyatı|
        """
        if risk_percentage <= 0.0 or risk_percentage > 5.0:
            raise ValueError("Kabul edilemez risk limiti. Yüksek WIN Rate sistemlerde risk %1-%2 arası olmalıdır.")
            
        # İşlem başına alınacak risk edilen kesin Dolar/Kripto miktarı
        risk_amount = account_balance * (risk_percentage / 100.0)
        
        # Giriş seviyesi ile stop loss limiti arasındaki salt parasal mesafe
        price_distance = abs(entry_price - stop_loss_price)
        
        if price_distance == 0:
             return 0.0 # Hatalı emir girişi
             
        # Kaldıraçtan bağımsız net kontrat/birim hacmi
        position_size = risk_amount / price_distance
        
        # Genellikle çok küçük pozisyonlar (dust) borsalarda min-order-size vb hatasına takılabilir, kontrolü exchange class'ında yapılacaktır.
        return position_size

    @staticmethod
    def calculate_dynamic_leverage(confidence_score: float, base_leverage: int = 1, max_leverage: int = 10) -> int:
        """
        Güven skoruna göre dinamik kaldıraç.
        """
        if confidence_score < 0.50:
            return base_leverage
            
        ratio = (confidence_score - 0.50) / 0.50
        calculated = base_leverage + (ratio * (max_leverage - base_leverage))
        
        return min(max_leverage, max(base_leverage, int(round(calculated))))

    @staticmethod
    def calculate_dynamic_stops(price: float, direction: str, atr: float, multiplier: float = 3.0):
        """
        ATR (Average True Range) tabanlı dinamik Stop Loss ve Take Profit seviyeleri hesaplar.
        Oynaklık arttıkça stop mesafesi açılır, sakin piyasada daralır.

        Args:
            price: Mevcut fiyat
            direction: LONG veya SHORT
            atr: Average True Range değeri
            multiplier: ATR çarpanı (varsayılan 3.0 - daha geniş stop için)

        Returns:
            (stop_loss, take_profit) tuple
        """
        # Standart Sapma x Oynaklık (Volatilite) çarpanı
        # multiplier=3.0 ile %0.5-1.5 arası stop mesafesi (sembol volatilitesine göre)
        stop_distance = atr * multiplier

        if direction == "LONG":
            sl = price - stop_distance
            tp = price + (stop_distance * 2.0) # 1:2 Risk/Ödül Oranı
        else: # SHORT
            sl = price + stop_distance
            tp = price - (stop_distance * 2.0)

        return sl, tp
