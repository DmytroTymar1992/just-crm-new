// цей скрипт відовідає за завантаження сторінок пагінацї при скролі до верху, за відображення чату за замовчуванням
// внизу скрол та за перенесення блоку задачі на верх при додаванні сторінок пагінації
document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');

    if (chatMessages) {
        const chatId = chatMessages.dataset.chatId;
        const page = parseInt(chatMessages.dataset.page) || 1;
        const hasPrevious = chatMessages.dataset.hasPrevious === 'true';

        // Функція для переміщення .task-info на початок
        function ensureTaskInfoOnTop() {
            const taskInfo = chatMessages.querySelector('.task-info');
            if (taskInfo && taskInfo.parentNode === chatMessages && chatMessages.firstChild !== taskInfo) {
                chatMessages.prepend(taskInfo); // Переміщаємо .task-info, якщо він не перший
            }
        }

        if (chatId !== 'null') {
            // Прокрутка донизу при завантаженні
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Обробка прокрутки до верху для завантаження старіших взаємодій
            let isLoading = false;
            let currentPage = page;
            let hasMorePrevious = hasPrevious;

            chatMessages.addEventListener('scroll', () => {
                if (isLoading || !hasMorePrevious) return;

                // Перевірка, чи прокручено майже до верху
                if (chatMessages.scrollTop < 50) {
                    isLoading = true;
                    const previousScrollHeight = chatMessages.scrollHeight;
                    currentPage -= 1;

                    fetch(`/chats/${chatId}/?page=${currentPage}`, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.html) {
                            // Додаємо старіші повідомлення нагорі
                            const tempDiv = document.createElement('div');
                            tempDiv.innerHTML = data.html;
                            const nodes = Array.from(tempDiv.children).filter(node => !node.classList.contains('task-info'));
                            for (let i = nodes.length - 1; i >= 0; i--) {
                                chatMessages.insertBefore(nodes[i], chatMessages.firstChild);
                            }
                            if (typeof observeUnreadMessages === 'function') {
                                observeUnreadMessages();
                            }
                            // Оновлюємо позицію прокрутки
                            const newScrollHeight = chatMessages.scrollHeight;
                            chatMessages.scrollTop = newScrollHeight - previousScrollHeight + chatMessages.scrollTop;
                            hasMorePrevious = data.has_previous;
                            ensureTaskInfoOnTop(); // Переміщуємо .task-info
                        }
                        isLoading = false;
                    })
                    .catch(error => {
                        console.error('Помилка завантаження взаємодій:', error);
                        isLoading = false;
                    });
                }
            });
        }
    }
});