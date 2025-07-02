// Цей скрипт відовідає за вибір телефону контакта в чаті
document.addEventListener('DOMContentLoaded', function() {
    const phoneInputs = document.querySelectorAll('input[name="selected_phone"]');
    const phoneNumberDisplay = document.getElementById('selectedPhoneDisplay');
    const phoneNameDisplay = document.getElementById('selectedPhoneName');
    const callLink = document.getElementById('callLink');

    function updateCallInfo() {
      let selected;
      if (phoneInputs.length === 1 && phoneInputs[0].type === 'hidden') {
        // якщо тільки один прихований — використовуємо його
        selected = phoneInputs[0];
      } else {
        // інакше шукаємо вибраний радіо
        selected = document.querySelector('input[name="selected_phone"]:checked');
      }

      if (selected) {
        const number = selected.value;
        const name = selected.dataset.name;
        phoneNumberDisplay.textContent = number;
        phoneNameDisplay.textContent = name;
        callLink.href = 'tel:' + number.replace(/\s+/g, '');
      } else {
        phoneNumberDisplay.textContent = '';
        phoneNameDisplay.textContent = '';
        callLink.href = '#';
      }
    }

    // Ініціалізуємо одразу
    updateCallInfo();

    // Якщо є кілька телефонів — слухаємо радіо
    phoneInputs.forEach(input => {
      if (input.type !== 'hidden') {
        input.addEventListener('change', updateCallInfo);
      }
    });
  });