const messageInput = document.getElementById("message-input");
const sendButton = document.querySelector(".send-btn");
const chatArea = document.querySelector(".chat-area");
const welcomeScreen = document.querySelector(".welcome-screen");
const newChatButton = document.querySelector(".new-chat-btn");

console.log("New Chat button:", newChatButton);

// Send message when button is clicked

newChatButton.addEventListener("click", newChat);

// Send message when button is clicked
sendButton.addEventListener("click", sendMessage);


// Send message when Enter is pressed
messageInput.addEventListener("keydown", function(event) {

    // Enter without Shift = send
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }

});


async function sendMessage() {

    const message = messageInput.value.trim();

    // Don't send empty messages
    if (!message) {
        return;
    }


    // Hide welcome screen
    welcomeScreen.style.display = "none";


    // Show user's message
    addMessage(message, "user");


    // Clear input
    messageInput.value = "";


    // Disable button while waiting
    sendButton.disabled = true;


    try {

        const response = await fetch("/chat", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                message: message
            })

        });


        const data = await response.json();


        if (data.response) {

            // Show Gemini's response
            addMessage(data.response, "bot");

        } else {

            addMessage(
                "Sorry, something went wrong.",
                "bot"
            );

        }


    } catch (error) {

        console.error("Error:", error);

        addMessage(
            "Unable to connect to Gemini.",
            "bot"
        );

    }


    // Enable button again
    sendButton.disabled = false;
}


function addMessage(message, sender) {

    const messageDiv = document.createElement("div");

    messageDiv.classList.add("message", sender);

    messageDiv.textContent = message;


    // Find or create message container
    let chatMessages = document.getElementById("chat-messages");


    if (!chatMessages) {

        chatMessages = document.createElement("div");

        chatMessages.id = "chat-messages";

        chatArea.insertBefore(
            chatMessages,
            document.querySelector(".input-container")
        );

    }


    chatMessages.appendChild(messageDiv);


    // Scroll to latest message
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
function newChat() {

    // Remove all previous messages
    const chatMessages = document.getElementById("chat-messages");

    if (chatMessages) {
        chatMessages.remove();
    }

    // Show welcome screen again
    welcomeScreen.style.display = "flex";

    // Clear the message box
    messageInput.value = "";

    // Put cursor back in the message box
    messageInput.focus();
}
async function loadHistory() {

    try {

        const response = await fetch("/history");

        const data = await response.json();

        const historyList = document.getElementById("history-list");

historyList.innerHTML = "";

data.conversations.forEach(function(conversation) {

    const historyItem = document.createElement("div");

    historyItem.classList.add("history-item");

    historyItem.innerHTML = `
        <span>💬</span>
        <span>${conversation[1]}</span>
    `;

    historyList.appendChild(historyItem);
});

    } catch (error) {

        console.error("Error loading chat history:", error);

    }
}

loadHistory();