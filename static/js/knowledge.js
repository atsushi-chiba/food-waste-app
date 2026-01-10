document.addEventListener('DOMContentLoaded', () => {
    const knowledgeItems = document.querySelectorAll('.knowledge-item');
    const triviaItems = document.querySelectorAll('#knowledge-list-container-trivia .knowledge-item'); // 豆知識のみ対象
    const filterButtons = document.querySelectorAll('.filter-btn');
    const searchInput = document.getElementById('knowledge-search');

    // フィルタリング処理（豆知識のみ対象）
    const applyFilters = () => {
        const activeBtn = document.querySelector('.filter-btn.active');
        const filterCategory = activeBtn ? activeBtn.getAttribute('data-filter') : '全て';
        const searchTerm = searchInput.value.toLowerCase();

        triviaItems.forEach(item => {
            const itemCategory = item.getAttribute('data-category');
            const itemText = item.textContent.toLowerCase();
            const matchesCategory = (filterCategory === '全て' || itemCategory === filterCategory);
            const matchesSearch = itemText.includes(searchTerm);

            if (matchesCategory && matchesSearch) {
                item.classList.remove('hidden');
            } else {
                item.classList.add('hidden');
            }
        });
    };

    searchInput.addEventListener('input', applyFilters);

    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            applyFilters();
        });
    });

    // --- モーダル制御の修正 ---
    knowledgeItems.forEach(item => {
        item.addEventListener('click', () => {
            // アレンジレシピの場合
            if (item.classList.contains('recipe-item')) {
                const title = item.getAttribute('data-title');
                const content = item.getAttribute('data-content');
                
                if (title && content) {
                    const recipeModal = document.getElementById('recipe-modal');
                    const titleElement = document.getElementById('recipe-modal-title');
                    const contentElement = document.getElementById('recipe-modal-content');
                    
                    titleElement.textContent = title;
                    contentElement.textContent = content;
                    
                    recipeModal.classList.add('is-active');
                    document.body.classList.add('modal-open');
                }
            } else {
                // 豆知識の場合（既存の処理）
                const targetId = item.getAttribute('data-target');
                const targetModal = document.getElementById(targetId);
                if (targetModal) {
                    targetModal.classList.add('is-active');
                    document.body.classList.add('modal-open'); 
                }
            }
        });
    });

    // 閉じるボタンのイベント（.modal-close に修正）
    const closeButtons = document.querySelectorAll('.modal-close');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            const modal = button.closest('.modal-overlay');
            if (modal) {
                modal.classList.remove('is-active');
                document.body.classList.remove('modal-open');
            }
        });
    });

    // オーバーレイ（背景）クリックで閉じる処理を追加
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('is-active');
                document.body.classList.remove('modal-open');
            }
        });
    });

    applyFilters();
});