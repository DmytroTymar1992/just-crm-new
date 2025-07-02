// Цей скрипт відповідає за відправку повідомлень в вайбер або телеграм
document.addEventListener('DOMContentLoaded', () => {
  if (!chatId || (!viberSendUrl && !telegramSendUrl)) return; // немає вибраного чату або URL

  const form = document.getElementById('sendForm');
  if (!form) return; // форми немає
  const input = document.getElementById('msgInput');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;

    // Визначаємо, на яку кнопку натиснули
    const buttonName = e.submitter.name;
    const sendUrl = buttonName === 'send_viber' ? viberSendUrl : telegramSendUrl;

    if (!sendUrl) {
      showToast('Немає URL для відправки повідомлення');
      return;
    }

    try {
      const resp = await fetch(sendUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify({ text })
      });

      if (!resp.ok) {
        console.error('Failed to send message:', resp.status, await resp.text());
        showToast(`Помилка відправки до ${buttonName === 'send_viber' ? 'Viber' : 'Telegram'} (HTTP ${resp.status})`);
      } else {
        input.value = ''; // Очищаємо поле після успішної відправки
      }
      // WebSocket додасть повідомлення через update_interaction
    } catch (error) {
      console.error(`Error sending message to ${buttonName === 'send_viber' ? 'Viber' : 'Telegram'}:`, error);
      showToast(`Помилка відправки повідомлення до ${buttonName === 'send_viber' ? 'Viber' : 'Telegram'}: ${error.message}`);
    }
  });
});