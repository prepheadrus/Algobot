import numpy as np

class CombinatorialFusion:
    """
    Farklı makine öğrenimi modellerinin (örn: LSTM ve XGBoost) çıktılarını birleştiren 
    Kombinatoryal Füzyon Analizi (CFA - Combinatorial Fusion Analysis) Mekanizması.
    """
    
    @staticmethod
    def fuse_probabilities(prob_list: list, weights: list = None) -> np.ndarray:
        """
        Gelen modellerden gelen [ [P(Low), P(Hold), P(High)], [P(Low), P(Hold), P(High)] ] 
        olasılık listelerini ağırlıklı ortalamayla birleştirerek en sağlıklı "Konfluans" kararına dönüştürür.
        """
        if not prob_list:
            raise ValueError("Füzyon için probability(olasılık) listesi boş olamaz.")
            
        # Eğer özel ağırlık belirtilmemişse modellere eşit güvenilirlik (ağırlık) ata
        num_models = len(prob_list)
        if weights is None:
            weights = [1.0 / num_models] * num_models
            
        # Listeleri numpy maskesine çevir ve ağırlıklarla çarp
        fused_probs = np.zeros_like(prob_list[0])
        for prob, w in zip(prob_list, weights):
            fused_probs += prob * w
            
        return fused_probs

    @staticmethod
    def get_signal_from_fused(fused_probs: np.ndarray, threshold: float = 0.65) -> int:
        """
        Nihai füzyon edilmiş olasılık matrisinden kesin bir al-sat sinyali üretir.
        Dönüş Modeli varsayımı: 0 = Short, 1 = Hold/Bekle, 2 = Long
        
        Sinyal sadece, en güçlü olasılık `threshold` değerini (örn. %65 güveni) aşarsa üretilir.
        Aksi takdirde risk almayıp Hold (1) üretir.
        """
        max_idx = np.argmax(fused_probs)
        max_prob = np.max(fused_probs)
        
        # Sadece belirlenen "confidence" güven sınırını aşarsa işlemi onayla
        if max_prob >= threshold:
            return max_idx
        
        # Sınır aşılmadıysa belirsizlik var demektir, flat kal.
        return 1
