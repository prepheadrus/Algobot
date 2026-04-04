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
        prices: pd.Series, events: pd.DataFrame, pt_sl: list, out: pd.Series
    ) -> pd.DataFrame:
        """
        Marcos Lopez de Prado'nun 'Üçlü Bariyer' Yöntemi
        (Triple Barrier Method)

        events: Hedef işlem noktalarının indeksini içeren DataFrame (örn: t1, hedef zaman aşımı)
        pt_sl: [kar-al (profit-take), zarar-kes (stop-loss)] çarpanları listesi (Örn: [1, 1], [2, 1])
        out: Hedef getiri veya volatilitenin tutulduğu seri (Bariyer genişliğini belirler)
        """
        # (Bu fonksiyonun içi, raporda bahsedilen ve kitaplarda standart olan algoritmanın
        # asenkron/vektörel bir özet simülasyonudur. İlerleyen aşamada ML modeli buraya bağlanır)

        # Kar/Zarar Limitlerinin Saptanması (Şimdilik pasif)
        pass
        
        labels = pd.DataFrame(
            index=events.index,
            columns=["take_profit", "stop_loss", "time_limit", "label"],
        )

        # (Burada her bir giriş noktası için fiyatın hangi bariyere -PT, SL, Zaman-
        # önce çarptığını vektörel veya döngüsel hesaplayacak altyapı ML eğitim aşamasında kodlanacaktır.)

        return labels

    @staticmethod
    def get_fractional_differentiation(
        series: pd.Series, d: float, thres: float = 0.01
    ) -> pd.Series:
        """
        Kesirli Fark Alma (Fractional Differentiation)
        Durağanlık (Stationarity) elde edip geçmiş finansal hafızayı korumayı sağlar.
        Marcos Lopez de Prado'nun yönteminin optimize edilmiş Pandas vektörel uyarlaması.

        Args:
            series: İşlem görecek fiyat serisi (örn: close)
            d: Kesir derecesi (genellikle 0.3 ile 0.7 arası)
            thres: Ağırlık kesme eşiği (Hafızanın ne kadar geriye gideceğini belirler)

        Returns:
            pd.Series: Fraksiyonel olarak farkı alınmış, durağanlaştırılmış seri
        """
        # 1. Katsayıların (Weights) oluşturulması
        w = [1.0]
        k = 1
        while True:
            w_k = -w[-1] / k * (d - k + 1)
            if abs(w_k) < thres:
                break
            w.append(w_k)
            k += 1

        w = np.array(w[::-1]).reshape(-1, 1)
        lookback = len(w)

        # 2. DataFrame üzerinden Rolling Window işlemi
        # Hızlı işlem için numpy dizisine çeviriyoruz
        series_np = series.values
        n = len(series_np)

        result = np.full(n, np.nan)

        # Yeterli veri olmayan ilk lookback kısımlarını atlıyoruz
        for i in range(lookback - 1, n):
            window = series_np[i - lookback + 1 : i + 1].reshape(-1, 1)
            result[i] = np.dot(w.T, window)[0, 0]

        return pd.Series(
            result, index=series.index, name=f'frac_diff_{str(d).replace(".", "")}'
        )

    @staticmethod
    def create_target_labels(
        df: pd.DataFrame, lookahead: int = 5, threshold: float = 0.002
    ) -> pd.Series:
        """
        Supersived Learning (Gözetimli Öğrenme) için gelecekteki `lookahead` mumu sonrasındaki
        fiyat artış/azalış yüzdesine bakıp hedef etiketi atar.
        2: Yükseliş (LONG Uygundu)
        0: Düşüş (SHORT Uygundu)
        1: Yatay/Belirsiz (HOLD)
        """
        # Gelecekteki fiyata göre getiri yüzdesini bul
        future_return = (df["close"].shift(-lookahead) / df["close"]) - 1.0

        # Etiketleme koşulları
        conditions = [
            (
                future_return >= threshold
            ),  # Fiyat belirtilen eşiğin üstüne çıktı (Örn: +%0.2)
            (
                future_return <= -threshold
            ),  # Fiyat belirtilen eşiğin altına indi (Örn: -%0.2)
        ]

        # Karşılık Gelen Kararlar (2=LONG, 0=SHORT)
        choices = [2, 0]

        # Koşullara uymayan her şeye 1 (Bekle) de
        labels = np.select(conditions, choices, default=1)
        return pd.Series(labels, index=df.index)
