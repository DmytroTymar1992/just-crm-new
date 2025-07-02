/**
 * Скрипт для форми відправки повідомлень:
 * 1) Автозростання #msgInput до 200px без скролбару
 * 2) Перемикання Telegram / Viber з різними класами та іконками
 */

document.addEventListener('DOMContentLoaded', function () {
  const textarea = document.getElementById('msgInput');

  textarea.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
  });

  const toggleChannel = document.getElementById('toggleChannel');
  const channelLabel = document.getElementById('currentChannel');
  const sendBtn = document.getElementById('sendBtn');
  const sendIcon = document.getElementById('sendIcon');

  // Отримуємо посилання на іконки з data-атрибутів
  const telegramIcon = sendBtn.dataset.iconTelegram;
  const viberIcon = sendBtn.dataset.iconViber;

  toggleChannel.addEventListener('click', function () {
    if (channelLabel.textContent === 'Telegram') {
      channelLabel.textContent = 'Viber';
      sendBtn.name = 'send_viber';
      toggleChannel.classList.remove('telegram');
      toggleChannel.classList.add('viber');
      sendIcon.src = viberIcon;
      sendIcon.alt = "Send to Viber";
    } else {
      channelLabel.textContent = 'Telegram';
      sendBtn.name = 'send_telegram';
      toggleChannel.classList.remove('viber');
      toggleChannel.classList.add('telegram');
      sendIcon.src = telegramIcon;
      sendIcon.alt = "Send to Telegram";
    }
  });
});
