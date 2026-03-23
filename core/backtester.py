"""
Backtester - Gelişmiş Backtest (Geriye Dönük Test) Motoru

Kullanıcıların oluşturduğu JSON stratejilerini geçmiş verilerde test eder.
Win-Rate, Max Drawdown, Net PnL gibi metrikleri hesaplar.

Örnek Kullanım:
    backtester = VectorizedBacktester(initial_balance=10000)
    results = backtester.run_backtest(df, signals, risk_params)
    print(f"Win Rate: {results['win_rate']}%")
    print(f"Net PnL: ${results['net_pnl']}")
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import logging

# Logger setup (core.logger alternatifi)
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@dataclass
class Trade:
    """
    Tek bir backtest işlemini temsil eder.
    
    Attributes:
        entry_time: İşlem açılış zamanı
        exit_time: İşlem kapanış zamanı
        entry_price: Giriş fiyatı
        exit_price: Çıkış fiyatı
        direction: İşlem yönü ('LONG' veya 'SHORT')
        size: Pozisyon büyüklüğü
        pnl: Kar/Zarar miktarı ($)
        pnl_percent: Kar/Zarar yüzdesi (%)
        exit_reason: Çıkış nedeni (STOP, TARGET, SIGNAL)
    """
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    direction: str
    size: float
    pnl: float = 0.0
    pnl_percent: float = 0.0
    exit_reason: str = 'SIGNAL'


@dataclass
class BacktestResult:
    """
    Backtest sonuçlarını temsil eder.
    
    Attributes:
        total_trades: Toplam işlem sayısı
        winning_trades: Kazanan işlem sayısı
        losing_trades: Kaybeden işlem sayısı
        win_rate: Kazanma oranı (%)
        net_pnl: Net kar/zarar ($)
        net_pnl_percent: Net kar/zarar yüzdesi (%)
        max_drawdown: Maksimum düşüş (%)
        avg_trade_pnl: Ortalama işlem PnL ($)
        avg_win: Ortalama kazanç ($)
        avg_loss: Ortalama kayıp ($)
        profit_factor: Kar faktörü (Brüt Kar / Brüt Kayıp)
        trades: Tüm işlemlerin listesi
    """
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    net_pnl: float = 0.0
    net_pnl_percent: float = 0.0
    max_drawdown: float = 0.0
    avg_trade_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    trades: List[Trade] = field(default_factory=list)


class VectorizedBacktester:
    """
    Vektörize Backtest Motoru
    
    Geçmiş veriler üzerinde strateji testleri yapar.
    PaperTrader mantığıyla uyumlu (komisyon, slipaj, risk yönetimi).
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        fee_rate: float = 0.0004,
        slippage: float = 1.0001,
        risk_per_trade: float = 0.01  # %1 risk
    ):
        """
        Backtester'ı başlat.
        
        Args:
            initial_balance: Başlangıç bakiyesi ($)
            fee_rate: Komisyon oranı (0.0004 = %0.04)
            slippage: Kayma oranı (1.0001 = %0.01)
            risk_per_trade: İşlem başına risk (%1 = 0.01)
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.fee_rate = fee_rate
        self.slippage = slippage
        self.risk_per_trade = risk_per_trade
        
        # Sonuçlar
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        
        logger.info(f"📊 Backtester başlatıldı: Başlangıç=${initial_balance:,.2f}")


    def run_backtest(
        self,
        df: pd.DataFrame,
        signals: pd.Series,
        risk_params: Optional[Dict[str, float]] = None
    ) -> BacktestResult:
        """
        Backtest simülasyonunu çalıştır.
        
        Args:
            df: OHLCV verisi içeren DataFrame
            signals: Sinyal serisi (0=SAT, 1=BEKLE, 2=AL)
            risk_params: Risk parametreleri (stop_loss_atr, take_profit_atr, vb.)
            
        Returns:
            BacktestResult: Backtest sonuçları
        """
        # Varsayılan risk parametreleri
        if risk_params is None:
            risk_params = {
                'stop_loss_atr_multiplier': 2.0,
                'take_profit_atr_multiplier': 4.0,
                'max_risk_percent': 1.0
            }
        
        # DataFrame kontrolü
        if df.empty:
            logger.error("❌ DataFrame boş!")
            return BacktestResult()
        
        if len(signals) != len(df):
            logger.error(f"❌ Sinyal uzunluğu uyuşmuyor: {len(signals)} vs {len(df)}")
            return BacktestResult()
        
        logger.info(f"📊 Backtest başlatıldı: {len(df)} mum, {signals.sum()} sinyal")
        
        # Pozisyon takibi
        in_position = False
        current_trade: Optional[Trade] = None
        peak_equity = self.initial_balance
        max_drawdown = 0.0
        
        # ATR hesaplama (stop loss için)
        if 'ATR_14' in df.columns:
            atr = df['ATR_14']
        else:
            # Basit ATR simülasyonu (fiyatın %2'si)
            atr = df['close'] * 0.02
        
        # Her mum için iterasyon
        for i in range(len(df)):
            timestamp = df.index[i] if hasattr(df.index, '__getitem__') else pd.Timestamp.now()
            row = df.iloc[i]
            signal = signals.iloc[i] if hasattr(signals, 'iloc') else signals[i]
            
            current_price = row['close']
            current_atr = atr.iloc[i] if hasattr(atr, 'iloc') else atr[i]
            
            # Stop loss ve take profit seviyeleri
            stop_loss_pct = risk_params.get('stop_loss_atr_multiplier', 2.0)
            take_profit_pct = risk_params.get('take_profit_atr_multiplier', 4.0)
            
            # Pozisyon boyutu (%1 risk)
            position_size = (self.balance * self.risk_per_trade) / (current_price * stop_loss_pct * 0.01)
            
            # Pozisyon açma (AL sinyali)
            if signal == 2 and not in_position:  # AL
                # Slipaj ve komisyon
                entry_price = current_price * self.slippage  # Biraz pahalıdan al
                entry_fee = position_size * entry_price * self.fee_rate
                
                # Stop loss ve take profit
                stop_loss = entry_price * (1 - stop_loss_pct * 0.01)
                take_profit = entry_price * (1 + take_profit_pct * 0.01)
                
                # Pozisyon aç
                in_position = True
                current_trade = Trade(
                    entry_time=timestamp,
                    exit_time=pd.NaT,
                    entry_price=entry_price,
                    exit_price=0.0,
                    direction='LONG',
                    size=position_size,
                    exit_reason='SIGNAL'
                )
                
                # Bilgileri sakla
                current_trade.stop_loss = stop_loss
                current_trade.take_profit = take_profit
                current_trade.entry_fee = entry_fee
                
                logger.debug(f"🟢 LONG açıldı: {entry_price:.2f} @ {timestamp}")
            
            # Pozisyon kapatma (SAT sinyali veya stop/target)
            elif in_position and current_trade:
                should_close = False
                exit_reason = 'SIGNAL'
                
                # SAT sinyali
                if signal == 0:
                    should_close = True
                    exit_reason = 'SIGNAL'
                
                # Stop loss
                elif current_price <= current_trade.stop_loss:
                    should_close = True
                    exit_reason = 'STOP'
                
                # Take profit
                elif current_price >= current_trade.take_profit:
                    should_close = True
                    exit_reason = 'TARGET'
                
                # Pozisyonu kapat
                if should_close:
                    # Slipaj ve komisyon
                    exit_price = current_price / self.slippage  # Biraz ucuza sat
                    exit_fee = position_size * exit_price * self.fee_rate
                    
                    # PnL hesaplama
                    gross_pnl = (exit_price - current_trade.entry_price) * position_size
                    net_pnl = gross_pnl - current_trade.entry_fee - exit_fee
                    pnl_percent = (net_pnl / (position_size * current_trade.entry_price)) * 100
                    
                    # Trade'i kaydet
                    current_trade.exit_time = timestamp
                    current_trade.exit_price = exit_price
                    current_trade.pnl = net_pnl
                    current_trade.pnl_percent = pnl_percent
                    current_trade.exit_fee = exit_fee
                    current_trade.exit_reason = exit_reason
                    
                    self.trades.append(current_trade)
                    
                    # Bakiye güncelle
                    self.balance += net_pnl
                    
                    # Equity curve
                    self.equity_curve.append(self.balance)
                    
                    # Peak ve drawdown
                    if self.balance > peak_equity:
                        peak_equity = self.balance
                    
                    drawdown = ((peak_equity - self.balance) / peak_equity) * 100
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                    
                    logger.debug(f"🔴 LONG kapatıldı: {exit_price:.2f} @ {timestamp} | PnL: ${net_pnl:.2f} ({exit_reason})")
                    
                    # Pozisyon kapatıldı
                    in_position = False
                    current_trade = None
            
            # Equity curve (pozisyonda değilsek de kaydet)
            if not in_position:
                self.equity_curve.append(self.balance)
        
        # Sonuçları hesapla
        result = self._calculate_metrics(max_drawdown)
        
        logger.info(f"✅ Backtest tamamlandı: {result.total_trades} işlem, Win Rate: {result.win_rate:.2f}%, Net PnL: ${result.net_pnl:.2f}")
        
        return result


    def _calculate_metrics(self, max_drawdown: float) -> BacktestResult:
        """
        Backtest metriklerini hesapla.
        
        Args:
            max_drawdown: Maksimum düşüş (%)
            
        Returns:
            BacktestResult: Hesaplanmış metrikler
        """
        if not self.trades:
            return BacktestResult()
        
        # Kazanan ve kaybeden işlemler
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        # Toplam PnL
        net_pnl = sum(t.pnl for t in self.trades)
        net_pnl_percent = ((self.balance - self.initial_balance) / self.initial_balance) * 100
        
        # Ortalamalar
        avg_trade_pnl = net_pnl / len(self.trades) if self.trades else 0.0
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        
        # Profit Factor (Brüt Kar / Brüt Kayıp)
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        return BacktestResult(
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=(len(winning_trades) / len(self.trades)) * 100 if self.trades else 0.0,
            net_pnl=net_pnl,
            net_pnl_percent=net_pnl_percent,
            max_drawdown=max_drawdown,
            avg_trade_pnl=avg_trade_pnl,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=self.trades
        )


    def reset(self):
        """
        Backtester'ı sıfırla (yeni test için).
        """
        self.balance = self.initial_balance
        self.trades = []
        self.equity_curve = []
        logger.info("🔄 Backtester sıfırlandı")


    def get_trade_history(self) -> pd.DataFrame:
        """
        İşlem geçmişini DataFrame olarak döndür.
        
        Returns:
            pd.DataFrame: Tüm işlemler
        """
        if not self.trades:
            return pd.DataFrame()
        
        trades_data = []
        for trade in self.trades:
            trades_data.append({
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'direction': trade.direction,
                'size': trade.size,
                'pnl': trade.pnl,
                'pnl_percent': trade.pnl_percent,
                'exit_reason': trade.exit_reason
            })
        
        return pd.DataFrame(trades_data)


    def get_equity_curve(self) -> pd.Series:
        """
        Equity eğrisini döndür.
        
        Returns:
            pd.Series: Equity eğrisi
        """
        return pd.Series(self.equity_curve)


# ============================================================================
# ÖRNEK KULLANIM VE TEST
# ============================================================================

if __name__ == "__main__":
    # Test DataFrame oluştur
    print("[TEST] Test DataFrame oluşturuluyor...")
    np.random.seed(42)
    n_rows = 1000
    
    # Random walk fiyat simülasyonu
    close_prices = 50000 + np.cumsum(np.random.randn(n_rows) * 100)
    high_prices = close_prices + np.abs(np.random.randn(n_rows)) * 50
    low_prices = close_prices - np.abs(np.random.randn(n_rows)) * 50
    open_prices = close_prices + np.random.randn(n_rows) * 50
    volumes = np.random.randint(100, 10000, n_rows)
    
    # ATR ekle (basit)
    atr = close_prices * 0.02
    
    test_df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes,
        'ATR_14': atr
    }, index=pd.date_range('2024-01-01', periods=n_rows, freq='1h'))
    
    # Test sinyalleri (rastgele AL/SAT)
    test_signals = pd.Series([0] * n_rows)
    test_signals.iloc[::50] = 2  # Her 50 mumda bir AL
    test_signals.iloc[51::50] = 0  # Bir sonraki mumda SAT
    
    print(f"[OK] Test DataFrame: {len(test_df)} satır")
    print(f"     Sinyaller: {test_signals.sum()} AL")
    
    # Backtester'ı başlat
    print("\n[TEST] Backtester başlatılıyor...")
    backtester = VectorizedBacktester(
        initial_balance=10000,
        fee_rate=0.0004,
        slippage=1.0001,
        risk_per_trade=0.01
    )
    
    # Backtest çalıştır
    print("\n[TEST] Backtest çalıştırılıyor...")
    risk_params = {
        'stop_loss_atr_multiplier': 2.0,
        'take_profit_atr_multiplier': 4.0,
        'max_risk_percent': 1.0
    }
    
    result = backtester.run_backtest(test_df, test_signals, risk_params)
    
    # Sonuçları göster
    print("\n" + "="*60)
    print("[OK] BACKTEST SONUÇLARI")
    print("="*60)
    print(f"Toplam İşlem:        {result.total_trades}")
    print(f"Kazanan İşlem:       {result.winning_trades}")
    print(f"Kaybeden İşlem:      {result.losing_trades}")
    print(f"Win Rate:            {result.win_rate:.2f}%")
    print(f"Net PnL:             ${result.net_pnl:.2f}")
    print(f"Net PnL %:           {result.net_pnl_percent:.2f}%")
    print(f"Max Drawdown:        {result.max_drawdown:.2f}%")
    print(f"Avg Trade PnL:       ${result.avg_trade_pnl:.2f}")
    print(f"Avg Win:             ${result.avg_win:.2f}")
    print(f"Avg Loss:            ${result.avg_loss:.2f}")
    print(f"Profit Factor:       {result.profit_factor:.2f}")
    print("="*60)
    
    # İşlem geçmişini göster
    if result.trades:
        print(f"\n[OK] İlk 5 işlem:")
        for i, trade in enumerate(result.trades[:5]):
            print(f"  {i+1}. {trade.direction} | Entry: ${trade.entry_price:.2f} | Exit: ${trade.exit_price:.2f} | PnL: ${trade.pnl:.2f} ({trade.exit_reason})")
    
    print("\n" + "="*60)
    print("[OK] TÜM TESTLER BAŞARILI!")
    print("="*60)
