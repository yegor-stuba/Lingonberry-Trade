// Performance Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Set up date range selector
    const dateRangeSelect = document.getElementById('date-range');
    dateRangeSelect.addEventListener('change', function() {
        const days = parseInt(this.value);
        updatePerformanceData(days);
    });
    
    // Initial load with default 30 days
    updatePerformanceData(30);
});

function updatePerformanceData(days) {
    // Fetch performance metrics
    fetchPerformanceMetrics(days);
    
    // Fetch equity curve data
    fetchEquityCurveData(days);
    
    // Fetch win rate data
    fetchWinRateData(days);
    
    // Fetch trade journal data
    fetchTradeJournalData(days);
}

function fetchPerformanceMetrics(days) {
    // Calculate date range
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    fetch(`/api/performance?start_date=${startDateStr}&end_date=${endDateStr}`)
        .then(response => response.json())
        .then(data => {
            // Update metrics
            document.getElementById('win-rate').textContent = data.win_rate.toFixed(1) + '%';
            document.getElementById('profit-factor').textContent = data.profit_factor.toFixed(2);
            document.getElementById('avg-win').textContent = '$' + data.avg_win.toFixed(2);
            document.getElementById('avg-loss').textContent = '$' + Math.abs(data.avg_loss).toFixed(2);
            document.getElementById('total-trades').textContent = data.trade_count;
            document.getElementById('total-pnl').textContent = '$' + data.total_pnl.toFixed(2);
        })
        .catch(error => {
            console.error('Error fetching performance metrics:', error);
        });
}

function fetchEquityCurveData(days) {
    fetch(`/api/performance/history?days=${days}`)
        .then(response => response.json())
        .then(data => {
            // Create equity curve chart
            const ctx = document.getElementById('equity-chart').getContext('2d');
            
            // Destroy existing chart if it exists
            if (window.equityChart) {
                window.equityChart.destroy();
            }
            
            window.equityChart = new Chart(ctx, {
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

function fetchWinRateData(days) {
    fetch(`/api/performance/history?days=${days}`)
        .then(response => response.json())
        .then(data => {
            // Create win rate chart
            const ctx = document.getElementById('win-rate-chart').getContext('2d');
            
            // Destroy existing chart if it exists
            if (window.winRateChart) {
                window.winRateChart.destroy();
            }
            
            window.winRateChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Win Rate %',
                        data: data.win_rate,
                        backgroundColor: 'rgba(40, 167, 69, 0.2)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 2,
                        pointRadius: 3,
                        pointBackgroundColor: 'rgba(40, 167, 69, 1)',
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
                                    return `Win Rate: ${context.raw.toFixed(1)}%`;
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
                            beginAtZero: true,
                            max: 100,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error fetching win rate data:', error);
        });
}

function fetchTradeJournalData(days) {
    // Calculate date range
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);
    
    const startDateStr = startDate.toISOString().split('T')[0];
    const endDateStr = endDate.toISOString().split('T')[0];
    
    fetch(`/api/trades?start_date=${startDateStr}&end_date=${endDateStr}&limit=100`)
        .then(response => response.json())
        .then(trades => {
            const tableBody = document.querySelector('#trade-journal-table tbody');
            tableBody.innerHTML = '';
            
            if (trades.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = '<td colspan="7" class="text-center">No trades in selected period</td>';
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
                    <td>${trade.entry_price}</td>
                    <td>${trade.exit_price || '-'}</td>
                    <td class="${pnlClass}">${trade.pnl ? '$' + trade.pnl.toFixed(2) : '-'}</td>
                    <td><span class="status-${trade.status.toLowerCase()}">${trade.status}</span></td>
                `;
                tableBody.appendChild(row);
            });
        })
        .catch(error => {
            console.error('Error fetching trade journal data:', error);
        });
}
