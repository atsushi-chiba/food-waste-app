document.addEventListener('DOMContentLoaded', (event) => {
    const modal = document.getElementById('welcomeModal');
    const closeButton = document.getElementById('closeModalButton');

    // app.py で show_modal=True の時だけこのスクリプトが読み込まれる
    if (modal && modal.style.display !== 'none') {
        modal.classList.add('is-active'); 
    }

    const closeModal = () => {
        if (modal) {
            modal.classList.remove('is-active');
            setTimeout(() => {
                modal.style.display = 'none';
            }, 300);
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