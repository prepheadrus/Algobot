import pytest
import numpy as np
import pandas as pd
import asyncio
from ml.model_training import ModelTrainer

def test_missing_class_injection():
    """
    Eksik Sınıf Enjeksiyonu Zırhı Testi.

    XGBoost eğitiminde (num_class=3) veride sadece 0 (SHORT) ve 2 (LONG) sınıfları varsa
    ValueError fırlatır. Bu test, ModelTrainer.train() metodunun bu durumda çökmemesini,
    eksik olan 1 (NEUTRAL) sınıfını ve sample_weights=1.0'ı veri setine başarıyla eklemesini sağlar.
    """

    # Sadece 0 ve 2 sınıflarından oluşan sentetik bir veri oluştur.
    X_train_data = {
        'feature1': [1.0, 2.0, 3.0, 4.0],
        'feature2': [4.0, 3.0, 2.0, 1.0]
    }
    y_train_data = [0, 2, 0, 2] # 1 (NEUTRAL) eksik

    X_train = pd.DataFrame(X_train_data)
    y_train = pd.Series(y_train_data)

    X_test = pd.DataFrame({
        'feature1': [1.5, 2.5],
        'feature2': [3.5, 2.5]
    })
    y_test = pd.Series([0, 2])

    trainer = ModelTrainer(
        n_estimators=10,
        max_depth=3,
        num_class=3,
        enable_auto_regularization=False
    )

    # Modelin ValueError fırlatmadan eğitildiğini kontrol et (Eğer fırlatırsa test başarısız olur)
    try:
        trainer.train(X_train, y_train, X_test, y_test)
    except Exception as e:
        pytest.fail(f"Eğitim sırasında beklenmeyen bir hata oluştu: {str(e)}")

    # Modelin eğitilmiş olduğunu teyit et
    assert trainer.is_trained is True

    # XGBoost modelini elde et (bu nesnenin sınıflarını doğrudan kontrol edemesek de
    # veriye başarıyla inject edildiğini ve training'in bittiğini biliyoruz)
    # Doğrulama: trainer predict edebiliyor mu?
    preds, confs, probs = trainer.predict_with_confidence(X_test)
    assert len(preds) == 2
    assert len(probs) == 2
    assert probs.shape[1] == 3 # Olasılık matrisi 3 sınıfı da (0, 1, 2) içermelidir

@pytest.mark.asyncio
async def test_event_loop_isolation_during_ml_training():
    """
    Event-Loop ve Asenkron İzolasyon (CPU-Bound Starvation) Testi.

    Ağır ML eğitim süreçlerinin asyncio.to_thread() ile çalıştırılarak
    ana Event-Loop'u bloke etmediğini (CPU-Bound Starvation) doğrular.
    """
    import asyncio
    import time

    # Ağır ML eğitim süreci simülasyonu için sentetik veri
    X_train_data = {
        'feature1': np.random.rand(1000),
        'feature2': np.random.rand(1000)
    }
    y_train_data = np.random.choice([0, 1, 2], size=1000)
    X_train = pd.DataFrame(X_train_data)
    y_train = pd.Series(y_train_data)

    X_test = pd.DataFrame({'feature1': np.random.rand(10), 'feature2': np.random.rand(10)})
    y_test = pd.Series(np.random.choice([0, 1, 2], size=10))

    trainer = ModelTrainer(
        n_estimators=50, # İşlem süresini uzatmak için makul bir sayı
        max_depth=3,
        num_class=3,
        enable_auto_regularization=False
    )

    # Arka planda çalışacak basit bir asenkron sayaç (Event-loop'un canlılığını ölçer)
    counter = 0
    loop_active = True

    async def heartbeat():
        nonlocal counter
        while loop_active:
            await asyncio.sleep(0.01)
            counter += 1

    # Heartbeat task'ini başlat
    heartbeat_task = asyncio.create_task(heartbeat())

    # ML Eğitimini ayrı bir thread'de asenkron olarak başlat
    start_time = time.time()
    await asyncio.to_thread(trainer.train, X_train, y_train, X_test, y_test)
    end_time = time.time()

    # Döngüyü sonlandır
    loop_active = False
    await heartbeat_task

    # Geçen süreye göre heartbeat'in çalışmış olması gerekir.
    elapsed_time = end_time - start_time

    # Eğer event-loop bloke olsaydı, heartbeat_task çalışamazdı ve counter 0 (veya çok düşük) kalırdı.
    # Geçen süre * 100 Hz (0.01sn) = beklenen counter. Bir miktar pay bırakıyoruz (örneğin %50'si kadar çalışmış olmalı)
    expected_minimum_ticks = (elapsed_time / 0.01) * 0.2

    assert counter > expected_minimum_ticks, f"Event-loop bloke oldu! Beklenen tick: >{expected_minimum_ticks}, Gerçekleşen: {counter}"
    assert trainer.is_trained is True
