/**
 * 🚀 VINUNI LAB 3 CLIENT LOGIC (NATIVE JAVASCRIPT & SSE CHAT STREAMING)
 */

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const btnChatbot = document.getElementById("btn-chatbot");
    const btnReact = document.getElementById("btn-react");
    const testCasesContainer = document.getElementById("test-cases-container");
    const currentModeIcon = document.getElementById("current-mode-icon");
    const currentModeTitle = document.getElementById("current-mode-title");
    const currentModeDesc = document.getElementById("current-mode-desc");
    const btnClearChat = document.getElementById("btn-clear-chat");
    const chatMessagesContainer = document.getElementById("chat-messages-container");
    const welcomeScreen = document.getElementById("welcome-screen");
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const btnSend = document.getElementById("btn-send");

    let currentMode = "chatbot"; // Default mode

    // 1. Tải và render Test Cases từ API
    async function loadTestCases() {
        try {
            const response = await fetch("/api/test-cases");
            if (!response.ok) throw new Error("Không thể tải test cases");
            const testCases = await response.json();
            
            testCasesContainer.innerHTML = ""; // Xóa loader
            
            testCases.forEach(tc => {
                const card = document.createElement("div");
                card.className = "test-case-card";
                
                // Xác định badge màu dựa trên phân loại
                let badgeClass = "simple";
                let categoryName = tc.category;
                if (tc.category.includes("Multi-step")) badgeClass = "multi-step";
                else if (tc.category.includes("Hành động")) badgeClass = "important";
                else if (tc.category.includes("Edge Case")) badgeClass = "edge-case";
                
                card.innerHTML = `
                    <div class="test-case-meta">
                        <span class="tc-id">Case #${tc.id}</span>
                        <span class="tc-badge ${badgeClass}">${categoryName}</span>
                    </div>
                    <p>${tc.question}</p>
                `;
                
                // Click test case
                card.addEventListener("click", () => {
                    chatInput.value = tc.question;
                    autoResizeTextarea();
                    btnSend.disabled = false;
                    
                    // Tự động chọn chế độ tối ưu nhất cho test case đó
                    if (tc.category.includes("Đơn giản")) {
                        switchMode("chatbot");
                    } else {
                        switchMode("react");
                    }
                    
                    chatInput.focus();
                });
                
                testCasesContainer.appendChild(card);
            });
        } catch (error) {
            console.error(error);
            testCasesContainer.innerHTML = `<div class="loader-tc text-red">⚠️ Không thể kết nối server để tải Test Cases.</div>`;
        }
    }

    // 2. Chuyển đổi chế độ hoạt động
    function switchMode(mode) {
        currentMode = mode;
        const infoBar = document.querySelector(".current-mode-info");
        
        if (mode === "chatbot") {
            btnChatbot.classList.add("active");
            btnReact.classList.remove("active");
            
            infoBar.classList.remove("react");
            currentModeIcon.textContent = "chat_bubble";
            currentModeTitle.textContent = "Chatbot Baseline Mode";
            currentModeDesc.textContent = "Mô hình phản hồi trực tiếp không truy cập kho dữ liệu đơn hàng.";
            
            chatInput.placeholder = "Hỏi bất kỳ câu hỏi nào về chính sách chung...";
        } else {
            btnChatbot.classList.remove("active");
            btnReact.classList.add("active");
            
            infoBar.classList.add("react");
            currentModeIcon.textContent = "psychology";
            currentModeTitle.textContent = "ReAct Agent Mode";
            currentModeDesc.textContent = "Hệ thống vòng lặp Thought ➔ Action ➔ Observation kết nối database để xử lý.";
            
            chatInput.placeholder = "Tra cứu đơn hàng cụ thể và kiểm tra điều kiện hoàn trả (ví dụ đơn O100091)...";
        }
    }

    btnChatbot.addEventListener("click", () => switchMode("chatbot"));
    btnReact.addEventListener("click", () => switchMode("react"));

    // 3. Xử lý khung nhập liệu (Textarea Auto-grow & Enter to Submit)
    function autoResizeTextarea() {
        chatInput.style.height = "auto";
        chatInput.style.height = (chatInput.scrollHeight - 4) + "px";
    }

    chatInput.addEventListener("input", () => {
        autoResizeTextarea();
        btnSend.disabled = chatInput.value.trim().length === 0;
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (chatInput.value.trim().length > 0) {
                submitMessage();
            }
        }
    });

    // 4. Xóa lịch sử chat
    btnClearChat.addEventListener("click", () => {
        // Giữ lại màn hình welcome
        chatMessagesContainer.innerHTML = "";
        chatMessagesContainer.appendChild(welcomeScreen);
        welcomeScreen.style.display = "block";
    });

    // Helper cuộn màn hình xuống cuối
    function scrollToBottom() {
        chatMessagesContainer.scrollTop = chatMessagesContainer.scrollHeight;
    }

    // Format text markdown cơ bản (Bullet points, bold, lines)
    function formatMarkdown(text) {
        if (!text) return "";
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        return formatted;
    }

    // 5. Gửi tin nhắn và bắt đầu Stream SSE
    function submitMessage() {
        const queryText = chatInput.value.trim();
        if (!queryText) return;

        // Ẩn welcome screen nếu đang hiển thị
        if (welcomeScreen.style.display !== "none") {
            welcomeScreen.style.display = "none";
        }

        // Tạo khung tin nhắn của User
        const userMsgDiv = document.createElement("div");
        userMsgDiv.className = "message user";
        userMsgDiv.innerHTML = `
            <div class="msg-avatar">
                <span class="material-symbols-rounded">person</span>
            </div>
            <div class="msg-bubble">
                <p>${formatMarkdown(queryText)}</p>
            </div>
        `;
        chatMessagesContainer.appendChild(userMsgDiv);
        
        // Reset input
        chatInput.value = "";
        chatInput.style.height = "auto";
        btnSend.disabled = true;
        scrollToBottom();

        // Tạo khung tin nhắn của Assistant (chưa có phản hồi)
        const assistantMsgDiv = document.createElement("div");
        assistantMsgDiv.className = `message assistant ${currentMode === "chatbot" ? "chatbot-msg" : ""}`;
        
        // Cấu trúc bong bóng phản hồi tùy theo Mode
        let avatarIcon = currentMode === "chatbot" ? "smart_toy" : "psychology";
        let innerHtml = `
            <div class="msg-avatar">
                <span class="material-symbols-rounded">${avatarIcon}</span>
            </div>
            <div class="msg-bubble">
                <div class="msg-body" id="msg-body-active">
                    <div class="loading-indicator">
                        <div class="spinner"></div>
                        <span id="loading-status">Đang suy nghĩ ...</span>
                    </div>
                </div>
            </div>
        `;
        assistantMsgDiv.innerHTML = innerHtml;
        chatMessagesContainer.appendChild(assistantMsgDiv);
        scrollToBottom();

        const activeMsgBody = document.getElementById("msg-body-active");
        activeMsgBody.removeAttribute("id"); // Xóa ID để tránh trùng lặp lần sau

        // Thiết lập EventSource kết nối SSE streaming API
        const encodedMsg = encodeURIComponent(queryText);
        const eventSource = new EventSource(`/api/chat-stream?message=${encodedMsg}&mode=${currentMode}`);

        // State biến của vòng lặp ReAct
        let reasoningBox = null;
        let reasoningStepsContainer = null;
        let currentStepDiv = null;

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("SSE Event Recieved:", data);

            // 1. Event Bắt đầu một Step của ReAct
            if (data.type === "step_start") {
                const statusSpan = assistantMsgDiv.querySelector("#loading-status");
                if (statusSpan) statusSpan.textContent = `Đang suy nghĩ (Bước ${data.step}/${data.max_steps})...`;

                // Nếu chưa tạo hộp tư duy ReAct, tiến hành tạo
                if (!reasoningBox) {
                    reasoningBox = document.createElement("div");
                    reasoningBox.className = "agent-reasoning-box";
                    reasoningBox.innerHTML = `
                        <div class="reasoning-header">
                            <span class="reasoning-title">
                                <span class="material-symbols-rounded spinner">sync</span>
                                TRÌNH SUY NGHĨ CỦA AGENT (REACT LOOP)
                            </span>
                            <span class="material-symbols-rounded reasoning-chevron">expand_more</span>
                        </div>
                        <div class="reasoning-steps"></div>
                    `;
                    
                    // Thêm sự kiện Collapse hộp tư duy
                    const header = reasoningBox.querySelector(".reasoning-header");
                    header.addEventListener("click", () => {
                        reasoningBox.classList.toggle("collapsed");
                    });

                    reasoningStepsContainer = reasoningBox.querySelector(".reasoning-steps");
                    // Insert hộp tư duy lên trên cùng bong bóng phản hồi
                    activeMsgBody.insertBefore(reasoningBox, activeMsgBody.firstChild);
                }

                // Tạo một step card mới
                currentStepDiv = document.createElement("div");
                currentStepDiv.className = "step-card";
                currentStepDiv.innerHTML = `
                    <div class="step-label">Bước ${data.step}:</div>
                    <div class="step-content">
                        <div class="loading-indicator">
                            <div class="spinner"></div>
                            <span>Đang lập luận...</span>
                        </div>
                    </div>
                `;
                reasoningStepsContainer.appendChild(currentStepDiv);
                scrollToBottom();
            }

            // 2. Event Thought từ LLM
            else if (data.type === "thought") {
                if (currentStepDiv) {
                    const stepContent = currentStepDiv.querySelector(".step-content");
                    stepContent.innerHTML = `<div class="thought-text">💭 <strong>Thought:</strong> ${formatMarkdown(data.text)}</div>`;
                } else {
                    // Cập nhật trạng thái loading cho Chatbot Mode
                    const loaderStatus = assistantMsgDiv.querySelector(".loading-indicator span");
                    if (loaderStatus) {
                        loaderStatus.textContent = data.text;
                    }
                }
            }

            // 3. Event Tool Call phát hiện được
            else if (data.type === "tool_call") {
                if (currentStepDiv) {
                    const stepContent = currentStepDiv.querySelector(".step-content");
                    // Append thông tin gọi tool
                    const toolCallDiv = document.createElement("div");
                    toolCallDiv.className = "tool-call-text";
                    let argsStr = data.args.join(", ");
                    toolCallDiv.innerHTML = `
                        <span class="material-symbols-rounded">build</span>
                        <span><strong>Action:</strong> <code>${data.tool_name}[${argsStr}]</code></span>
                    `;
                    stepContent.appendChild(toolCallDiv);
                    scrollToBottom();
                }
            }

            // 4. Event Observation (Kết quả trả về từ tool)
            else if (data.type === "observation") {
                if (currentStepDiv) {
                    const stepContent = currentStepDiv.querySelector(".step-content");
                    
                    // Tạo một box hiển thị Observation thu gọn/mở rộng được
                    const obsBox = document.createElement("div");
                    obsBox.className = "observation-box";
                    obsBox.innerHTML = `
                        <div class="observation-header">
                            <span>👁️ Observation: Kết quả thực thi</span>
                            <span class="material-symbols-rounded observation-chevron">expand_more</span>
                        </div>
                        <div class="observation-content">${data.observation}</div>
                    `;
                    
                    // Toggle collapse observation
                    const obsHeader = obsBox.querySelector(".observation-header");
                    obsHeader.addEventListener("click", () => {
                        obsBox.classList.toggle("collapsed");
                    });
                    
                    stepContent.appendChild(obsBox);
                    scrollToBottom();
                }
            }

            // 5. Event lỗi Tool Call
            else if (data.type === "tool_error") {
                if (currentStepDiv) {
                    const stepContent = currentStepDiv.querySelector(".step-content");
                    const errCard = document.createElement("div");
                    errCard.className = "guardrail-card";
                    errCard.innerHTML = `
                        <span class="material-symbols-rounded">warning</span>
                        <span>${data.error}</span>
                    `;
                    stepContent.appendChild(errCard);
                    scrollToBottom();
                }
            }

            // 6. Event vi phạm Guardrail an toàn
            else if (data.type === "guardrail") {
                eventSource.close();
                // Dọn dẹp loader
                const loader = activeMsgBody.querySelector(".loading-indicator");
                if (loader) loader.remove();
                
                // Hiển thị hộp thông báo Guardrail bị kích hoạt
                const guardrailDiv = document.createElement("div");
                guardrailDiv.className = "guardrail-card";
                guardrailDiv.innerHTML = `
                    <span class="material-symbols-rounded">gavel</span>
                    <span><strong>Guardrail Triggered:</strong> ${data.fallback}</span>
                `;
                activeMsgBody.appendChild(guardrailDiv);
                
                // Nếu ReAct Box đang xoay vòng, chuyển icon sang dừng
                if (reasoningBox) {
                    const icon = reasoningBox.querySelector(".reasoning-title .spinner");
                    if (icon) {
                        icon.className = "material-symbols-rounded text-purple";
                        icon.textContent = "gavel";
                    }
                }
                scrollToBottom();
            }

            // 7. Event Phản hồi cuối cùng (Final Answer)
            else if (data.type === "final_answer") {
                eventSource.close();
                
                // Loại bỏ loader
                const loader = activeMsgBody.querySelector(".loading-indicator");
                if (loader) loader.remove();
                
                // Hiển thị text trả lời cuối cùng
                const answerParagraph = document.createElement("p");
                answerParagraph.innerHTML = formatMarkdown(data.answer);
                activeMsgBody.appendChild(answerParagraph);
                
                // Cập nhật trạng thái Completed cho hộp ReAct
                if (reasoningBox) {
                    const icon = reasoningBox.querySelector(".reasoning-title .spinner");
                    if (icon) {
                        icon.className = "material-symbols-rounded text-purple";
                        icon.textContent = "done_all";
                    }
                    // Tự động thu nhỏ ReAct Box lại để giao diện thông thoáng
                    reasoningBox.classList.add("collapsed");
                }
                
                scrollToBottom();
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE Connection Error:", err);
            eventSource.close();
            
            const loader = activeMsgBody.querySelector(".loading-indicator");
            if (loader) loader.remove();
            
            const errorDiv = document.createElement("p");
            errorDiv.style.color = "var(--color-red)";
            errorDiv.innerHTML = "❌ <strong>Lỗi:</strong> Kết nối với máy chủ bị gián đoạn. Vui lòng kiểm tra lại server backend.";
            activeMsgBody.appendChild(errorDiv);
            scrollToBottom();
        };
    }

    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitMessage();
    });

    // Khởi chạy
    loadTestCases();
});
