// Цей скрипт відповідає за швидкі команди в полі введення повідомлення такі як - пос. та прив.

document.addEventListener('DOMContentLoaded', () => {
    const msgInput = document.getElementById('msgInput');

    function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'; // або без обмеження — textarea.scrollHeight + 'px'
}

    if (!chatId || !msgInput) return; // Перевірка наявності чату та поля

    // Обробка введення тексту
    msgInput.addEventListener('input', (e) => {
    const originalText = e.target.value;
    const lowerText = originalText.toLowerCase();

    // Скидаємо стилі помилки, якщо текст не "прив."
    if (msgInput.classList.contains('error-input') && lowerText.trim() !== 'прив.') {
        msgInput.classList.remove('error-input');
        console.log('Removed error-input class due to text change');
    }

    // Обробка "пос." як окремого слова
    const posRegex = /(?:^|\s)(пос\.)(?=\s|$)/i;
    if (posRegex.test(originalText)) {
        if (referralLink) {
            e.target.value = originalText.replace(posRegex, (match, p1) => match.replace(p1, referralLink));
            autoResizeTextarea(e.target);
        } else {
            showToast('Посилання для контакту відсутнє');
        }
        return;
    }

    // Обробка "прив." тільки якщо це єдине слово
    if (lowerText.trim() === 'прив.') {
        if (!welcomeMessage) {
            showToast('Привітальне повідомлення не налаштовано');
            return;
        }
        if (!referralLink) {
            showToast('Посилання для контакту відсутнє');
            return;
        }
        if (!userPhone) {
            showToast('Номер телефону користувача не налаштовано');
            return;
        }

        const nameWords = contactName.trim().split(/\s+/);
        const validName = nameWords.find(word =>
            ukrainianNames.some(name => name.toLowerCase() === word.trim().toLowerCase())
        );
        const isValidName = !!validName;

        let finalMessage = welcomeMessage
            .replace('{link}', referralLink)
            .replace('{phone}', userPhone)
            .replace('{contact_name}', isValidName ? validName : '');

        e.target.value = finalMessage;
        autoResizeTextarea(e.target);

        if (!isValidName && contactName) {
            msgInput.classList.add('error-input');
            showToast('Ім’я контакту некоректне');
            console.log('Applied error-input class. contactName:', contactName, 'isValidName:', isValidName, 'nameWords:', nameWords, 'validName:', validName);
        } else {
            console.log('No error-input applied. contactName:', contactName, 'isValidName:', isValidName, 'validName:', validName);
        }
    }
});
});