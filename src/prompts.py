"""
🧠 PROMPTS & SAFEGUARDS — Role 3: Prompt Engineer

Domain: Trợ Lý Tra Cứu Đơn Hàng & Xử Lý Đổi Trả.
Compatibility target: src/tools.py trên branch `tamtc`.

Role boundaries:
- Role 2 cung cấp hai read-only tools và trả về plain text.
- Role 3 định nghĩa prompt contract, failure modes và guardrails.
- Role 4 phải parse Action, thực thi tool, nối Observation vào scratchpad và
  cưỡng chế giới hạn vòng lặp ở tầng code.
- Role 1 dùng failure modes để tạo test cases.
- Role 5 audit trace Thought -> Action -> Observation -> Final Answer.
"""

from typing import Final


# ---------------------------------------------------------------------------
# DATASET PROFILE — kiểm tra trực tiếp từ CSV trên branch tamtc
# ---------------------------------------------------------------------------
DATASET_NAME: Final[str] = "Kaggle_Ecommerce Data.csv"
DATASET_MODE: Final[str] = "synthetic_static_csv"
DATASET_TOTAL_ROWS: Final[int] = 34_500
DATASET_TOTAL_COLUMNS: Final[int] = 19
ORDER_ID_IS_UNIQUE: Final[bool] = True
RETURNED_YES_COUNT: Final[int] = 1_903
RETURNED_NO_COUNT: Final[int] = 32_597
DATASET_MAX_DELIVERED_DATE: Final[str] = "2026-07-28"

CONFIRMED_DATASET_COLUMNS: Final[tuple[str, ...]] = (
    "order_id",
    "customer_id",
    "product_id",
    "category",
    "price",
    "discount",
    "quantity",
    "payment_method",
    "order_date",
    "delivered_date",
    "region",
    "returned",
    "request_date",
    "return_reason",
    "total_amount",
    "shipping_cost",
    "profit_margin",
    "customer_age",
    "customer_gender",
)

DATASET_BOUNDARIES: Final[tuple[str, ...]] = (
    "Dataset là dữ liệu synthetic phục vụ lab, không phải hệ thống order production.",
    "CSV là snapshot tĩnh; dữ liệu không chứng minh trạng thái giao hàng real-time.",
    "Mỗi order_id trong file hiện tại là duy nhất và ánh xạ tới đúng một product_id.",
    "Dataset không có cột currency; ký hiệu $ trong tool chỉ là định dạng demo.",
    "Có dữ liệu lịch sử không nhất quán; không được biến mọi field thành fact nghiệp vụ đáng tin tuyệt đối.",
    "Tool hiện tại chỉ đọc và kiểm tra eligibility; không có tool tạo/cập nhật return request.",
)

KNOWN_DATA_QUALITY_WARNINGS: Final[tuple[str, ...]] = (
    "Ít nhất một bản ghi có request_date xảy ra trước order_date/delivered_date.",
    "Phần lớn returned='Yes' có request_date cách delivered_date quá 3 ngày, không nhất quán với policy demo 3 ngày.",
    "request_date và return_reason trống ở các dòng returned='No'; đây là missing có điều kiện, không phải lỗi parse.",
)


# ---------------------------------------------------------------------------
# ACTUAL ROLE 2 TOOL CONTRACT — branch tamtc
# ---------------------------------------------------------------------------
TOOL_CONTRACTS: Final[tuple[str, ...]] = (
    "search_order_by_id[order_id]: Tra đúng một order_id và trả plain-text order snapshot.",
    "check_return_eligibility[order_id]: Kiểm tra policy demo 3 ngày và trạng thái returned trong CSV; trả plain text.",
)

ALLOWED_TOOLS: Final[frozenset[str]] = frozenset(
    {"search_order_by_id", "check_return_eligibility"}
)
MUTATING_TOOLS: Final[frozenset[str]] = frozenset()
WRITE_ACTION_SUPPORTED: Final[bool] = False

# Chính sách đúng theo code Role 2, không phải cam kết production.
DEMO_RETURN_POLICY: Final[str] = (
    "Đơn chưa có returned='Yes' và delivered_date cách ngày hệ thống không quá 3 ngày."
)


# ---------------------------------------------------------------------------
# MỐC 1 — FAILURE MODES
# ---------------------------------------------------------------------------
TOOL_FAILURE_MODES: Final[tuple[str, ...]] = (
    "Thiếu order_id hoặc order_id không đúng định dạng Oxxxxxx.",
    "Tên tool/signature trong prompt không khớp AVAILABLE_TOOLS của Role 2.",
    "CSV không tồn tại nhưng _load_orders_data trả [], khiến lỗi file bị hiểu nhầm thành order không tồn tại.",
    "CSV đổi schema, encoding hoặc tên file làm tool trả dữ liệu thiếu/sai.",
    "Tool trả plain text thay vì object có schema, khiến Role 4 phải parse output dễ vỡ.",
    "Giá trị numeric/date lỗi bị thay bằng 0 hoặc chuỗi LỖI, làm mất nguyên nhân gốc.",
    "Agent gọi search_order_by_id lặp lại với cùng order_id sau cùng một Observation.",
    "Agent gọi check_return_eligibility trước khi xác minh order bằng search_order_by_id.",
    "Agent gọi tool khi câu hỏi chỉ hỏi policy chung và không cần dữ liệu order.",
    "Agent gọi dữ liệu snapshot là trạng thái vận chuyển hiện tại hoặc tracking real-time.",
    "Agent gọi delivered_date là ngày giao dự kiến hiện tại dù đây chỉ là field lịch sử trong CSV.",
    "Agent khẳng định currency là USD chỉ vì Role 2 hard-code ký hiệu $.",
    "Agent tiết lộ customer_age, customer_gender hoặc profit_margin không cần thiết cho người dùng.",
    "Agent tiết lộ nguyên customer_id thay vì mask khi tóm tắt.",
    "Agent tin một chronology bất thường như request_date trước order_date mà không cảnh báo data quality.",
    "Agent tuyên bố đã tạo/cập nhật return request dù không tồn tại write tool.",
    "Agent suy diễn số tiền refund, fee, carrier hoặc request_id không có trong Observation.",
    "Prompt injection nằm trong câu người dùng hoặc nội dung Observation/tool output.",
    "Agent không dừng khi Observation bắt đầu bằng LỖI:.",
    "ReAct loop vượt MAX_ITERATIONS hoặc Role 4 không chặn action ngoài whitelist.",
)


