// Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Set current date
    const currentDate = new Date();
    document.getElementById('current-date').textContent = currentDate.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    
    // Fetch performance metrics
    fetchPerformanceMetrics();
    
    // Fetch active trades
    fetchActiveTrades();
    
    // Fetch recent trades
    fetchRecentTrades();
    
    // Fetch equity curve data
    fetchEquityCurveData();
});

function fetchPerformanceMetrics() {
    fetch('/api/performance')
        .then(response => response.json())
        .then(data => {
            // Update metrics
            document.getElementById('win-rate').textContent = data.win_rate.toFixed(1) + '%';
            document.getElementById('profit-factor').textContent = data.profit_factor.toFixed(2);
            document.getElementById('total-trades').textContent = data.trade_count;
            document.getElementById('total-pnl').textContent = '$' + data.total_pnl.toFixed(2);
        })
        .catch(error => {
            console.error('Error fetching performance metrics:', error);
        });
}

function fetchActiveTrades() {
    fetch('/api/trades?status=active')
        .then(response => response.json())
        .then(trades => {
            const tableBody = document.querySelector('#active-trades-table tbody');
            tableBody.innerHTML = '';
            
            if (trades.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="6" class="text-center">No active trades</td>';
                tableBody.appendChild(row);
                return;
            }
            
            trades.forEach(trade => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${trade.symbol}</td>
                    <td>${trade.direction}</td>
                    <td>${trade.entry_price}</td>
                    <td>${trade.stop_loss}</td>
                    <td>${trade.take_profit}</td>
                    <td><span class="status-active">Active</span></td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error fetching active trades:', error);
        });
}

function fetchRecentTrades() {
    fetch('/api/trades?status=closed&limit=10')
        .then(response => response.json())
        .then(trades => {
            const tableBody = document.querySelector('#recent-trades-table tbody');
            tableBody.innerHTML = '';
            
            if (trades.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="6" class="text-center">No recent trades</td>';
                tableBody.appendChild(row);
                return;
            }
            
            trades.forEach(trade => {
                const row = document.createElement('tr');
                const pnlClass = trade.pnl > 0 ? 'success-color' : 'danger-color';
                
                row.innerHTML = `
                    <td>${trade.symbol}</td>
                    <td>${trade.direction}</td>
                    <td>${trade.entry_price}</td>
                    <td>${trade.exit_price}</td>
                    <td class="${pnlClass}">$${trade.pnl.toFixed(2)}</td>
                    <td><span class="status-closed">Closed</span></td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error fetching recent trades:', error);
        });
}

function fetchEquityCurveData() {
    fetch('/api/performance/history?days=30')
        .then(response => response.json())
        .then(data => {
            // Create equity curve chart
            const ctx = document.getElementById('equity-chart').getContext('2d');
            
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Cumulative P&L',
                        data: data.cumulative_pnl,
                        backgroundColor: 'rgba(74, 111, 165, 0.2)',
                        borderColor: 'rgba(74, 111, 165, 1)',
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: 'rgba(74, 111, 165, 1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return `P&L: $${context.raw.toFixed(2)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false
                            }
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
            console.error('Error fetching equity curve data:', error);
        });
}
