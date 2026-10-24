/**
 * TrekBuddy – Your Indian Trek Guide
 * Frontend JavaScript Client
 * Integrates directly with FastAPI backend on http://127.0.0.1:8080/api/chat
 */

document.addEventListener("DOMContentLoaded", () => {
  // Backend Endpoints
  const API_BASE = "http://127.0.0.1:8080";
  const CHAT_ENDPOINT = `${API_BASE}/api/chat`;
  const RESET_ENDPOINT = `${API_BASE}/api`;

  // DOM Elements
  const chatMessages = document.getElementById("chatMessages");
  const chatWrapper = document.querySelector(".chat-wrapper");
  const chatForm = document.getElementById("chatForm");
  const messageInput = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");
  const clearBtn = document.getElementById("clearBtn");
  const errorBanner = document.getElementById("errorBanner");
  const errorMessage = document.getElementById("errorMessage");
  const dismissError = document.getElementById("dismissError");
  const suggestionsContainer = document.getElementById("suggestionsContainer");

  let isSending = false;

  // Auto-focus input on load
  messageInput.focus();

  // Scroll to bottom helper
  function scrollToBottom() {
    chatWrapper.scrollTo({
      top: chatWrapper.scrollHeight,
      behavior: "smooth"
    });
  }

  // Auto-resize textarea to fit content (up to 120px)
  function adjustTextareaHeight() {
    messageInput.style.height = "auto";
    const newHeight = Math.min(messageInput.scrollHeight, 120);
    messageInput.style.height = `${newHeight}px`;
  }

  messageInput.addEventListener("input", adjustTextareaHeight);

  // Dismiss Error Banner
  dismissError.addEventListener("click", () => {
    errorBanner.hidden = true;
  });

  function showError(msg) {
    errorMessage.textContent = msg;
    errorBanner.hidden = false;
  }

  function hideError() {
    errorBanner.hidden = true;
  }

  // Format assistant text safely (escaping HTML and converting basic markdown: bold, lists, headers, tables)
  function formatAssistantMessage(text) {
    if (!text) return "";

    // Escape HTML first to prevent XSS
    let escaped = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");

    // Convert markdown bold (**text**) to <strong>text</strong>
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Process line by line
    const lines = escaped.split("\n");
    let result = [];
    let inList = false;
    let inTable = false;
    let tableHeaderDone = false;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();

      // Check if table row (| Col 1 | Col 2 |)
      if (line.startsWith("|") && line.endsWith("|")) {
        // Table divider row: |---|---|
        if (/^\|[\s\-:|]+\|$/.test(line)) {
          tableHeaderDone = true;
          continue;
        }

        if (!inTable) {
          if (inList) {
            result.push("</ul>");
            inList = false;
          }
          result.push('<div class="table-responsive"><table class="trek-table">');
          inTable = true;
          tableHeaderDone = false;
        }

        const cells = line.slice(1, -1).split("|").map(c => c.trim());
        const cellTag = !tableHeaderDone ? "th" : "td";
        const rowHtml = cells.map(c => `<${cellTag}>${c}</${cellTag}>`).join("");
        result.push(`<tr>${rowHtml}</tr>`);
        continue;
      } else if (inTable) {
        result.push("</table></div>");
        inTable = false;
      }

      // Check if heading (### or ## or #)
      const headingMatch = line.match(/^(#{1,4})\s+(.*)$/);
      if (headingMatch) {
        if (inList) {
          result.push("</ul>");
          inList = false;
        }
        const level = Math.min(headingMatch[1].length + 1, 4);
        result.push(`<h${level} class="trek-heading">${headingMatch[2]}</h${level}>`);
        continue;
      }

      // Check if bullet list
      const bulletMatch = line.match(/^[-*•]\s+(.*)$/);
      if (bulletMatch) {
        if (!inList) {
          result.push("<ul>");
          inList = true;
        }
        result.push(`<li>${bulletMatch[1]}</li>`);
        continue;
      } else if (inList) {
        result.push("</ul>");
        inList = false;
      }

      // Standard paragraph
      if (line.length > 0) {
        result.push(`<p>${line}</p>`);
      }
    }

    if (inList) result.push("</ul>");
    if (inTable) result.push("</table></div>");

    return result.join("") || `<p>${escaped}</p>`;
  }

  // Append a user or assistant message to the chat container
  function appendMessage(role, text) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = `avatar ${role}-avatar`;
    avatar.setAttribute("aria-hidden", "true");

    if (role === "assistant") {
      avatar.innerHTML = `
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 20h18L12 4 3 20z"/>
        </svg>`;
    } else {
      avatar.innerHTML = `
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        </svg>`;
    }

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    const sender = document.createElement("div");
    sender.className = "message-sender";
    sender.textContent = role === "assistant" ? "TrekBuddy" : "You";

    const content = document.createElement("div");
    content.className = "message-content";

    if (role === "assistant") {
      content.innerHTML = formatAssistantMessage(text);
    } else {
      const p = document.createElement("p");
      p.textContent = text;
      content.appendChild(p);
    }

    bubble.appendChild(sender);
    bubble.appendChild(content);

    row.appendChild(avatar);
    row.appendChild(bubble);

    chatMessages.appendChild(row);
    scrollToBottom();
  }

  // Append and remove typing / loading indicator
  function createLoadingIndicator() {
    const loadingRow = document.createElement("div");
    loadingRow.className = "message-row assistant loading-row";
    loadingRow.id = "activeLoadingIndicator";

    const avatar = document.createElement("div");
    avatar.className = "avatar assistant-avatar";
    avatar.innerHTML = `
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M3 20h18L12 4 3 20z"/>
      </svg>`;

    const bubble = document.createElement("div");
    bubble.className = "typing-bubble";
    bubble.innerHTML = `
      <div class="typing-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span class="typing-label">TrekBuddy is thinking...</span>
    `;

    loadingRow.appendChild(avatar);
    loadingRow.appendChild(bubble);

    chatMessages.appendChild(loadingRow);
    scrollToBottom();
    return loadingRow;
  }

  function removeLoadingIndicator() {
    const loadingRow = document.getElementById("activeLoadingIndicator");
    if (loadingRow) {
      loadingRow.remove();
    }
  }

  // Handle Send Message
  async function handleSendMessage(rawText) {
    const text = (rawText || messageInput.value).trim();

    // Prevent sending empty messages
    if (!text || isSending) return;

    // Reset input field and height
    messageInput.value = "";
    messageInput.style.height = "auto";
    hideError();

    // Hide suggestion chips once conversation starts
    if (suggestionsContainer) {
      suggestionsContainer.style.display = "none";
    }

    // Display user message in chat
    appendMessage("user", text);

    // Set sending state and show loading indicator
    isSending = true;
    sendBtn.disabled = true;
    messageInput.disabled = true;
    createLoadingIndicator();

    try {
      // Connect to FastAPI backend with plain-text body
      const response = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "text/plain; charset=utf-8"
        },
        body: text
      });

      if (!response.ok) {
        let errDetail = `Server responded with status ${response.status}`;
        try {
          const body = await response.text();
          if (body) {
            // Attempt to parse json detail if FastAPI returned { "detail": ... }
            try {
              const parsed = JSON.parse(body);
              if (parsed.detail) errDetail = parsed.detail;
            } catch {
              errDetail = body;
            }
          }
        } catch (_) {}

        throw new Error(errDetail);
      }

      // Backend returns plain text response
      const reply = await response.text();
      removeLoadingIndicator();
      appendMessage("assistant", reply);

    } catch (err) {
      removeLoadingIndicator();
      console.error("Chatbot request error:", err);

      let friendlyMsg = "Unable to connect to TrekBuddy backend. Please ensure your FastAPI server is running on http://127.0.0.1:8080.";
      if (err.message && !err.message.includes("Failed to fetch") && !err.message.includes("NetworkError")) {
        friendlyMsg = `Backend Error: ${err.message}`;
      }

      showError(friendlyMsg);
      appendMessage("assistant", `⚠️ **Connection Error:** ${friendlyMsg}`);
    } finally {
      isSending = false;
      sendBtn.disabled = false;
      messageInput.disabled = false;
      messageInput.focus();
      scrollToBottom();
    }
  }

  // Form submit handler
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  // Enter sends message; Shift+Enter creates new line
  messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  // Suggestion chips handler
  if (suggestionsContainer) {
    suggestionsContainer.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (chip && chip.dataset.prompt) {
        handleSendMessage(chip.dataset.prompt);
      }
    });
  }

  // Reset / Clear chat handler
  clearBtn.addEventListener("click", async () => {
    if (confirm("Reset conversation history?")) {
      try {
        await fetch(RESET_ENDPOINT, { method: "DELETE" });
      } catch (e) {
        console.warn("Could not reset backend history:", e);
      }
      // Reload UI state
      window.location.reload();
    }
  });
});
