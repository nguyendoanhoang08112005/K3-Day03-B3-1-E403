import http.server
import socketserver
import json
import urllib.parse
import sys
import os
import re
import ast
import inspect
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import AVAILABLE_TOOLS
from prompts import CHATBOT_BASELINE_PROMPT
from providers import get_llm_provider

# Import an toàn các biến ReAct
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

# Import helper từ app.py
from app import _is_provider_error, _parse_action, _execute_tool, DEFAULT_REACT_SYSTEM_PROMPT

if not REACT_SYSTEM_PROMPT:
    REACT_SYSTEM_PROMPT = DEFAULT_REACT_SYSTEM_PROMPT

try:
    MAX_ITERATIONS = max(1, int(MAX_ITERATIONS))
except (TypeError, ValueError):
    MAX_ITERATIONS = 5


def run_react_agent_generator(user_query: str, provider):
    """
    Generator của ReAct Agent (Thought -> Action -> Observation) trả về các event để stream qua SSE.
    """
    scratchpad = []
    executed_actions = set()

    for step in range(1, MAX_ITERATIONS + 1):
        yield {"type": "step_start", "step": step, "max_steps": MAX_ITERATIONS}
        
        trace = "\n".join(scratchpad) if scratchpad else "(chưa có)"
        prompt = (
            f"Câu hỏi người dùng: {user_query}\n\n"
            f"Trace hiện tại:\n{trace}\n\n"
            "Hãy đưa ra bước tiếp theo."
        )
        response = str(
            provider.generate(prompt, system_prompt=REACT_SYSTEM_PROMPT)
        ).strip()
        
        # Tách Thought và Action/Final Answer ra để hiển thị đẹp hơn
        thought = ""
        thought_match = re.search(r"Thought:\s*(.*?)(?=\n(?:Action|Final Answer):|$)", response, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
            yield {"type": "thought", "text": thought}
        
        if _is_provider_error(response):
            fallback = "Không thể kết nối LLM provider. Vui lòng kiểm tra cấu hình API."
            yield {"type": "final_answer", "answer": fallback}
            return

        final_match = re.search(
            r"^\s*Final Answer\s*:\s*(.+)$",
            response,
            flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        if final_match:
            final_answer = final_match.group(1).strip()
            yield {"type": "final_answer", "answer": final_answer}
            return

        try:
            action = _parse_action(response)
        except ValueError as exc:
            observation = f"LỖI: {exc}"
            yield {"type": "tool_error", "error": observation}
            scratchpad.extend((response, f"Observation: {observation}"))
            continue

        if action is None:
            # Nếu LLM không tuân thủ mẫu, cố gắng tìm dạng Action thủ công
            manual_match = re.search(r"Action:\s*(\w+)\[(.*?)\]", response)
            if manual_match:
                tool_name = manual_match.group(1).strip()
                arg_val = manual_match.group(2).strip().strip("'\" ")
                action = (tool_name, (arg_val,), {})
            else:
                observation = "LỖI: Phản hồi của Agent phải chứa đúng một Action hoặc Final Answer."
                yield {"type": "tool_error", "error": observation}
                scratchpad.extend((response, f"Observation: {observation}"))
                continue

        tool_name, args, kwargs = action
        
        # Hiển thị tool call lên UI
        yield {"type": "tool_call", "tool_name": tool_name, "args": args, "kwargs": kwargs}
        
        # Kiểm tra Whitelist
        if tool_name not in ALLOWED_TOOLS:
            observation = f"LỖI: Công cụ '{tool_name}' không nằm trong whitelist được phép sử dụng."
            yield {"type": "observation", "observation": observation}
            scratchpad.extend((response, f"Observation: {observation}"))
            continue
            
        action_key = (tool_name, repr(args), repr(sorted(kwargs.items())))
        if action_key in executed_actions:
            fallback = "Agent đã lặp lại cùng một hành động nên bị ngắt an toàn."
            yield {"type": "guardrail", "fallback": fallback}
            return

        executed_actions.add(action_key)
        observation = _execute_tool(tool_name, args, kwargs)
        
        yield {"type": "observation", "observation": observation}
        scratchpad.extend((response, f"Observation: {observation}"))

    fallback = (
        f"Agent đã đạt giới hạn {MAX_ITERATIONS} bước mà chưa có câu trả lời; "
        "vòng lặp đã được ngắt an toàn."
    )
    yield {"type": "guardrail", "fallback": fallback}


class LocalHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Native Python Web Server hỗ trợ static files và stream chat API"""
    
    def translate_path(self, path):
        # Trỏ static files vào thư mục src/static
        root = os.path.dirname(os.path.abspath(__file__))
        static_dir = os.path.join(root, "static")
        
        # Clean path
        parsed_url = urllib.parse.urlparse(path)
        clean_path = parsed_url.path
        
        if clean_path == "/" or clean_path == "":
            clean_path = "/index.html"
            
        # Nối với static dir
        target = os.path.join(static_dir, clean_path.lstrip("/"))
        return target

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        
        # API trả về Test Cases từ file JSON
        if path == "/api/test-cases":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(root_dir, "config", "test_cases.json")
            if not os.path.exists(config_path):
                config_path = "test_cases.json"
                
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps([{"id": 1, "category": "Error", "question": f"Lỗi đọc test cases: {str(e)}"}], ensure_ascii=False).encode("utf-8"))
            return
            
        # API stream chat dạng Server-Sent Events (SSE)
        elif path == "/api/chat-stream":
            user_message = query.get("message", [""])[0]
            mode = query.get("mode", ["chatbot"])[0]
            
            if not user_message:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing message parameter")
                return
                
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            provider = get_llm_provider()
            
            if mode == "chatbot":
                # Baseline Chatbot
                try:
                    self.send_event({"type": "thought", "text": "Đang phân tích câu trả lời bằng Chatbot..."})
                    response = provider.generate(user_message, system_prompt=CHATBOT_BASELINE_PROMPT)
                    
                    if _is_provider_error(response):
                        self.send_event({"type": "final_answer", "answer": f"Lỗi LLM: {response}"})
                    else:
                        self.send_event({"type": "final_answer", "answer": response})
                except Exception as e:
                    self.send_event({"type": "final_answer", "answer": f"Exception occurred: {str(e)}"})
            else:
                # ReAct Agent
                try:
                    for event in run_react_agent_generator(user_message, provider):
                        self.send_event(event)
                except Exception as e:
                    self.send_event({"type": "final_answer", "answer": f"ReAct Exception occurred: {str(e)}"})
            return
            
        # Phục vụ static files bình thường
        super().do_GET()

    def send_event(self, data):
        """Helper gửi data SSE dạng JSON"""
        try:
            payload = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()
        except Exception:
            pass # Client disconnected


def run_server(port=8000):
    handler = LocalHTTPRequestHandler
    # Đăng ký handler hỗ trợ UTF-8
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"\n==================================================")
        print(f"🚀 VINUNI LAB 3 WEB SERVER ĐANG CHẠY...")
        print(f"🔗 Mở trình duyệt tại: http://localhost:{port}")
        print(f"==================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
