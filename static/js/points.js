document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('confirmation-modal');
    const tradeButtons = document.querySelectorAll('.trade-button');
    const confirmYes = document.getElementById('confirm-yes');
    const confirmNo = document.getElementById('confirm-no');
    const closeTop = document.getElementById('close-modal-top');
    const itemNameSpan = document.getElementById('item-name');
    const itemCostSpan = document.getElementById('item-cost');

    let currentItem = null;

    // モーダルを開く前にポイントをチェックする
    tradeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const cost = parseInt(button.getAttribute('data-cost'), 10);
            const item = button.getAttribute('data-item');
            
            // 現在のポイント数をDOMから取得
            const currentPointsText = document.querySelector('.current-points').textContent;
            const currentPoints = parseInt(currentPointsText, 10);

            // ポイントが足りているかチェック
            if (currentPoints < cost) {
                // 足りない場合はトーストで通知
                showToast('ポイントが不足しています');
            } else {
                // 足りている場合はモーダルを表示
                currentItem = item;
                itemNameSpan.textContent = item;
                itemCostSpan.textContent = cost;
                // 「はい」ボタンにデータを設定
                confirmYes.setAttribute('data-item', item);
                confirmYes.setAttribute('data-cost', cost);
                modal.classList.add('is-active');
            }
        });
    });

    // モーダルを閉じる共通関数
    const closeModal = () => {
        modal.classList.remove('is-active');
    };

    // 閉じるアクション
    [confirmNo, closeTop].forEach(btn => {
        if (btn) btn.addEventListener('click', closeModal);
    });

    // 背景クリックで閉じる
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });



    // 4. 「はい」ボタンの処理 (★アラートをトーストに置き換え)
    confirmYes.addEventListener('click', async function() {
        const itemToTrade = this.getAttribute('data-item');
        // cost は modal 内の表示から取得
        const cost = Number(document.getElementById('item-cost').textContent);

        // サーバーへ交換リクエストを送る
        try {
            const resp = await fetch('/api/redeem', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_name: itemToTrade, cost: cost })
            });

            const result = await resp.json();

            if (resp.ok) {
                showToast(result.message);
                // ポイント表示を更新
                fetchAndDisplayPoints();
            } else {
                // 失敗時はエラーメッセージを表示
                showToast(result.message || '交換に失敗しました');
            }
        } catch (err) {
            console.error('交換リクエストエラー:', err);
            showToast('交換中にエラーが発生しました');
        } finally {
            closeModal();
        }
    });
});

// static/js/points.js (新規/修正)

// ----------------------------------------------------
// 1. ポイントデータを取得し、HTMLに表示する関数
// ----------------------------------------------------
async function fetchAndDisplayPoints() {
    try {
        // バックエンドのユーザープロフィールAPIを呼び出す
        // このAPIは、ユーザー名、合計ポイントなどを返す想定
        const response = await fetch('/api/user/me'); 
        
        if (!response.ok) {
            throw new Error('ポイントデータの取得に失敗しました。');
        }
        
        const data = await response.json();
        const totalPoints = data.total_points || 0; // total_points フィールドを想定
        
        // HTMLの該当要素を更新
        const pointsElement = document.querySelector('.current-points');
        if (pointsElement) {
            pointsElement.innerHTML = `${totalPoints}<span class="unit">P</span>`;
        }
        
        return totalPoints; // 交換ロジックで使用するために返す
        
    } catch (error) {
        console.error('ポイント表示エラー:', error);
        // エラーメッセージを表示する処理などをここに追加
        return 0; 
    }
}

// ----------------------------------------------------
// 2. ポイント計算をトリガーする関数 (デバッグ用/週次処理)
// ----------------------------------------------------
// (現在、画面上にトリガーボタンがないため、このロジックはデバッグ用とします)
async function triggerWeeklyPointCalculation() {
    try {
        // バックエンドのポイント計算APIを呼び出す
        const response = await fetch('/api/calculate_weekly_points', {
            method: 'POST', // ポイント計算はDBを更新するためPOSTが適切
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        if (!response.ok) {
            throw new Error('ポイント計算中にサーバーエラーが発生しました。');
        }
        
        const result = await response.json();
        console.log('ポイント計算結果:', result);
        // 成功したらポイントを再取得して表示を更新
        fetchAndDisplayPoints(); 
        
    } catch (error) {
        console.error('ポイント計算トリガーエラー:', error);
        // ユーザーに通知
    }
}


// ----------------------------------------------------
// 3. ページロード時の初期実行
// ----------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    fetchAndDisplayPoints();
    // もし週次ポイント計算を明示的にトリガーしたいボタンがあれば、ここでイベントリスナーを設定
});