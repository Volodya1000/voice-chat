export function setupSendForm(sendForm, messageInput, selectedChatId) {
  if (!sendForm) return;
  sendForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const content = messageInput.value.trim();
    if (!content) return;
    const original = content;
    messageInput.value = "";

    try {
      const resp = await fetch(`/chats/${selectedChatId}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ content })
      });
      if (!resp.ok) {
        console.error("Failed to send", await resp.text());
        messageInput.value = original;
      }
    } catch (err) {
      console.error("Error sending message:", err);
      messageInput.value = original;
    }
  });
}
