document.addEventListener('DOMContentLoaded', () => {
    const knowledgeItems = document.querySelectorAll('.knowledge-item');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const triviaContainer = document.getElementById('knowledge-list-container-trivia');
    const searchInput = document.getElementById('knowledge-search'); // 追加

    // 共通のフィルタリング関数
    const applyFilters = () => {
        const activeBtn = document.querySelector('.filter-btn.active');
        const filterCategory = activeBtn ? activeBtn.getAttribute('data-filter') : '全て';
        const searchTerm = searchInput.value.toLowerCase(); // 検索語を小文字に統一

        knowledgeItems.forEach(item => {
            const itemCategory = item.getAttribute('data-category');
            const itemText = item.textContent.toLowerCase(); // タイトルのテキスト

            // カテゴリの一致確認
            const matchesCategory = (filterCategory === '全て' || itemCategory === filterCategory);
            // 検索キーワードの一致確認
            const matchesSearch = itemText.includes(searchTerm);

            if (matchesCategory && matchesSearch) {
                item.classList.remove('hidden');
            } else {
                item.classList.add('hidden');
            }
        });
    };

    // 検索入力時のイベント
    searchInput.addEventListener('input', applyFilters);

    // フィルタボタンクリック時の処理を更新
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            applyFilters(); // フィルタ実行
        });
    });

    // --- 以下、モーダル制御のコードは変更なし ---
    knowledgeItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetId = item.getAttribute('data-target');
            const targetModal = document.getElementById(targetId);
            if (targetModal) {
                targetModal.style.display = 'block';
                document.body.classList.add('modal-open'); 
            }
        });
    });

    const closeButtons = document.querySelectorAll('.close-btn');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const modal = button.closest('.detail-modal');
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        });
    });

    // 初期状態の実行
    applyFilters();
});