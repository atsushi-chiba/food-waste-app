document.addEventListener('DOMContentLoaded', () => {
    const dailyLossChartCtx = document.getElementById('dailyLossChart').getContext('2d');
    const dishTableBody = document.querySelector('#dishTable tbody');
    const noDataMessage = document.getElementById('noDataMessage');

    // 1. URLから現在表示すべき週の基準日 ('date'パラメータ) を取得
    const urlParams = new URLSearchParams(window.location.search);
    const targetDate = urlParams.get('date') || new Date().toISOString().split('T')[0]; // パラメータがなければ今日の日付

    /**
     * APIから統計データを取得し、グラフとテーブルをレンダリングする
     * @param {string} date - 基準となる日付 (YYYY-MM-DD)
     */
    async function fetchAndRenderStats(date) {
        const apiUrl = `/api/weekly_stats?date=${date}`;
        let stats;

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            stats = await response.json();
        } catch (error) {
            console.error("Failed to fetch weekly stats:", error);
            stats = { is_data_present: false, daily_graph_data: [], dish_table: [] };
        }

        // 2. データ有無による表示の切り替え
        const chartContainer = document.querySelector('.chart-container');
        const tableContainer = document.querySelector('.table-container');
        
        if (!stats.is_data_present || stats.daily_graph_data.length === 0) {
            chartContainer.style.display = 'none';
            tableContainer.style.display = 'none';
            noDataMessage.style.display = 'block';
        } else {
            chartContainer.style.display = 'block';
            tableContainer.style.display = 'block';
            noDataMessage.style.display = 'none';

            // 3. 棒グラフの描画
            renderChart(dailyLossChartCtx, stats.daily_graph_data);

            // 4. テーブルデータの挿入
            renderTable(dishTableBody, stats.dish_table);
        }
    }

    /**
     * 日別廃棄量の棒グラフを描画する
     */
    function renderChart(ctx, dailyData) {
        const labels = dailyData.map(d => d.day); // ['日', '月', '火', ...]
        const data = dailyData.map(d => d.total_grams);

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '廃棄量 (グラム)',
                    data: data,
                    backgroundColor: 'rgba(40, 167, 69, 0.8)', // 緑色
                    borderColor: 'rgba(40, 167, 69, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '廃棄量 (g)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    /**
     * 週間廃棄品目一覧のテーブルに行を挿入する
     */
    function renderTable(tbody, tableData) {
        // 既存の行をクリア
        tbody.innerHTML = ''; 

        tableData.forEach(item => {
            const row = tbody.insertRow();
            
            // 日付 
            const dateCell = row.insertCell();
            dateCell.textContent = item.date;
            
            // 品目名
            const dishNameCell = row.insertCell();
            dishNameCell.textContent = item.dish_name;
            
            // 重量 (g)
            const weightCell = row.insertCell();
            weightCell.textContent = item.weight_grams.toFixed(1); // 小数点以下1桁まで
            weightCell.style.textAlign = 'right';

            // 理由
            const reasonCell = row.insertCell();
            reasonCell.textContent = item.reason;
        });
    }

    // ページロード時に統計情報を取得し、レンダリングを開始
    fetchAndRenderStats(targetDate);
});