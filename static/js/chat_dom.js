export function scrollToBottom(messageList) {
  if (messageList) messageList.scrollTop = messageList.scrollHeight;
}

export function addMessageToDOM(messageList, message) {
  const time = new Date(message.created_at).toLocaleString();
  const messageDiv = document.createElement("div");
  const typeClass = message.message_type.toLowerCase();
  messageDiv.classList.add("message", typeClass);
  messageDiv.setAttribute("data-id", message.id);

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
  body.textContent = message.content;

  messageDiv.appendChild(meta);
  messageDiv.appendChild(body);

  if (messageList) {
    messageList.appendChild(messageDiv);
    scrollToBottom(messageList);
  }
}

export function appendTokenToMessage(messageList, msgId, token) {
  const messageBody = document.querySelector(`.message[data-id='${msgId}'] .m-body`);
  if (messageBody) {
    messageBody.parentElement.classList.remove("streaming");
    messageBody.textContent += token;
    scrollToBottom(messageList);
  }
}
