// 메시지 전송 처리
const sendButton = document.getElementById("sendBtn");
const messageInput = document.getElementById("messageInput");
const messagesContainer = document.getElementById("messages");

// 메시지 전송 함수
async function sendMessage() {
        const messageText = messageInput.value.trim();
    if (messageText !== "") {
        // 사용자 메시지
        const userMessage = document.createElement("div");
        userMessage.classList.add("chat-message", "user");
        userMessage.innerHTML = `<div class="message-bubble">${messageText}</div>`;
        messagesContainer.appendChild(userMessage);
        messageInput.value = ""; // 입력창 초기화
        // 자동 스크롤
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        console.log(messageText)
        // 상대방의 답변을 자동으로 추가 (예시)
        try {
            // AI 응답 가져오기
            const config = {"configurable": {"thread_id": "2"}}
            const response = await fetch(`api/tour/agent/?query=${messageText}&user_id=1`)
            // console.log("response:", response)
            const data = await response.json();
            console.log("data:", data)
            // console.log("data.messages:", data.messages)
            // AI 응답 메시지 필터링
            // const count = data.messages.length -1; // 배열의 마지막 인덱스 계산
            // let messages = data.messages.at(-1) || [];
            // console.log("messages:", messages)
            // const aiResponseMessage = messages.find(msg => msg.role === "assistant" && msg.content);
            let messages = data.ai_response
            console.log("messages:", messages)
            if (messages) {
            // const aiMessage = aiResponseMessage.content;
            const aiMessage = messages;
            // AI 답변을 화면에 표시
            const botMessage = document.createElement("div");
            botMessage.classList.add("chat-message", "bot");
            botMessage.innerHTML = `<div class="message-bubble">${aiMessage}</div>`;
            messagesContainer.appendChild(botMessage);

            // 자동 스크롤
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            } else {
            console.error("No valid AI response found in messages.");
            }
        } catch (error) {
            console.error("Error fetching AI response:", error);

            // 에러 메시지를 화면에 표시 (선택 사항)
            const errorMessage = document.createElement("div");
            errorMessage.classList.add("chat-message", "bot");
            errorMessage.innerHTML = `<div class="message-bubble">오류가 발생했습니다. 잠시 후 다시 시도해주세요.</div>`;
            messagesContainer.appendChild(errorMessage);

            // 자동 스크롤
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
}
    

    



// Enter 키로 메시지 전송
messageInput.addEventListener("keydown", function(event) {
if (event.key === "Enter") {
    sendMessage();
}
});

// 전송 버튼 클릭 시 메시지 전송
sendButton.addEventListener("click", sendMessage);