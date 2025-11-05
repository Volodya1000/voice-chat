// Скролл вниз
export function scrollToBottom(messageList) {
  if (messageList) messageList.scrollTop = messageList.scrollHeight;
}

// Добавление нового сообщения в DOM
export function addMessageToDOM(messageList, message) {
  const time = new Date(message.created_at).toLocaleString();
  const messageDiv = document.createElement("div");
  const typeClass = message.message_type.toLowerCase();
  messageDiv.classList.add("message", typeClass);

  // ⚠ Важно: используем data-msg-id для согласованности с SSE
  messageDiv.setAttribute("data-msg-id", message.id);

  const meta = document.createElement("div");
  meta.className = "m-meta";
  const strong = document.createElement("strong");
  strong.textContent = message.message_type.charAt(0).toUpperCase() + message.message_type.slice(1);
  const spanTime = document.createElement("span");
  spanTime.className = "time";
  spanTime.textContent = time;
  meta.appendChild(strong);
  meta.appendChild(spanTime);

  const body = document.createElement("div");
  body.className = "m-body";
  body.textContent = message.content; // начальное содержимое

  messageDiv.appendChild(meta);
  messageDiv.appendChild(body);

  if (messageList) {
    messageList.appendChild(messageDiv);
    scrollToBottom(messageList);
    console.log("[DEBUG] Message added to DOM", message.id, messageDiv);
  }
}

// Добавление токенов модели в существующее сообщение
export function appendTokenToMessage(messageList, msgId, token) {
  const messageBody = document.querySelector(`.message[data-msg-id='${msgId}'] .m-body`);
  if (messageBody) {
    messageBody.parentElement.classList.remove("streaming");
    messageBody.textContent += token;
    scrollToBottom(messageList);
  } else {
    console.warn("[WARN] msgEl not found for token", msgId);
  }
}
