//цей скрипт відовідає за завантаження в чаті списку вакансій компанії по ворк юа

    document.addEventListener('DOMContentLoaded', () => {
    if (!chatId) return;

    fetch(`/chats/${chatId}/vacancies/html/`)
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('vacanciesContainer');
            container.innerHTML = data.html;
        })
        .catch(err => {
            console.error(err);
            document.getElementById('vacanciesContainer').innerHTML = '<p>Помилка завантаження</p>';
        });
});