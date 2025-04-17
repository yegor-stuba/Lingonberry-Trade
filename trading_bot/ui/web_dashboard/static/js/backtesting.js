// Backtesting Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Set default dates
    setDefaultDates();
    
    // Load available symbols
    loadSymbols();
    
    // Set up form submission
    const backtestForm = document.getElementById('backtest-form');
    backtestForm.addEventListener('submit', function(e) {
        e.preventDefault();
        runBacktest();
    });
});

function setDefaultDates() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 3); // 3 months ago
    
    document.getElementById('start-date').value = startDate.toISOString().split('T')[0];
    document.getElementById('end-date').value = endDate.toISOString().split('T')[0];
}

function loadSymbols() {
    fetch('/api/symbols')
        .then(response => response.json())
        .then(symbols => {
            const symbolSelect = document.getElementById('symbol');
            
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

function runBacktest() {
    // Show loading state
    document.getElementById('backtest-form').querySelector('button').textContent = 'Running...';
    
    // Get form data
    const formData = {
        symbol: document.getElementById('symbol').value,
        timeframe: document.getElementById('timeframe').value,
        start_date: document.getElementById('start-date').value,
        end_date: document.getElementById('end-date').value,
        strategy: document.getElementById('strategy').value,
        parameters: {
            risk_per_trade: parseFloat(document.getElementById('risk-per-trade').value)
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
        document.getElementById('backtest-form').querySelector('button').textContent = 'Run Backtest';
        
        if (data.success) {
            // Show results
            displayBacktestResults(data.results);
        } else {
            alert('Backtest failed: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error running backtest:', error);
        document.getElementById('backtest-form').querySelector('button').textContent = 'Run Backtest';
        alert('Error running backtest. Please try again.');
    });
}

function displayBacktestResults(results) {
    // Show results containers
    document.getElementById('backtest-results').style.display = 'block';
    document.getElementById('backtest-trades').style.display = 'block';
    
    // Update metrics
    document.getElementById('backtest-win-rate').textContent = results.metrics.win_rate.toFixed(1) + '%';
    document.getElementById('backtest-profit-factor').textContent = results.metrics.profit_factor.toFixed(2);
    document.getElementById('backtest-total-trades').textContent = results.trades.length;
    document.getElementById('backtest-total-pnl').textContent = '$' + results.metrics.total_pnl.toFixed(2);
    
    // Create equity curve chart
    createBacktestEquityChart(results.trades);
    
    // Populate trades table
    populateBacktestTradesTable(results.trades);
    
    // Scroll to results
    document.getElementById('backtest-results').scrollIntoView({ behavior: 'smooth' });
}

function createBacktestEquityChart(trades) {
    // Calculate cumulative P&L
    let cumulativePnl = 0;
    const equityData = trades.map(trade => {
        cumulativePnl += trade.pnl;
        return {
            date: new Date(trade.exit_time || trade.entry_time),
            pnl: cumulativePnl
        };
    });
    
    // Sort by date
    equityData.sort((a, b) => a.date - b.date);
    
    // Extract data for chart
    const labels = equityData.map(item => item.date.toLocaleDateString());
    const data = equityData.map(item => item.pnl);
    
    // Create chart
    const ctx = document.getElementById('backtest-equity-chart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (window.backtestEquityChart) {
        window.backtestEquityChart.destroy();
    }
    
    window.backtestEquityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Cumulative P&L',
                data: data,
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
}

function populateBacktestTradesTable(trades) {
    const tableBody = document.querySelector('#backtest-trades-table tbody');
    tableBody.innerHTML = '';
    
    if (trades.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="7" class="text-center">No trades generated</td>';
        tableBody.appendChild(row);
        return;
    }
    
    trades.forEach(trade => {
        const row = document.createElement('tr');
        const pnlClass = trade.pnl > 0 ? 'success-color' : 'danger-color';
        const entryDate = new Date(trade.entry_time).toLocaleDateString();
        
        row.innerHTML = `
            <td>${entryDate}</td>
            <td>${trade.symbol}</td>
            <td>${trade.direction}</td>
            <td>${trade.entry_price}</td>
            <td>${trade.exit_price || '-'}</td>
            <td class="${pnlClass}">${trade.pnl ? '$' + trade.pnl.toFixed(2) : '-'}</td>
            <td><span class="status-${trade.status.toLowerCase()}">${trade.status}</span></td>
        `;
        tableBody.appendChild(row);
    });
}
