document.addEventListener('DOMContentLoaded', () => {
    const knowledgeItems = document.querySelectorAll('.knowledge-item');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const searchInput = document.getElementById('knowledge-search');

    // フィルタリング処理（変更なし）
    const applyFilters = () => {
        const activeBtn = document.querySelector('.filter-btn.active');
        const filterCategory = activeBtn ? activeBtn.getAttribute('data-filter') : '全て';
        const searchTerm = searchInput.value.toLowerCase();

        knowledgeItems.forEach(item => {
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
            const targetId = item.getAttribute('data-target');
            const targetModal = document.getElementById(targetId);
            if (targetModal) {
                // style.display ではなくクラスを追加する
                targetModal.classList.add('is-active');
                document.body.classList.add('modal-open'); 
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