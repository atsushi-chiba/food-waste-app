document.addEventListener('DOMContentLoaded', () => {
    const dailyLossChartCtx = document.getElementById('dailyLossChart').getContext('2d');
    const dishTableBody = document.querySelector('#dishTable tbody');
    const noDataMessage = document.getElementById('noDataMessage');

    // チャートインスタンス保持用
    let myChart = null;

    const urlParams = new URLSearchParams(window.location.search);
    const targetDate = urlParams.get('date') || new Date().toISOString().split('T')[0];

    async function fetchAndRenderStats(date) {
        const apiUrl = `/api/weekly_stats?date=${date}`;
        try {
            const response = await fetch(apiUrl);
            const stats = await response.json();

            const chartContainer = document.querySelector('.chart-container');
            const tableContainer = document.querySelector('.table-container');

            if (!stats.is_data_present) {
                chartContainer.style.display = 'none';
                tableContainer.style.display = 'none';
                noDataMessage.style.display = 'block';
            } else {
                chartContainer.style.display = 'block';
                tableContainer.style.display = 'block';
                noDataMessage.style.display = 'none';

                renderChart(dailyLossChartCtx, stats.daily_graph_data);
                renderTable(dishTableBody, stats.dish_table);
            }
        } catch (error) {
            console.error("Fetch error:", error);
        }
    }

    function renderChart(ctx, dailyData) {
        // 既存のチャートを破棄
        if (myChart) {
            myChart.destroy();
        }

        myChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dailyData.map(d => d.day),
                datasets: [{
                    label: '廃棄量 (g)',
                    data: dailyData.map(d => d.total_grams),
                    backgroundColor: 'rgba(76, 175, 80, 0.8)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // CSSの高さ設定を優先
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }

    function renderTable(tbody, tableData) {
        tbody.innerHTML = '';
        tableData.forEach(item => {
            const row = tbody.insertRow();
            row.insertCell().textContent = item.date;
            row.insertCell().textContent = item.dish_name;
            const weightCell = row.insertCell();
            weightCell.textContent = item.weight_grams.toFixed(1);
            weightCell.style.textAlign = 'right';
            row.insertCell().textContent = item.reason;
        });
    }

    fetchAndRenderStats(targetDate);
});