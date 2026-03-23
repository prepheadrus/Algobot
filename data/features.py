import pandas as pd
import numpy as np

class AdvancedFeatures:
    """Makine öğrenimi için ileri düzey özellik (feature) çıkartma metotlarını barındırır."""

    @staticmethod
    def get_volatility(close_prices: pd.Series, span: int = 100) -> pd.Series:
        """Belirtilen periyot için üstel ağırlıklı (EWMA) günlük volatiliteyi hesaplar."""
        # Getiriler (Returns)
        returns = close_prices.pct_change()
        # İstenen pencere boyutu için standart sapma (volatilite x günlük veya periyotluk)
        return returns.ewm(span=span).std()

    @staticmethod
    def get_triple_barrier_labels(
            prices: pd.Series, 
            events: pd.DataFrame, 
            pt_sl: list, 
            out: pd.Series) -> pd.DataFrame:
        """
        Marcos Lopez de Prado'nun 'Üçlü Bariyer' Yöntemi
        (Triple Barrier Method)

        events: Hedef işlem noktalarının indeksini içeren DataFrame (örn: t1, hedef zaman aşımı)
        pt_sl: [kar-al (profit-take), zarar-kes (stop-loss)] çarpanları listesi (Örn: [1, 1], [2, 1])
        out: Hedef getiri veya volatilitenin tutulduğu seri (Bariyer genişliğini belirler)
        """
        # (Bu fonksiyonun içi, raporda bahsedilen ve kitaplarda standart olan algoritmanın 
        # asenkron/vektörel bir özet simülasyonudur. İlerleyen aşamada ML modeli buraya bağlanır)
        
        events_out = events.copy(deep=True)
        
        # Kar/Zarar Limitlerinin Saptanması
        if pt_sl[0] > 0:
            pt = pt_sl[0] * out
        else:
            pt = pd.Series(index=events.index) # NaN

        if pt_sl[1] > 0:
            sl = -pt_sl[1] * out
        else:
            sl = pd.Series(index=events.index) # NaN

        labels = pd.DataFrame(index=events.index, columns=['take_profit', 'stop_loss', 'time_limit', 'label'])
        
        # (Burada her bir giriş noktası için fiyatın hangi bariyere -PT, SL, Zaman- 
        # önce çarptığını vektörel veya döngüsel hesaplayacak altyapı ML eğitim aşamasında kodlanacaktır.)
        
        return labels

    @staticmethod
    def get_fractional_differentiation(series: pd.Series, d: float, thres: float = 0.01) -> pd.Series:
        """
        Kesirli Fark Alma (Fractional Differentiation)
        Durağanlık (Stationarity) elde edip geçmiş finansal hafızayı korumayı sağlar.
        `d`: Kesir derecesi (örn 0.4, 0.5 vb.)
        """
        # Katsayıların (Weights) oluşturulması
        w = [1.0]
        k = 1
        while True:
            w_k = -w[-1] / k * (d - k + 1)
            if abs(w_k) < thres:
                break
            w.append(w_k)
            k += 1
            
        w = np.array(w[::-1]).reshape(-1, 1)
        
        # Orijinal zaman serisi verisi üzerinde kayan pencerelerle çarpım işlemi
        # (Optimizasyon ML aşamasına bırakılacak şekilde hazır tutulmaktadır)
        # Bu işlem zaman serisi analiz modülünde Pandas kullanılarak tamamlanır.
        
        return series # Şimdilik yer tutucu, Model eğitiminde gerçek işlem entegre edilecek.

    @staticmethod
    def create_target_labels(df: pd.DataFrame, lookahead: int = 5, threshold: float = 0.002) -> pd.Series:
        """
        Supersived Learning (Gözetimli Öğrenme) için gelecekteki `lookahead` mumu sonrasındaki 
        fiyat artış/azalış yüzdesine bakıp hedef etiketi atar.
        2: Yükseliş (LONG Uygundu)
        0: Düşüş (SHORT Uygundu)
        1: Yatay/Belirsiz (HOLD)
        """
        # Gelecekteki fiyata göre getiri yüzdesini bul
        future_return = (df['close'].shift(-lookahead) / df['close']) - 1.0
        
        # Etiketleme koşulları
        conditions = [
            (future_return >= threshold),   # Fiyat belirtilen eşiğin üstüne çıktı (Örn: +%0.2)
            (future_return <= -threshold)   # Fiyat belirtilen eşiğin altına indi (Örn: -%0.2)
        ]
        
        # Karşılık Gelen Kararlar (2=LONG, 0=SHORT)
        choices = [2, 0]
        
        # Koşullara uymayan her şeye 1 (Bekle) de
        labels = np.select(conditions, choices, default=1)
        return pd.Series(labels, index=df.index)
