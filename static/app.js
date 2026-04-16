const API = "http://127.0.0.1:5000";

let userId = localStorage.getItem("user_id") || crypto.randomUUID();
localStorage.setItem("user_id", userId);

let convId = localStorage.getItem("conv_id");

async function init() {
  if (!convId) {
    const name = prompt("Enter your name");
    const res = await fetch(`${API}/start`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ user_id: userId, name })
    });

    const data = await res.json();
    convId = data.id;
    localStorage.setItem("conv_id", convId);
  }

  setInterval(loadMessages, 2000); // auto refresh
}

const messagesDiv = document.getElementById("messages");

async function loadMessages() {
  const res = await fetch(`${API}/messages/${convId}`);
  const data = await res.json();

  messagesDiv.innerHTML = "";

  data.forEach(m => {
    messagesDiv.innerHTML += `
      <div class="msg ${m.sender}">
        ${m.message || ""}
        ${m.image_url ? `<img src="${m.image_url}" />` : ""}
      </div>
    `;
  });

  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

document.getElementById("msg").addEventListener("input", () => {
  fetch(`${API}/typing`, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ conversation_id: convId, typing: true })
  });
});

async function deleteConversation(id) {
  await fetch(`${API}/admin/delete_conversation/${id}`, {
    method: "DELETE"
  });
  loadConvs();
}

document.getElementById("chatForm").onsubmit = async (e) => {
  e.preventDefault();

  const formData = new FormData();
  formData.append("conversation_id", convId);
  formData.append("message", msg.value);

  const file = image.files[0];
  if (file) formData.append("image", file);

  await fetch(`${API}/send`, { method: "POST", body: formData });

  msg.value = "";
};

init();