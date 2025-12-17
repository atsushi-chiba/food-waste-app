document.addEventListener('DOMContentLoaded', (event) => {
    const modal = document.getElementById('welcomeModal');
    const closeButton = document.getElementById('closeModalButton');

    // ページロード時にモーダルを表示
    if (modal) {
        // display: flex; の代わりにクラスを追加してアニメーションを有効化
        modal.classList.add('is-active'); 
    }

    // モーダルを閉じる関数
    const closeModal = () => {
        if (modal) {
            // アニメーションのためにクラスを削除し、アニメーション後に非表示にする
            modal.classList.remove('is-active');
            
            // アニメーションが完了するのを待ってから display: none にする (CSSのtransition時間と合わせる)
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300); // 0.3秒待つ
        }
    };

    // 閉じるボタンがクリックされたとき
    if (closeButton) {
        closeButton.addEventListener('click', closeModal);
    }

    // モーダル外のオーバーレイがクリックされたとき
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
    
    // Escキーが押されたとき
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('is-active')) {
            closeModal();
        }
    });
});