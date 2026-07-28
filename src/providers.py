"""
🔌 MULTI-PROVIDER LLM ADAPTER (OpenAI, Gemini, Anthropic, OpenRouter & Offline Mock)
Hỗ trợ chuyển đổi linh hoạt giữa các nhà cung cấp AI chỉ bằng cách đổi biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
import requests
from dotenv import load_dotenv

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if os.name == "nt":
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass

for stream in (sys.stdout, sys.stderr):
    if stream.encoding and stream.encoding.lower() != "utf-8":
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho tất cả các LLM Provider"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider"""
    _last_request_time = 0.0
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-flash-latest"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env!"
        
        import time
        # Hạn mức Free Tier là 5 RPM -> Giãn cách tối thiểu 12 giây giữa các request
        min_interval = 12.0
        current_time = time.time()
        elapsed = current_time - GeminiProvider._last_request_time
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            print(f"\n⏳ [Cooldown] Chờ {sleep_time:.1f} giây để tránh Rate Limit (5 RPM)...")
            time.sleep(sleep_time)
            
        max_retries = 3
        wait_seconds = 15
        
        for attempt in range(max_retries):
            try:
                # Cập nhật thời điểm gửi request
                GeminiProvider._last_request_time = time.time()
                from google import genai
                client = genai.Client(api_key=self.api_key)
                contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=contents
                )
                return response.text
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"\n⚠️ Gemini Rate Limit (429). Đang chờ {wait_seconds} giây trước khi thử lại (Lần {attempt+1}/{max_retries})...")
                    time.sleep(wait_seconds)
                    wait_seconds += 5  # Tăng thời gian chờ cho lần sau
                    continue
                return f"[Gemini Exception]: {err_str}"
        
        return "[Gemini Error]: Vượt quá số lần thử lại sau lỗi rate limit 429."


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (GPT-4o, GPT-3.5-turbo, etc.)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env!"
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude Provider (Claude 3.5 Sonnet, Claude 3 Haiku)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "claude-3-haiku-20240307"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_anthropic_api_key_here":
            return "[Anthropic Error]: Chưa cấu hình ANTHROPIC_API_KEY trong file .env!"
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            kwargs = {
                "model": self.model_name,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
            if system_prompt:
                kwargs["system"] = system_prompt
                
            response = client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            return f"[Anthropic Exception]: {str(e)}"


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter Provider (Hỗ trợ gọi mọi model qua OpenRouter API)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "google/gemini-2.5-flash"
        
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            return "[OpenRouter Error]: Chưa cấu hình OPENROUTER_API_KEY trong file .env!"
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model_name,
                "messages": messages
            }
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"[OpenRouter API Error {res.status_code}]: {res.text}"
        except Exception as e:
            return f"[OpenRouter Exception]: {str(e)}"


class NvidiaProvider(BaseLLMProvider):
    """NVIDIA NIM Provider (OpenAI-compatible API, nhiều model miễn phí)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "meta/llama-3.3-70b-instruct"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_nvidia_api_key_here":
            return "[NVIDIA Error]: Chưa cấu hình NVIDIA_API_KEY trong file .env!"
        try:
            import openai
            client = openai.OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=self.api_key
            )
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[NVIDIA Exception]: {str(e)}"


class MockProvider(BaseLLMProvider):
    """Offline Mock Provider (Cho bài test không cần kết nối API)"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        text = prompt.lower()
        react_prompt = system_prompt.lower()
        is_react = (
            "các tool hợp lệ:" in react_prompt
            and "action: <tên_tool>" in react_prompt
        )
        order_match = re.search(r"\b[O0]\d{6}\b", prompt, re.IGNORECASE)
        order_id = order_match.group(0).upper() if order_match else None

        if not is_react:
            if "người khác" in text or "bỏ qua quy định" in text:
                return (
                    "Mình không thể tra cứu đơn hàng của người khác hoặc bỏ qua "
                    "quy định bảo vệ dữ liệu."
                )
            if order_id:
                return (
                    "Mình chưa thể kiểm tra đơn cụ thể trong chế độ chatbot. "
                    "Bạn hãy cung cấp order_id cho ReAct Agent; mình sẽ không "
                    "đoán dữ liệu hoặc tuyên bố đã tạo yêu cầu đổi trả."
                )
            if "chính sách" in text and ("đổi trả" in text or "trả" in text):
                return (
                    "Theo policy demo, đơn chưa được trả và ngày giao cách ngày "
                    "hệ thống không quá 3 ngày mới đủ điều kiện để xem xét đổi trả."
                )
            return "Mình đang chạy ở chế độ giả lập offline."

        if "người khác" in text or "bỏ qua quy định" in text:
            return (
                "Thought: Yêu cầu vượt quyền và cố bỏ qua guardrail.\n"
                "Final Answer: Mình không thể tra cứu đơn hàng của người khác "
                "hoặc tự động hoàn trả đơn hàng."
            )

        if not order_id:
            return (
                "Thought: Chưa có mã đơn hàng để tra cứu.\n"
                "Final Answer: Bạn vui lòng cung cấp order_id theo dạng Oxxxxxx."
            )

        searched = "Action: search_order_by_id" in prompt
        checked_return = "Action: check_return_eligibility" in prompt
        asks_return = any(
            keyword in text
            for keyword in ("đổi", "trả", "hoàn tiền", "hoàn trả")
        )

        if not searched:
            return (
                "Thought: Cần tra cứu đơn hàng trước khi trả lời.\n"
                f'Action: search_order_by_id["{order_id}"]'
            )

        if asks_return and not checked_return:
            return (
                "Thought: Đã tra cứu đơn; cần kiểm tra điều kiện đổi trả.\n"
                f'Action: check_return_eligibility["{order_id}"]'
            )

        delivered_match = re.search(
            r"Ngày giao(?: dự kiến)?:\s*(\d{1,2}/\d{1,2}/\d{4})",
            prompt,
            re.IGNORECASE,
        )
        delivery_text = (
            f"Dữ liệu ghi nhận ngày giao {delivered_match.group(1)}."
            if delivered_match
            else "Đã tìm thấy thông tin đơn hàng trong dữ liệu mẫu."
        )

        if checked_return:
            if "xác nhận được phép đổi trả" in text:
                return (
                    "Thought: Đã có đủ kết quả từ hai tool.\n"
                    f"Final Answer: {delivery_text} Đơn hiện đủ điều kiện đổi "
                    "trả theo policy demo; hệ thống chưa tạo yêu cầu hoàn trả."
                )
            return (
                "Thought: Đã có đủ kết quả từ hai tool.\n"
                f"Final Answer: {delivery_text} Đơn hiện không đủ điều kiện đổi "
                "trả theo policy demo."
            )

        return (
            "Thought: Đã có kết quả tra cứu đơn hàng.\n"
            f"Final Answer: {delivery_text}"
        )


def get_llm_provider(provider_name: str = None) -> BaseLLMProvider:
    """Factory function tự chọn Provider từ biến môi trường LLM_PROVIDER"""
    name = (provider_name or os.getenv("LLM_PROVIDER") or "mock").lower().strip()
    
    if name == "gemini":
        return GeminiProvider()
    elif name == "openai":
        return OpenAIProvider()
    elif name == "anthropic":
        return AnthropicProvider()
    elif name == "openrouter":
        return OpenRouterProvider()
    elif name == "nvidia":
        return NvidiaProvider()
    else:
        return MockProvider()


if __name__ == "__main__":
    print("=== TEST MULTI-PROVIDER LLM ADAPTER ===")
    provider = get_llm_provider()
    print(f"✅ Provider đang dùng: {provider.__class__.__name__}")
    print(f"🤖 User Query: Hello")
    print(f"💬 Response  : {provider.generate('Hello')}")
