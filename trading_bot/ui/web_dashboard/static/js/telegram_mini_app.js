// Telegram Mini App JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Telegram WebApp
    const tgApp = window.Telegram.WebApp;
    tgApp.expand();
    
    // Set up tab switching
    setupTabs();
    
    // Load initial data
    loadPerformanceData();
    loadSymbols();
    
    // Set up backtest form submission
    const backtestForm = document.getElementById('tg-backtest-form');
    backtestForm.addEventListener('submit', function(e) {
        e.preventDefault();
        runQuickBacktest();
    });
});

function setupTabs() {
    const tabs = document.querySelectorAll('.tg-tab');
    const tabContents = document.querySelectorAll('.tg-tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding content
            const tabName = this.getAttribute('data-tab');
            this.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            // Load data for the selected tab
            if (tabName === 'performance') {
                loadPerformanceData();
            } else if (tabName === 'journal') {
                loadJournalData();
            }
        });
    });
}

function loadPerformanceData() {
    // Fetch performance metrics
    fetch('/api/performance')
        .then(response => response.json())
        .then(data => {
            // Update metrics
            document.getElementById('tg-win-rate').textContent = data.win_rate.toFixed(1) + '%';
            document.getElementById('tg-profit-factor').textContent = data.profit_factor.toFixed(2);
            document.getElementById('tg-total-trades').textContent = data.trade_count;
            document.getElementById('tg-total-pnl').textContent = '$' + data.total_pnl.toFixed(2);
            
            // Create equity curve chart
            createEquityChart(30);
        })
        .catch(error => {
            console.error('Error fetching performance data:', error);
        });
}

function createEquityChart(days) {
    fetch(`/api/performance/history?days=${days}`)
        .then(response => response.json())
        .then(data => {
            // Create equity curve chart
            const ctx = document.getElementById('tg-equity-chart').getContext('2d');
            
            // Destroy existing chart if it exists
            if (window.tgEquityChart) {
                window.tgEquityChart.destroy();
            }
            
            window.tgEquityChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'P&L',
                        data: data.cumulative_pnl,
                        backgroundColor: 'rgba(36, 129, 204, 0.2)',
                        borderColor: 'rgba(36, 129, 204, 1)',
                        borderWidth: 2,
                        pointRadius: 2,
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return `$${context.raw.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: false
                        },
                        y: {
                            beginAtZero: false,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error creating equity chart:', error);
        });
}

function loadJournalData() {
    fetch('/api/trades?limit=20')
        .then(response => response.json())
        .then(trades => {
            const tableBody = document.querySelector('#tg-trade-journal-table tbody');
            tableBody.innerHTML = '';
            
            if (trades.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="4" style="text-align: center;">No trades found</td>';
                tableBody.appendChild(row);
                return;
            }
            
            trades.forEach(trade => {
                const row = document.createElement('tr');
                const pnlClass = trade.pnl > 0 ? 'success-color' : 'danger-color';
                const dateStr = new Date(trade.entry_time).toLocaleDateString();
                
                row.innerHTML = `
                    <td>${dateStr}</td>
                    <td>${trade.symbol}</td>
                    <td>${trade.direction}</td>
                    <td class="${pnlClass}">${trade.pnl ? '$' + trade.pnl.toFixed(2) : '-'}</td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error loading journal data:', error);
        });
}

function loadSymbols() {
    fetch('/api/symbols')
        .then(response => response.json())
        .then(symbols => {
            const symbolSelect = document.getElementById('tg-symbol');
            
            symbols.forEach(symbol => {
                const option = document.createElement('option');
                option.value = symbol;
                option.textContent = symbol;
                symbolSelect.appendChild(option);
            });
            
            // Set default to BTCUSDT if available
            if (symbols.includes('BTCUSDT')) {
                symbolSelect.value = 'BTCUSDT';
            } else if (symbols.includes('EURUSD')) {
                symbolSelect.value = 'EURUSD';
            }
        })
        .catch(error => {
            console.error('Error loading symbols:', error);
        });
}

function runQuickBacktest() {
    // Show loading state
    document.getElementById('tg-backtest-form').querySelector('button').textContent = 'Running...';
    
    // Get form data
    const symbol = document.getElementById('tg-symbol').value;
    const timeframe = document.getElementById('tg-timeframe').value;
    const period = document.getElementById('tg-period').value;
    
    // Calculate dates
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - parseInt(period));
    
    const formData = {
        symbol: symbol,
        timeframe: timeframe,
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
        strategy: 'smc',
        parameters: {
            risk_per_trade: 1.0
        }
    };
    
    // Send request to API
    fetch('/api/backtest', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        // Reset button
        document.getElementById('tg-backtest-form').querySelector('button').textContent = 'Run Backtest';
        
        if (data.success) {
            // Show results via Telegram Mini App
            showBacktestResults(data.results);
        } else {
            // Show error in Telegram Mini App
            const tgApp = window.Telegram.WebApp;
            tgApp.showAlert('Backtest failed: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error running backtest:', error);
        document.getElementById('tg-backtest-form').querySelector('button').textContent = 'Run Backtest';
        
        // Show error in Telegram Mini App
        const tgApp = window.Telegram.WebApp;
        tgApp.showAlert('Error running backtest. Please try again.');
    });
}

function showBacktestResults(results) {
    // Format results for Telegram Mini App
    const tgApp = window.Telegram.WebApp;
    
    // Create a summary message
    const summary = `
    Backtest Results:
    
    Symbol: ${results.symbol}
    Period: ${results.start_date} to ${results.end_date}
    
    Win Rate: ${results.metrics.win_rate.toFixed(1)}%
    Profit Factor: ${results.metrics.profit_factor.toFixed(2)}
    Total Trades: ${results.trades.length}
    Total P&L: $${results.metrics.total_pnl.toFixed(2)}
    `;
    
    // Show results in Telegram Mini App
    tgApp.showPopup({
        title: 'Backtest Results',
        message: summary,
        buttons: [
            {text: 'OK', type: 'default'}
        ]
    });
    
    // Send results back to the bot
    tgApp.sendData(JSON.stringify({
        action: 'backtest_results',
        results: {
            symbol: results.symbol,
            timeframe: results.timeframe,
            win_rate: results.metrics.win_rate,
            profit_factor: results.metrics.profit_factor,
            total_trades: results.trades.length,
            total_pnl: results.metrics.total_pnl
        }
    }));
}
