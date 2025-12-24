document.addEventListener('DOMContentLoaded', () => {
    const knowledgeItems = document.querySelectorAll('.knowledge-item');
    const filterButtons = document.querySelectorAll('.filter-btn');
    const triviaContainer = document.getElementById('knowledge-list-container-trivia');

    // モーダルを開く処理
    knowledgeItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetId = item.getAttribute('data-target');
            const modal = document.getElementById(targetId);
            
            if (modal) {
                modal.classList.add('is-active');
                document.body.classList.add('modal-open');
            }
        });
    });

    // モーダルを閉じる関数
    const closeModal = (modal) => {
        modal.classList.remove('is-active');
        document.body.classList.remove('modal-open');
    };

    // 閉じるボタンおよび背景クリック
    document.querySelectorAll('.modal-overlay').forEach(modal => {
        const closeBtn = modal.querySelector('.modal-close');
        
        // 閉じるボタンクリック
        closeBtn.addEventListener('click', () => closeModal(modal));
        
        // 背景クリック
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal);
            }
        });
    });

    // フィルタリング機能
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            const filterCategory = button.getAttribute('data-filter');

            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            const items = triviaContainer.querySelectorAll('.knowledge-item'); 
            items.forEach(item => {
                const itemCategory = item.getAttribute('data-category');
                if (filterCategory === '全て' || itemCategory === filterCategory) {
                    item.classList.remove('hidden');
                } else {
                    item.classList.add('hidden');
                }
            });
        });
    });

    // 初期表示：最初のボタン（料理）をクリック
    const defaultButton = document.querySelector('.filter-btn');
    if (defaultButton) defaultButton.click();
});