export function setupSSE(selectedChatId, messageList, addMessageToDOM, appendTokenToMessage) {
  if (!selectedChatId || typeof EventSource === 'undefined') return;
  const eventSource = new EventSource(`/chats/${selectedChatId}/events`);
  eventSource.addEventListener("new_message", (event) => {
    const message = JSON.parse(event.data);
    addMessageToDOM(messageList, message);
  });
  eventSource.addEventListener("stream_token", (event) => {
    const tokenData = JSON.parse(event.data);
    appendTokenToMessage(messageList, tokenData.msg_id, tokenData.token);
  });
  eventSource.onerror = (err) => {
    console.error("SSE error", err);
    eventSource.close();
  };
}
