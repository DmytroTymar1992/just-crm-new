/* static/js/base.js */
/* Скрипт викидає користувача після 15 хв неактивності */
document.addEventListener('DOMContentLoaded', function() {
    console.log('JavaScript loaded!');

    // Перевіряємо, чи користувач авторизований (logoutUrl визначений)
    if (typeof logoutUrl !== 'undefined') {
        let inactivityTimer;

        // Функція для скидання таймера
        function resetTimer() {
            clearTimeout(inactivityTimer);
            inactivityTimer = setTimeout(function() {
                window.location.href = logoutUrl; // Перенаправлення на логаут
            }, inactivityTimeout);
        }

        // Слухачі подій для активності користувача
        document.addEventListener('mousemove', resetTimer);
        document.addEventListener('keydown', resetTimer);
        document.addEventListener('click', resetTimer);
        document.addEventListener('scroll', resetTimer);

        // Запускаємо таймер при завантаженні сторінки
        resetTimer();
    }
});