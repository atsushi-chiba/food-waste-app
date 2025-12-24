document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('confirmation-modal');
    const tradeButtons = document.querySelectorAll('.trade-button');
    const confirmYes = document.getElementById('confirm-yes');
    const confirmNo = document.getElementById('confirm-no');
    const closeTop = document.getElementById('close-modal-top');
    const itemNameSpan = document.getElementById('item-name');
    const itemCostSpan = document.getElementById('item-cost');

    let currentItem = null;

    // モーダルを開く
    tradeButtons.forEach(button => {
        button.addEventListener('click', () => {
            currentItem = button.getAttribute('data-item');
            const currentCost = button.getAttribute('data-cost');
            itemNameSpan.textContent = currentItem;
            itemCostSpan.textContent = currentCost;
            modal.classList.add('is-active');
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

    // 交換実行（仮の処理）
    confirmYes.addEventListener('click', () => {
        closeModal();
        // 既存のトースト通知関数があれば呼び出し
        if (typeof showToast === 'function') {
            showToast(`${currentItem} を交換しました！`);
        } else {
            alert(`${currentItem} を交換しました！`);
        }
    });
});