import torch
import torch.nn as nn
import numpy as np

class LSTMPredictor(nn.Module):
    """
    Zaman serisi verilerindeki uzun vadeli bağımlılıkları öğrenerek 
    bir sonraki kapanış fiyatının yönünü veya değerini tahmin eden LSTM ağı.
    """
    def __init__(self, input_size, hidden_size=64, num_layers=2, output_size=3, dropout=0.2):
        super(LSTMPredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        # LSTM Katmanı
        self.lstm = nn.LSTM(
            input_size, 
            hidden_size, 
            num_layers, 
            batch_first=True, 
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Tam Bağlantılı (Fully Connected) Çıktı Katmanı
        # output_size=3 varsayımı: Üçlü Bariyer etiketlerine göre (Long, Short, Bekle/Hold) olasılıklar.
        self.fc = nn.Linear(hidden_size, output_size)
        
    def forward(self, x):
        # x'in beklenen boyutu: (batch_size, sequence_length, features)
        
        # Gizli state'lerin ilklendirilmesi (0 ile)
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
        
        # İleri yayılım
        out, _ = self.lstm(x, (h0, c0))
        
        # Son zaman adımının çıktısını al (Sadece en son tahmin bizim için önemli)
        out = self.fc(out[:, -1, :])
        return out

    def predict_proba(self, x_tensor):
        """Modelin çıktısını softmax'ten geçirerek olasılığa çevirir"""
        self.eval() # Değerlendirme moduna geç (Dropout vb iptal)
        with torch.no_grad():
            outputs = self.forward(x_tensor)
            probabilities = torch.softmax(outputs, dim=1)
        return probabilities.cpu().numpy()
