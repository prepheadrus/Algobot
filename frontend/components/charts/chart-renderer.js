/**
 * Chart Renderer Component
 * 
 * TradingView Lightweight Charts wrapper.
 * Tüm grafik çizim işlemleri bu modülde izole edilmiştir.
 * 
 * Usage:
 *   import chartRenderer from '../components/charts/chart-renderer.js';
 *   
 *   // Initialize chart
 *   chartRenderer.init('chart-container');
 *   
 *   // Update data
 *   chartRenderer.updateCandles(candles);
 *   chartRenderer.updateMarkers(markers);
 */

class ChartRenderer {
    constructor() {
        this.chart = null;
        this.candleSeries = null;
        this.volumeSeries = null;
        this.containerId = null;
        
        console.log('📊 [CHART] Renderer initialized');
    }
    
    /**
     * Initialize chart
     * @param {string} containerId - DOM container ID
     * @param {Object} options - Chart options
     */
    init(containerId, options = {}) {
        this.containerId = containerId;
        
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`❌ [CHART] Container not found: ${containerId}`);
            return;
        }
        
        const defaultOptions = {
            width: container.clientWidth,
            height: 600,
            layout: {
                backgroundColor: '#0a0e1a',
                textColor: '#d1d4dc'
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' }
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal
            },
            timeScale: {
                borderColor: 'rgba(197, 203, 206, 0.8)',
                timeVisible: true,
                secondsVisible: false
            }
        };
        
        // Create chart
        this.chart = LightweightCharts.createChart(container, { ...defaultOptions, ...options });
        
        // Add candlestick series
        this.candleSeries = this.chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350'
        });
        
        // Add volume series
        this.volumeSeries = this.chart.addHistogramSeries({
            color: '#26a69a',
            priceFormat: { type: 'volume' },
            priceScaleId: '',
            scaleMargins: { top: 0.85, bottom: 0 }
        });
        
        // Handle resize
        window.addEventListener('resize', () => {
            this.chart.applyOptions({
                width: container.clientWidth
            });
        });
        
        console.log(`✅ [CHART] Initialized on #${containerId}`);
    }
    
    /**
     * Update candle data
     * @param {Array} candles - OHLCV candles
     */
    updateCandles(candles) {
        if (!this.candleSeries) {
            console.error('❌ [CHART] Chart not initialized');
            return;
        }
        
        const formattedCandles = candles.map(c => ({
            time: c[0] / 1000, // Convert ms to seconds
            open: c[1],
            high: c[2],
            low: c[3],
            close: c[4]
        }));
        
        this.candleSeries.setData(formattedCandles);
        console.debug(`📊 [CHART] Updated ${formattedCandles.length} candles`);
    }
    
    /**
     * Update volume data
     * @param {Array} candles - OHLCV candles
     */
    updateVolume(candles) {
        if (!this.volumeSeries) {
            console.error('❌ [CHART] Volume series not initialized');
            return;
        }
        
        const volumeData = candles.map(c => ({
            time: c[0] / 1000,
            value: c[5],
            color: c[4] >= c[1] ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)'
        }));
        
        this.volumeSeries.setData(volumeData);
    }
    
    /**
     * Add markers (signals, trades)
     * @param {Array} markers - Markers array
     */
    updateMarkers(markers) {
        if (!this.candleSeries) {
            console.error('❌ [CHART] Chart not initialized');
            return;
        }
        
        const formattedMarkers = markers.map(m => ({
            time: m.time / 1000,
            position: m.position || 'aboveBar',
            color: m.color || '#2196f3',
            shape: m.shape || 'circle',
            text: m.text
        }));
        
        this.candleSeries.setMarkers(formattedMarkers);
        console.debug(`📍 [CHART] Updated ${formattedMarkers.length} markers`);
    }
    
    /**
     * Add trading line
     * @param {Array} lineData - Line points
     * @param {string} color - Line color
     */
    addLine(lineData, color = '#2196f3') {
        if (!this.chart) {
            console.error('❌ [CHART] Chart not initialized');
            return;
        }
        
        const lineSeries = this.chart.addLineSeries({
            color: color,
            lineWidth: 2
        });
        
        const formattedData = lineData.map(d => ({
            time: d.time / 1000,
            value: d.value
        }));
        
        lineSeries.setData(formattedData);
        return lineSeries;
    }
    
    /**
     * Fit content to visible range
     */
    fitContent() {
        if (this.chart) {
            this.chart.timeScale().fitContent();
        }
    }
    
    /**
     * Set visible range
     * @param {number} from - From time (seconds)
     * @param {number} to - To time (seconds)
     */
    setVisibleRange(from, to) {
        if (this.chart) {
            this.chart.timeScale().setVisibleRange({ from, to });
        }
    }
    
    /**
     * Destroy chart
     */
    destroy() {
        if (this.chart) {
            this.chart.remove();
            this.chart = null;
            this.candleSeries = null;
            this.volumeSeries = null;
            console.log('🗑️ [CHART] Destroyed');
        }
    }
}

// Singleton instance
const chartRenderer = new ChartRenderer();

// Export singleton
export default chartRenderer;

// Also export for window access (debugging)
if (typeof window !== 'undefined') {
    window.chartRenderer = chartRenderer;
}
