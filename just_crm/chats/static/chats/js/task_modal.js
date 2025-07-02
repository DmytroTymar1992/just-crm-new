//Цей скрипт відповідає за створення задачі в чаті
document.addEventListener('DOMContentLoaded', function () {
    const modalContainer = document.getElementById('modalContainer');

    function closeModal(modal) {
        modal.style.display = 'none';
        modalContainer.innerHTML = '';
    }

    function showError(modal, error) {
        let errorDiv = modal.querySelector('.error-messages');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-messages';
            modal.querySelector('.tasks-modal-content').insertBefore(errorDiv, modal.querySelector('form'));
        }
        if (error.errors) {
            const errors = JSON.parse(error.errors);
            const labels = error.labels || {};
            let html = '<ul>';
            Object.entries(errors).forEach(([field, errs]) => {
                const label = labels[field] || field;
                errs.forEach(err => {
                    html += `<li>${label}: ${err.message}</li>`;
                });
            });
            html += '</ul>';
            errorDiv.innerHTML = html;
        } else {
            errorDiv.innerHTML = `<ul><li>${error.error || 'Невідома помилка'}</li></ul>`;
        }
    }

    function handleFormSubmit(e) {
        e.preventDefault();
        const form = this.closest('.ajax-form');
        const modal = form.closest('.tasks-modal');
        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ''
            }
        })
            .then(async response => {
                const data = await response.json();
                if (response.ok) {
                    if (data.success) closeModal(modal);
                    else showError(modal, data);
                } else {
                    showError(modal, data);
                }
            })
            .catch(error => {
                console.error('Error submitting form:', error);
                showError(modal, { error: 'Помилка відправки форми: ' + error.message });
            });
    }

    function typeEffect(el, text, delay = 40) {
        el.value = '';
        let i = 0;
        (function type() {
            if (i < text.length) {
                el.value += text.charAt(i);
                i++;
                setTimeout(type, delay);
            }
        })();
    }

    document.getElementById('createTaskBtn').addEventListener('click', function () {
        fetch('/tasks/create/{{ selected_chat.id }}/?prefill=1')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch modal content');
                }
                return response.text();
            })
            .then(html => {
                modalContainer.innerHTML = html;
                const modal = modalContainer.querySelector('.tasks-modal');
                if (!modal) {
                    console.error('Modal element not found in fetched HTML');
                    return;
                }
                modal.style.display = 'flex';

                const dataEl = modal.querySelector('#suggestion-json');
                if (dataEl) {
                    try {
                        const data = JSON.parse(dataEl.textContent);
                        const typeField = modal.querySelector('#id_task_type');
                        const targetField = modal.querySelector('#id_target');
                        const descField = modal.querySelector('#id_description');
                        if (typeField && data.task_type) typeField.value = data.task_type;
                        if (targetField && data.target) typeEffect(targetField, data.target);
                        if (descField && data.description) typeEffect(descField, data.description);
                    } catch (e) {
                        console.error('Failed to apply AI suggestion:', e);
                    }
                }

                const closeButton = modal.querySelector('.close');
                if (closeButton) {
                    closeButton.addEventListener('click', function () {
                        closeModal(modal);
                    });
                }

                modal.addEventListener('click', function (e) {
                    if (e.target === modal) {
                        closeModal(modal);
                    }
                });

                const submitButton = modal.querySelector('.ajax-submit');
                if (submitButton) {
                    submitButton.addEventListener('click', handleFormSubmit);
                } else {
                    console.warn('Submit button (.ajax-submit) not found in modal');
                }

                const dateInput = modal.querySelector('#id_task_date');
                if (dateInput && dateInput.value) {
                    loadSlots(dateInput.value);
                }
            })
            .catch(error => {
                console.error('Error fetching modal:', error);
                showToast('Помилка завантаження форми створення задачі');
            });
    });
});
