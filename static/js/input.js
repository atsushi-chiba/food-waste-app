document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('main-input-form');
    const foodLossItem = document.getElementById('dish1');
    const foodLossAmount = document.getElementById('amount1');
    const leftoverItem = document.getElementById('dish2');

    form.addEventListener('submit', function(event) {
        const foodLossItemValue = foodLossItem.value.trim();
        const foodLossAmountValue = foodLossAmount.value.trim();
        const foodLossReasonValue = document.querySelector('input[name="reason_text"]:checked');
        const leftoverItemValue = leftoverItem.value.trim();

        const isFoodLossInput = foodLossItemValue || foodLossAmountValue || foodLossReasonValue;
        const isLeftoverInput = leftoverItemValue;

        // どちらも未入力の場合は送信を防ぐ
        if (!isFoodLossInput && !isLeftoverInput) {
            alert('少なくともどちらか一方のフォームを入力してください。');
            event.preventDefault();
            return;
        }

        // フードロス記録が入力されている場合、すべての項目が入力されているかチェック
        if (isFoodLossInput) {
            if (!foodLossItemValue || !foodLossAmountValue || !foodLossReasonValue) {
                alert('フードロス記録を送信する場合は、すべての項目（料理名/品目名、廃棄量、廃棄理由）を入力してください。');
                event.preventDefault();
                return;
            }
        }
    });
});
