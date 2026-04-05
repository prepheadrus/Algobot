"""
ML Veri Hazırlama ve Etiketleme Modülü

Bu modül, Marcos Lopez de Prado'nun "Triple Barrier Method" (Üçlü Bariyer Yöntemi)
algoritmasını kullanarak finansal verileri makine öğrenmesi eğitimine hazırlar.

Kaynak: Advances in Financial Machine Learning (2018) - Marcos Lopez de Prado
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from core.logger import logger
from data.features import AdvancedFeatures


def apply_triple_barrier(
    df: pd.DataFrame,
    target_col: str = "close",
    atr_col: Optional[str] = None,
    tp_multiplier: float = 2.0,
    sl_multiplier: float = 2.0,
    time_horizon: int = 10,
    volatility_lookback: int = 14,
) -> pd.DataFrame:
    """
    Triple Barrier Method (Üçlü Bariyer Yöntemi) ile etiketleme yapar.

    Her bir mum için 3 bariyer oluşturur:
    1. Üst Bariyer (Take Profit): Fiyat + (ATR * tp_multiplier)
    2. Alt Bariyer (Stop Loss): Fiyat - (ATR * sl_multiplier)
    3. Dikey Bariyer (Time Horizon): time_horizon mum sonrası

    Fiyatın ilk hangi bariyere çarptığına göre etiket atar:
    - 1: İlk üst bariyere çarptı (LONG başarılı)
    - -1: İlk alt bariyere çarptı (SHORT başarılı / LONG zarar)
    - 0: Dikey bariyere çarptı (Nötr/Yatay)

    Args:
        df: OHLCV verisi (index datetime olmalı)
        target_col: Hedef fiyat kolonu (default: 'close')
        atr_col: ATR kolonu adı (varsa kullanılır, yoksa hesaplanır)
        tp_multiplier: Take Profit çarpanı (ATR bazlı)
        sl_multiplier: Stop Loss çarpanı (ATR bazlı)
        time_horizon: Dikey bariyer için mum sayısı

    Returns:
        pd.DataFrame: Etiketler (target) ve bariyer bilgileri eklenmiş DataFrame
    """
    logger.info(
        f"Triple Barrier etiketleme başlatılıyor: TP={tp_multiplier}, SL={sl_multiplier}, Horizon={time_horizon}"
    )

    df = df.copy()

    # ATR hesapla (eğer yoksa)
    if atr_col is None or atr_col not in df.columns:
        if "ATR_14" in df.columns:
            atr_col = "ATR_14"
        else:
            # Basit ATR hesaplaması (True Range'in hareketli ortalaması)
            high = df["high"]
            low = df["low"]
            close = df["close"]

            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))

            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(volatility_lookback).mean()

            df["_atr_temp"] = atr
            atr_col = "_atr_temp"

    # ATR değerlerini al (NaN'leri doldur)
    atr = df[atr_col].fillna(df[target_col] * 0.02)  # Fallback: %2 volatilite

    # Bariyerleri hesapla
    upper_barrier = df[target_col] + (atr * tp_multiplier)
    lower_barrier = df[target_col] - (atr * sl_multiplier)

    # Etiketleri sakla
    labels = np.zeros(len(df), dtype=int)
    reasons = []  # Hangi bariyere çarptı? (TP, SL, Time)

    # Her satır için ileriye dönük tarama
    for i in range(len(df) - time_horizon):
        entry_price = df[target_col].iloc[i]

        # İleriye dönük fiyatları tara (time_horizon mum)
        end_idx = min(i + time_horizon, len(df) - 1)

        upper_hit = False
        lower_hit = False

        for j in range(i + 1, end_idx + 1):
            high_price = df["high"].iloc[j]
            low_price = df["low"].iloc[j]

            # Üst bariyer kontrolü
            if high_price >= upper_barrier.iloc[i]:
                upper_hit = True
                break

            # Alt bariyer kontrolü
            if low_price <= lower_barrier.iloc[i]:
                lower_hit = True
                break

        # Etiket ata (SİSTEM STANDARDI: 2=LONG, 0=SHORT, 1=HOLD)
        if upper_hit:
            labels[i] = 2  # LONG başarılı (Üst bariyere çarptı)
            reasons.append("TP")
        elif lower_hit:
            labels[i] = 0  # SHORT başarılı (Alt bariyere çarptı)
            reasons.append("SL")
        else:
            # Dikey bariyere çarptı (zaman doldu)
            # Son fiyata göre etiket (yukarı=2, aşağı=0, yatay=1)
            final_price = df[target_col].iloc[end_idx]
            if final_price > entry_price * 1.001:  # %0.1 üstte
                labels[i] = 2  # LONG (yukarı kırık)
                reasons.append("TIME_UP")
            elif final_price < entry_price * 0.999:  # %0.1 altta
                labels[i] = 0  # SHORT (aşağı kırık)
                reasons.append("TIME_DOWN")
            else:
                labels[i] = 1  # NÖTR/HOLD (yatay)
                reasons.append("TIME_NEUTRAL")

    # Son time_horizon satır için etiket yok (ileriye dönük veri yok)
    labels[len(df) - time_horizon :] = 0
    reasons.extend(["NO_DATA"] * time_horizon)

    # Sonuçları DataFrame'e ekle
    df["target"] = labels
    df["barrier_reason"] = reasons
    df["upper_barrier"] = upper_barrier
    df["lower_barrier"] = lower_barrier

    # İstatistikleri logla
    unique, counts = np.unique(labels, return_counts=True)
    label_dist = dict(zip(unique, counts))
    logger.info(f"Etiket dağılımı: {label_dist}")

    # Geçici ATR kolonunu temizle
    if "_atr_temp" in df.columns:
        df.drop(columns=["_atr_temp"], inplace=True)

    return df


def engineer_features(
    df: pd.DataFrame,
    feature_cols: Optional[list] = None,
    scaler_type: str = "standard",
    normalize: bool = True,
) -> Tuple[pd.DataFrame, Optional[object]]:
    """
    Özellik mühendisliği ve ölçeklendirme yapar.

    Mevcut indikatörleri (RSI, MACD, OBV vb.) ML modelinin anlayabileceği
    şekilde normalize eder/ölçeklendirir. Gürültülü, yüksek korelasyonlu
    (Curse of Dimensionality) özellikleri silip, Oransal (Ratio) ve Durağan
    (Stationary) Alpha Faktörleri ekler.

    Args:
        df: Ham veri (indikatörlerle birlikte)
        feature_cols: Kullanılacak özellik kolonları (None ise otomatik seçer)
        scaler_type: Ölçeklendirici tipi ('standard' veya 'minmax')
        normalize: Ölçeklendirme yapılacak mı?

    Returns:
        Tuple[pd.DataFrame, Optional[object]]: (Ölçeklenmiş DataFrame, Scaler objesi)
    """
    df = df.copy()

    # --- 1. YENİ ALPHA FAKTÖRLERİ EKLENMESİ (Durağanlık ve Oransallık) ---
    logger.info("🔧 [ML] Oransal ve durağan Alpha Faktörleri hesaplanıyor...")

    # Fractional Differentiation (d=0.4) - Fiyat hafızasını koruyarak durağanlaştırma
    if "close" in df.columns:
        try:
            df["frac_diff_04"] = AdvancedFeatures.get_fractional_differentiation(
                df["close"], d=0.4
            )
        except Exception as e:
            logger.warning(f"⚠️ Fractional Diff hesaplanamadı: {e}")

    # Kalman Smoothed Returns (Gürültüden arındırılmış getiri - Lookahead bias yok)
    if "smoothed_close" in df.columns:
        # Pct_change default olarak 1 period geriye bakar (sızıntı yok)
        df["kalman_ret"] = df["smoothed_close"].pct_change()
    elif "close" in df.columns:
        # Fallback
        df["kalman_ret"] = df["close"].pct_change()

    # Distance to VWAP Oranı
    if "close" in df.columns and "VWAP" in df.columns:
        # VWAP sıfır olma ihtimaline karşı epsilon koruması
        df["dist_to_vwap"] = (df["close"] - df["VWAP"]) / (df["VWAP"] + 1e-8)

    # Distance to EMA Oranı
    if "close" in df.columns and "EMA_50" in df.columns:
        df["dist_to_ema50"] = (df["close"] - df["EMA_50"]) / (df["EMA_50"] + 1e-8)

    # Bollinger BandWidth (%B)
    if all(col in df.columns for col in ["close", "BBU_20_2.0_2.0", "BBL_20_2.0_2.0"]):
        band_width = df["BBU_20_2.0_2.0"] - df["BBL_20_2.0_2.0"]
        # Bant genişliği sıfır olabileceği durumlar için koruma
        df["bollinger_pct_b"] = (df["close"] - df["BBL_20_2.0_2.0"]) / (
            band_width.replace(0, 1e-8)
        )

    # --- 2. DROP LIST (Çöpe Gidecekler) ---
    # Modelin kafasını karıştıracak, ağaçları statik seviyelere bağlayacak ham fiyatlar silinir.
    drop_list = [
        "open",
        "high",
        "low",
        "close",
        "smoothed_close",
        "SMA_20",
        "EMA_50",
        "MACDs_12_26_9",
        "MACD_12_26_9",  # Sadece MACDh_12_26_9 kalacak
        "STOCH_D_14_3_3",
        "BBU_20_2.0_2.0",
        "BBL_20_2.0_2.0",
        "BBM_20_2.0_2.0",
        "PVI",
        "NVI",
        "VWAP",  # VWAP'ın kendisi de fiyat içerir, biz oranını ('dist_to_vwap') kullanacağız.
    ]

    # --- 3. KEEP LIST (Tutulacaklar - Temel Gücümüz) ---
    # Modelde kalmayı hak edenler
    keep_list = [
        "RSI_14",
        "MACDh_12_26_9",
        "ATR_14",
        "OBV_EMA",
        "ADX_14",
        "KONKORDE_AZUL",
        "KONKORDE_VERDE",
        "KONKORDE_MARRON",
        "SWING_HIGH",
        "SWING_LOW",
        "volatility_ema",
        "BTC_VIX",
        "PVIM",
        "NVIM",
        "STOCH_K_14_3_3",
    ]

    # Yeni eklenen Alpha Faktörleri
    alpha_list = [
        "frac_diff_04",
        "kalman_ret",
        "dist_to_vwap",
        "dist_to_ema50",
        "bollinger_pct_b",
    ]

    # Otomatik özellik kolonları seç (eğer belirtilmemişse)
    if feature_cols is None:
        target_features = keep_list + alpha_list
        # Sadece DataFrame'de var olan ve hesaplanabilen kolonları al
        feature_cols = [col for col in target_features if col in df.columns]

        # Eğer hala boşsa, (fallback durumu) drop_list dışındaki sayısal kolonları al
        if not feature_cols:
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            exclude_cols = [
                "target",
                "barrier_reason",
                "upper_barrier",
                "lower_barrier",
            ] + drop_list
            feature_cols = [col for col in feature_cols if col not in exclude_cols]
    else:
        # Kullanıcı elle liste vermişse bile drop_list'i temizle
        feature_cols = [col for col in feature_cols if col not in drop_list]

    logger.info(
        f"Özellik mühendisliği: {len(feature_cols)} kolon kullanılıyor. (Curse of Dimensionality önlendi)"
    )

    # NaN ve Infinity temizliği (standartımız)
    # Yeni eklenen alpha faktörleri (örn pct_change veya fraksiyonel fark) NaN üretebilir.
    for col in feature_cols:
        if col in df.columns:
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
            df[col] = df[col].fillna(
                0
            )  # XGBoost NaN'leri tolere edebilir ancak scaler için doldurmak güvenlidir.

    # Performans optimizasyonu (Hafıza kullanımı azaltma)
    try:
        from data.data_prep import reduce_mem_usage

        df = reduce_mem_usage(df)
        logger.info("✅ [ML] Memory optimizasyonu uygulandı (reduce_mem_usage).")
    except ImportError:
        logger.debug("reduce_mem_usage fonksiyonu import edilemedi, atlanıyor.")
        pass

    # Drop list'te olan ve veri DataFrame'ine sızan kolonları (orijinal ve kopya olmayan haliyle) tamamen çıkar
    # 'target' vs gibi leakage veya metadata kolonları dışındaki drop_list kolonlarını siliyoruz ki RAM'den de çıksınlar.
    cols_to_drop = [col for col in drop_list if col in df.columns]
    df.drop(columns=cols_to_drop, inplace=True, errors="ignore")

    # Ölçeklendirme
    scaler = None
    if normalize and len(feature_cols) > 0:
        if scaler_type == "standard":
            scaler = StandardScaler()
        elif scaler_type == "minmax":
            scaler = MinMaxScaler(feature_range=(0, 1))
        else:
            raise ValueError(f"Bilinmeyen scaler_type: {scaler_type}")

        # Sadece özellik kolonlarını ölçekle
        df_scaled = df.copy()
        df_scaled[feature_cols] = scaler.fit_transform(df[feature_cols])

        logger.info(f"Ölçeklendirme tamamlandı ({scaler_type})")

        return df_scaled, scaler

    return df, scaler


def create_train_test_split(
    df: pd.DataFrame,
    train_ratio: float = 0.8,
    target_col: str = "target",
    shuffle: bool = False,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Zaman serisi bütünlüğünü koruyarak Train/Test ayrımı yapar.

    Klasik random shuffle KULLANILMAZ (zaman serisi için uygun değil).
    Bunun yerine kronolojik sırayla ilk %80 eğitim, son %20 test olur.

    Args:
        df: Hazırlanmış veri seti
        train_ratio: Eğitim oranı (0-1 arası)
        target_col: Hedef kolon adı
        shuffle: Karıştırma yapılacak mı? (Zaman serisi için False önerilir)
        random_state: Random seed (shuffle=True ise kullanılır)

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: (train_df, test_df)
    """
    logger.info(f"Train/Test split: train_ratio={train_ratio}, shuffle={shuffle}")

    if not 0 < train_ratio < 1:
        raise ValueError(f"train_ratio 0 ile 1 arasında olmalı: {train_ratio}")

    # Zaman serisi için kronolojik split (shuffle=False)
    if not shuffle:
        split_idx = int(len(df) * train_ratio)

        train_df = df.iloc[:split_idx].copy()
        test_df = df.iloc[split_idx:].copy()

        logger.info(
            f"Kronolojik split: Train={len(train_df)} satır, Test={len(test_df)} satır"
        )
    else:
        # Shuffle gerekiyorsa (dikkatli kullanın!)
        train_df, test_df = train_test_split(
            df, train_size=train_ratio, shuffle=shuffle, random_state=random_state
        )
        logger.info(
            f"Random split: Train={len(train_df)} satır, Test={len(test_df)} satır"
        )

    # Etiket dağılımlarını logla
    if target_col in train_df.columns:
        train_dist = train_df[target_col].value_counts().to_dict()
        test_dist = (
            test_df[target_col].value_counts().to_dict()
            if target_col in test_df.columns
            else {}
        )

        logger.info(f"Train etiket dağılımı: {train_dist}")
        logger.info(f"Test etiket dağılımı: {test_dist}")

    return train_df, test_df


def prepare_ml_data(
    df: pd.DataFrame,
    feature_cols: Optional[list] = None,
    target_col: str = "target",
    train_ratio: float = 0.8,
    tp_multiplier: float = 2.0,
    sl_multiplier: float = 2.0,
    time_horizon: int = 10,
    scaler_type: str = "standard",
    normalize: bool = True,
    skip_barrier: bool = False,  # Yeni parametre - apply_triple_barrier atla
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, object]:
    """
    End-to-end ML veri hazırlama pipeline'ı.

    Args:
        df: Ham OHLCV verisi (indikatörlerle birlikte)
        feature_cols: Kullanılacak özellik kolonları
        target_col: Hedef kolon adı
        train_ratio: Eğitim oranı
        tp_multiplier: Take Profit çarpanı
        sl_multiplier: Stop Loss çarpanı
        time_horizon: Dikey bariyer mum sayısı
        scaler_type: Ölçeklendirici tipi
        normalize: Ölçeklendirme yapılacak mı?
        skip_barrier: apply_triple_barrier atla (zaten yapıldıysa)

    Returns:
        Tuple: (X_train, X_test, y_train, y_test, scaler)
    """
    logger.info(f"ML veri hazırlama pipeline'ı başlatılıyor... (Gelen Parametreler: TP={tp_multiplier}, SL={sl_multiplier}, Horizon={time_horizon})")

    # 1. Triple Barrier etiketleme (skip_barrier=False ise)
    if not skip_barrier:
        df_labeled = apply_triple_barrier(
            df=df,
            target_col="close",
            tp_multiplier=tp_multiplier,
            sl_multiplier=sl_multiplier,
            time_horizon=time_horizon,
        )
    else:
        df_labeled = df
        logger.info("⏭️ [ML] Triple Barrier atlandı (zaten yapılmış)")

    # 2. Özellik mühendisliği ve ölçeklendirme
    df_processed, scaler = engineer_features(
        df_labeled,
        feature_cols=feature_cols,
        scaler_type=scaler_type,
        normalize=normalize,
    )

    # 3. Train/Test split
    train_df, test_df = create_train_test_split(
        df_processed,
        train_ratio=train_ratio,
        target_col=target_col,
        shuffle=False,  # Zaman serisi için kronolojik split
    )

    # 4. Özellik ve hedef ayrıştırma - DOĞRU SIRALAMA!
    # ÖNCE y'yi AYIR, SONRA X'ten leakage kolonlarını SİL

    if feature_cols is None:
        # Sadece sayısal kolonları al
        all_numeric_cols = df_processed.select_dtypes(
            include=[np.number]
        ).columns.tolist()

        # X'ten çıkarılacak leakage kolonları (geleceğe dair tüm geçici kolonlar)
        leakage_cols = [
            target_col,  # 'target' - y olarak ayrılacak, X'te olamaz
            "barrier_reason",  # Barrier bilgisi (gelecek)
            "upper_barrier",  # Üst bariyer (gelecek)
            "lower_barrier",  # Alt bariyer (gelecek)
            "future_ret",  # Gelecek getiri (LEAKAGE!)
            "signal",  # Sinyal (gelecek)
            "prediction",  # Tahmin (gelecek)
        ]

        # X için leakage kolonlarını çıkar
        feature_cols = [col for col in all_numeric_cols if col not in leakage_cols]

        logger.info(
            f"🛡️ DATA LEAKAGE ÖNLEME: {len(leakage_cols)} leakage kolonu X'ten çıkarıldı"
        )
        logger.debug(f"   Çıkarılan kolonlar: {leakage_cols}")
        logger.info(f"   X kolonları ({len(feature_cols)}): {feature_cols[:10]}...")

    # ÖNCE y'yi AYIR (target kolonu hala varken)
    y_train = train_df[target_col].copy()
    y_test = test_df[target_col].copy()

    # SONRA X'i oluştur (leakage kolonları olmadan)
    X_train = train_df[feature_cols].copy()
    X_test = test_df[feature_cols].copy()

    # [ML] Dampened Kalman & Triple Barrier Hazır log mesajı
    logger.info("[ML] Dampened Kalman & Triple Barrier Hazır")

    logger.info("ML veri hazırlığı tamamlandı:")
    logger.info(f"  X_train: {X_train.shape}, y_train: {y_train.shape}")
    logger.info(f"  X_test: {X_test.shape}, y_test: {y_test.shape}")
    logger.info(f"  Feature sayısı: {len(feature_cols)}")
    logger.info(f"  X kolonları: {feature_cols[:10]}... (ilk 10)")

    return X_train, X_test, y_train, y_test, scaler


def get_feature_importance_df(
    model, feature_cols: list, top_n: int = 20
) -> pd.DataFrame:
    """
    Model özellik önemlerini DataFrame olarak döner.

    Args:
        model: Eğitilmiş model (feature_importances_ özelliği olmalı)
        feature_cols: Özellik kolonları
        top_n: İlk N özelliği göster

    Returns:
        pd.DataFrame: Özellik önemleri (azalan sırada)
    """
    if not hasattr(model, "feature_importances_"):
        raise ValueError("Model feature_importances_ özelliğine sahip değil")

    importance_df = pd.DataFrame(
        {"feature": feature_cols, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    return importance_df.head(top_n)
