// chat_upload.js
export function setupDocumentUpload() {
  const uploadButton = document.getElementById('document-upload-button');
  const fileInput = document.getElementById('document-upload-input');
  const loadingIndicator = document.getElementById('loading-indicator');

  if (!uploadButton || !fileInput) {
    console.error('Не найдены элементы для загрузки документа.');
    return;
  }

  // Клик по кнопке открывает input
  uploadButton.addEventListener('click', () => {
    fileInput.click();
  });

  // Событие выбора файла
  fileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Получаем chat_id
    let chat_id;
    if (window.__CHAT_CONTEXT && window.__CHAT_CONTEXT.selected_chat !== undefined) {
      chat_id = typeof window.__CHAT_CONTEXT.selected_chat === 'object'
        ? window.__CHAT_CONTEXT.selected_chat.id
        : window.__CHAT_CONTEXT.selected_chat;
    }

    if (chat_id === undefined || chat_id === null) {
      console.error('Не найден ID чата (chat_id). Загрузка отменена.', window.__CHAT_CONTEXT);
      alert('Ошибка: Не удалось определить ID чата. Не могу загрузить файл.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);

    if (loadingIndicator) loadingIndicator.style.display = 'block';

    try {
      const response = await fetch(`/api/chats/${chat_id}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Файл успешно загружен:', result);
        alert(`Файл "${file.name}" успешно загружен.`);
      } else {
        const errorData = await response.json();
        console.error('Ошибка загрузки:', errorData);
        alert(`Ошибка загрузки: ${errorData.detail || 'Неизвестная ошибка'}`);
      }
    } catch (error) {
      console.error('Ошибка сети:', error);
      alert('Произошла сетевая ошибка. Попробуйте еще раз.');
    } finally {
      if (loadingIndicator) loadingIndicator.style.display = 'none';
      event.target.value = null;
    }
  });
}
