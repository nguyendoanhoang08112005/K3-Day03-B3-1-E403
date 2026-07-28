"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import sys
import re
import inspect
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import AVAILABLE_TOOLS
from prompts import CHATBOT_BASELINE_PROMPT
from providers import get_llm_provider

# Import an toàn các biến ReAct (sẽ được Role 3 bổ sung ở Mốc 3)
try:
    from prompts import REACT_SYSTEM_PROMPT
except ImportError:
    REACT_SYSTEM_PROMPT = ""

try:
    from prompts import MAX_ITERATIONS
except ImportError:
    MAX_ITERATIONS = 5

try:
    from prompts import ALLOWED_TOOLS
except ImportError:
    ALLOWED_TOOLS = {"search_order_by_id", "check_return_eligibility"}

load_dotenv()

def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")
    
    # Gọi LLM Provider thực hiện sinh câu trả lời
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")
    print("-" * 50)


def parse_action(llm_output: str):
    """
    Trích xuất Action từ LLM Output.
    Định dạng mong muốn: Action: tên_công_cụ['tham_số'] hoặc Action: tên_công_cụ[tham_số]
    Ví dụ: Action: search_order_by_id['O100009']
    """
    match = re.search(r"Action:\s*(\w+)\[(.*?)\]", llm_output)
    if match:
        tool_name = match.group(1).strip()
        arg_val = match.group(2).strip().strip("'\" ")
        return tool_name, [arg_val] if arg_val else []
    return None, None


def execute_tool(tool_name: str, args: list) -> str:
    """
    Thực thi công cụ thực tế từ AVAILABLE_TOOLS.
    """
    if tool_name not in AVAILABLE_TOOLS:
        return f"LỖI: Công cụ '{tool_name}' không tồn tại. Các công cụ hợp lệ: {list(AVAILABLE_TOOLS.keys())}"
    
    if not args:
        return f"LỖI: Thiếu tham số cho công cụ '{tool_name}'."
        
    tool_func = AVAILABLE_TOOLS[tool_name]
    try:
        # Kiểm tra chữ ký hàm của tool để lấy số tham số
        sig = inspect.signature(tool_func)
        params = list(sig.parameters.keys())
        
        if len(args) != len(params):
            return f"LỖI: Công cụ '{tool_name}' yêu cầu {len(params)} tham số. Bạn đã truyền {len(args)} tham số: {args}."
        
        # Thực thi hàm
        return tool_func(*args)
    except Exception as e:
        return f"LỖI thực thi công cụ '{tool_name}': {str(e)}"


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    # Khởi tạo ngữ cảnh hội thoại với câu hỏi của User
    conversation_history = f"Question: {user_query}\n"
    
    step = 0
    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Gọi LLM sinh phản hồi tiếp theo dựa trên lịch sử hoạt động
        llm_response = provider.generate(conversation_history, system_prompt=REACT_SYSTEM_PROMPT)
        
        # In kết quả sinh của LLM (Thought + Action/Final Answer)
        print(f"🤖 Phản hồi của Agent:\n{llm_response.strip()}")
        
        # Ghi nhận phản hồi của LLM vào lịch sử hội thoại
        conversation_history += f"\n{llm_response.strip()}"
        
        # 1. Kiểm tra xem Agent đã đưa ra Final Answer chưa
        if "Final Answer:" in llm_response:
            match_final = re.search(r"Final Answer:\s*(.*)", llm_response, re.DOTALL)
            final_ans = match_final.group(1).strip() if match_final else llm_response
            print(f"\n🏁 Final Answer: {final_ans}")
            break
            
        # 2. Phân tích Action của Agent để gọi Tool
        tool_name, args = parse_action(llm_response)
        
        if tool_name:
            # Kiểm tra xem tool có thuộc danh sách được phép không
            if tool_name not in ALLOWED_TOOLS:
                observation = f"LỖI: Công cụ '{tool_name}' không nằm trong whitelist được phép sử dụng."
                print(f"⚠️ {observation}")
            else:
                print(f"⚙️ Thực thi: Gọi tool '{tool_name}' với tham số {args}")
                observation = execute_tool(tool_name, args)
                print(f"👁️ Observation: {observation}")
            
            # Ghi nhận kết quả Observation vào lịch sử
            conversation_history += f"\nObservation: {observation}"
        else:
            # Fallback nếu LLM sinh phản hồi không chứa Action hay Final Answer
            err_msg = "LỖI: Định dạng phản hồi không hợp lệ. Vui lòng sử dụng cấu trúc: Thought:... Action: tool_name['arg'] hoặc Thought:... Final Answer:..."
            print(f"⚠️ {err_msg}")
            conversation_history += f"\nObservation: {err_msg}"
            
    if step >= MAX_ITERATIONS:
        print(f"\n🛡️ GUARDRAIL TRIGGERED: Đạt giới hạn tối đa {MAX_ITERATIONS} bước lặp. Ngắt lặp an toàn!")
    print("-" * 50)


if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")
    
    import time
    
    print("--- DEMO 1: CHẠY BỘ TEST CASES TRÊN CHATBOT BASELINE ---")
    for test in tests:
        print(f"\nCase #{test['id']} [{test['category']}]")
        run_baseline_chatbot(test["question"], provider)
        time.sleep(2)  # Giãn cách 2 giây tránh lỗi Rate Limit 429
        
    print("\n--- DEMO 2: CHẠY BỘ TEST CASES TRÊN REACT AGENT (MỐC 3) ---")
    for test in tests:
        print(f"\nCase #{test['id']} [{test['category']}]")
        run_react_agent(test["question"], provider)
        time.sleep(2)  # Giãn cách 2 giây tránh lỗi Rate Limit 429
