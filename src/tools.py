"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)

Mô-đun này chứa các công cụ (tools) phục vụ cho hệ thống ReAct Agent trong
việc tra cứu thông tin đơn hàng và xử lý yêu cầu đổi trả hàng hóa.

Các tools được cung cấp:
    - search_order_by_id: Tra cứu thông tin chi tiết đơn hàng theo mã
    - check_return_eligibility: Kiểm tra điều kiện đổi trả của đơn hàng

Nguồn dữ liệu: Kaggle_Ecommerce Data.csv

Example:
    >>> from src.tools import search_order_by_id, check_return_eligibility
    >>> result = search_order_by_id("O100001")
    >>> eligibility = check_return_eligibility("O100001")
"""

import csv
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Đường dẫn đến dataset
DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "Kaggle_Ecommerce Data.csv")

# Thời hạn đổi trả (ngày)
RETURN_WINDOW_DAYS: int = 3


def _load_orders_data() -> List[Dict[str, str]]:
    """
    Đọc toàn bộ dữ liệu đơn hàng từ file CSV.

    Hàm nội bộ (private) phục vụ việc đọc và cache dữ liệu từ file
    Kaggle_Ecommerce Data.csv. Kết quả được trả về dưới dạng danh sách
    các dictionary, mỗi dictionary đại diện cho một đơn hàng.

    Returns:
        List[Dict[str, str]]: Danh sách các đơn hàng, mỗi phần tử là dict
            với keys tương ứng tên cột trong file CSV.
            Trả về list rỗng nếu file không tồn tại hoặc có lỗi đọc.

    Raises:
        FileNotFoundError: Nếu file CSV không tồn tại tại đường dẫn DATASET_PATH.
        csv.Error: Nếu có lỗi khi parse file CSV.

    Example:
        >>> orders = _load_orders_data()
        >>> print(f"Tổng số đơn hàng: {len(orders)}")
        Tổng số đơn hàng: 18642
    """
    orders: List[Dict[str, str]] = []
    try:
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                orders.append(row)
    except FileNotFoundError:
        return []
    return orders


def _parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse chuỗi ngày tháng với định dạng DD/MM/YYYY.

    Hàm nội bộ (private) hỗ trợ việc chuyển đổi chuỗi ngày tháng
    từ format "DD/MM/YYYY" sang đối tượng datetime.

    Args:
        date_str (str): Chuỗi ngày tháng cần parse.
            Ví dụ: "28/07/2026"

    Returns:
        Optional[datetime]: Đối tượng datetime nếu parse thành công,
            None nếu định dạng không hợp lệ.

    Example:
        >>> _parse_date("28/07/2026")
        datetime.datetime(2026, 7, 28, 0, 0)
        >>> _parse_date("invalid")
        None
    """
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except (ValueError, TypeError):
        return None


def search_order_by_id(order_id: str) -> str:
    """
    Tra cứu thông tin chi tiết của một đơn hàng theo mã đơn hàng.

    Hàm này tìm kiếm và trả về toàn bộ thông tin liên quan đến đơn hàng
    được chỉ định, bao gồm thông tin sản phẩm, thanh toán, vận chuyển
    và trạng thái đổi trả (nếu có).

    Args:
        order_id (str): Mã đơn hàng cần tra cứu.
            - Không phân biệt hoa thường (sẽ được chuyển thành uppercase).
            - Ví dụ: 'O100001', 'o100001', 'O100000'

    Returns:
        str: Chuỗi chứa thông tin chi tiết đơn hàng được format đẹp,
            bao gồm:
            - Thông tin đơn hàng: Mã đơn, mã khách hàng
            - Thông tin sản phẩm: Mã SP, danh mục, đơn giá, số lượng,
              giảm giá, thành tiền, phí vận chuyển, lợi nhuận
            - Thông tin giao hàng: Ngày đặt, ngày giao dự kiến
            - Thông tin thanh toán: Phương thức thanh toán, khu vực
            - Thông tin khách hàng: Tuổi, giới tính
            - Trạng thái đổi trả: Đã yêu cầu/CHưa yêu cầu, lý do (nếu có)

            Trả về chuỗi lỗi nếu không tìm thấy đơn hàng.

    Raises:
        Không raise exception. Các lỗi được xử lý nội bộ và trả về
        chuỗi thông báo lỗi.

    Example:
        >>> result = search_order_by_id("O100000")
        >>> print(result)
        📦 THÔNG TIN ĐƠN HÀNG
        ===============================================
        🆔 Mã đơn hàng: O100000
        ...

    See Also:
        check_return_eligibility: Kiểm tra điều kiện đổi trả của đơn hàng.
    """
    orders = _load_orders_data()
    order_id_upper = order_id.upper()

    for order in orders:
        if order.get("order_id", "").upper() == order_id_upper:
            # Parse dữ liệu số
            try:
                price = float(order.get("price", 0))
                discount = float(order.get("discount", 0))
                quantity = int(order.get("quantity", 0))
                total_amount = float(order.get("total_amount", 0))
                shipping_cost = float(order.get("shipping_cost", 0))
                profit_margin = float(order.get("profit_margin", 0))
            except (ValueError, ZeroDivisionError):
                price = discount = quantity = total_amount = shipping_cost = profit_margin = 0.0

            result = f"""
📦 THÔNG TIN ĐƠN HÀNG
{'='*55}
🆔 Mã đơn hàng: {order.get('order_id', 'N/A')}
👤 Mã khách hàng: {order.get('customer_id', 'N/A')}

📅 NGÀY ĐẶT & GIAO HÀNG:
   - Ngày đặt: {order.get('order_date', 'N/A')}
   - Ngày giao dự kiến: {order.get('delivered_date', 'N/A')}

🏷️ THÔNG TIN SẢN PHẨM:
   - Mã sản phẩm: {order.get('product_id', 'N/A')}
   - Danh mục: {order.get('category', 'N/A')}
   - Đơn giá: ${price:,.2f}
   - Số lượng: {quantity}
   - Giảm giá: {discount*100:.0f}%
   - Thành tiền: ${total_amount:,.2f}
   - Phí vận chuyển: ${shipping_cost:,.2f}
   - Lợi nhuận: ${profit_margin:,.2f}

💳 THANH TOÁN & VẬN CHUYỂN:
   - Phương thức thanh toán: {order.get('payment_method', 'N/A')}
   - Khu vực: {order.get('region', 'N/A')}

👤 THÔNG TIN KHÁCH HÀNG:
   - Tuổi: {order.get('customer_age', 'N/A')}
   - Giới tính: {order.get('customer_gender', 'N/A')}
{'='*55}
"""
            # Thêm thông tin đổi trả nếu có
            returned = order.get("returned", "No")
            if returned.lower() == "yes":
                result += f"""
🔄 TRẠNG THÁI ĐỔI TRẢ:
   - Đã yêu cầu đổi trả
   - Ngày yêu cầu: {order.get('request_date', 'N/A')}
   - Lý do: {order.get('return_reason', 'N/A')}
"""
            else:
                result += """
🔄 TRẠNG THÁI ĐỔI TRẢ: Chưa yêu cầu đổi trả
"""
            return result

    return f"LỖI: Không tìm thấy đơn hàng với mã '{order_id}'"


def check_return_eligibility(order_id: str) -> str:
    """
    Kiểm tra đơn hàng có đủ điều kiện đổi trả hay không.

    Hàm này xác định xem một đơn hàng có được phép đổi trả hay không
    dựa trên chính sách đổi trả: Khách hàng được đổi trả trong vòng
    3 ngày kể từ ngày giao hàng (delivered_date).

    Logic kiểm tra:
        1. Tìm đơn hàng theo mã đơn hàng
        2. Parse delivered_date từ đơn hàng
        3. Tính số ngày kể từ ngày giao đến hiện tại
        4. Kiểm tra các điều kiện:
           - Đã được đổi trả chưa?
           - Còn trong thời hạn 3 ngày không?
           - Đã quá hạn bao lâu?

    Args:
        order_id (str): Mã đơn hàng cần kiểm tra điều kiện đổi trả.
            - Không phân biệt hoa thường.
            - Ví dụ: 'O100001', 'O100000'

    Returns:
        str: Kết quả kiểm tra được format đẹp, gồm:

        **THÀNH CÔNG (<= 3 ngày):**
            - Mã đơn hàng, mã khách hàng
            - Thông tin giao hàng: Ngày giao, số ngày đã qua, số ngày còn lại
            - Chi tiết sản phẩm: Mã SP, danh mục, đơn giá, số lượng, thành tiền
            - Thông tin thanh toán
            - Hướng dẫn đổi trả

        **QUÁ HẠN (> 3 ngày):**
            - Mã đơn hàng, mã khách hàng
            - Thông tin giao hàng
            - Thông báo quá hạn với số ngày quá hạn
            - Chi tiết đơn hàng (tham khảo)
            - Thông tin hỗ trợ

        **ĐÃ ĐỔI TRẢ:**
            - Thông báo đơn đã được yêu cầu đổi trả
            - Ngày yêu cầu và lý do

        **LỖI:**
            - Chuỗi thông báo lỗi nếu không tìm thấy đơn hàng
              hoặc định dạng ngày không hợp lệ

    Raises:
        Không raise exception. Các lỗi được xử lý nội bộ.

    Example:
        >>> result = check_return_eligibility("O100000")
        >>> print(result)
        ✅ XÁC NHẬN ĐƯỢC PHÉP ĐỔI TRẢ
        ===============================================
        ...

    Note:
        - Chính sách đổi trả: 3 ngày kể từ ngày giao hàng
        - Ngày hiện tại được tính bằng datetime.now()
        - Đơn đã đổi trả sẽ không được phép đổi trả lần hai

    See Also:
        search_order_by_id: Tra cứu thông tin chi tiết đơn hàng.
    """
    orders = _load_orders_data()
    order_id_upper = order_id.upper()

    for order in orders:
        if order.get("order_id", "").upper() == order_id_upper:
            # Parse delivered_date
            delivered_date_str = order.get("delivered_date", "")
            delivered_date = _parse_date(delivered_date_str)

            if delivered_date is None:
                return (
                    f"LỖI: Định dạng ngày giao hàng không hợp lệ "
                    f"trong đơn hàng '{order_id}'. "
                    f"Ngày: '{delivered_date_str}'"
                )

            # Tính số ngày kể từ ngày giao hàng đến hiện tại
            today = datetime.now()
            days_since_delivery = (today - delivered_date).days

            # Parse thông tin đơn hàng
            try:
                price = float(order.get("price", 0))
                discount = float(order.get("discount", 0))
                quantity = int(order.get("quantity", 0))
                total_amount = float(order.get("total_amount", 0))
            except (ValueError, ZeroDivisionError):
                price = discount = quantity = total_amount = 0.0

            # Kiểm tra đã được đổi trả chưa
            if order.get("returned", "No").lower() == "yes":
                return f"""
❌ KHÔNG THỂ ĐỔI TRẢ
{'='*55}
🆔 Mã đơn hàng: {order.get('order_id', 'N/A')}

⚠️ Đơn hàng này đã được yêu cầu đổi trả trước đó.
   Ngày yêu cầu: {order.get('request_date', 'N/A')}
   Lý do: {order.get('return_reason', 'N/A')}
"""

            # Kiểm tra điều kiện đổi trả
            if days_since_delivery <= RETURN_WINDOW_DAYS:
                # Đủ điều kiện đổi trả
                remaining_days = RETURN_WINDOW_DAYS - days_since_delivery
                return f"""
✅ XÁC NHẬN ĐƯỢC PHÉP ĐỔI TRẢ
{'='*55}
🆔 Mã đơn hàng: {order.get('order_id', 'N/A')}
👤 Mã khách hàng: {order.get('customer_id', 'N/A')}

📅 THÔNG TIN GIAO HÀNG:
   - Ngày giao: {order.get('delivered_date', 'N/A')}
   - Số ngày kể từ khi giao: {days_since_delivery} ngày
   - Còn lại: {remaining_days} ngày để yêu cầu đổi trả

🏷️ CHI TIẾT SẢN PHẨM:
   - Mã sản phẩm: {order.get('product_id', 'N/A')}
   - Danh mục: {order.get('category', 'N/A')}
   - Đơn giá: ${price:,.2f}
   - Số lượng: {quantity}
   - Giảm giá: {discount*100:.0f}%
   - Thành tiền: ${total_amount:,.2f}

💳 THANH TOÁN:
   - Phương thức: {order.get('payment_method', 'N/A')}

📋 HƯỚNG DẪN ĐỔI TRẢ:
   Quý khách vui lòng liên hệ bộ phận chăm sóc khách hàng
   hoặc thực hiện yêu cầu đổi trả trong {remaining_days} ngày tới.
{'='*55}
"""
            else:
                # Quá hạn đổi trả
                days_overdue = days_since_delivery - RETURN_WINDOW_DAYS
                return f"""
❌ KHÔNG THỂ ĐỔI TRẢ - QUÁ HẠN
{'='*55}
🆔 Mã đơn hàng: {order.get('order_id', 'N/A')}
👤 Mã khách hàng: {order.get('customer_id', 'N/A')}

📅 THÔNG TIN GIAO HÀNG:
   - Ngày giao: {order.get('delivered_date', 'N/A')}
   - Số ngày kể từ khi giao: {days_since_delivery} ngày

⚠️ THÔNG BÁO:
   Đơn hàng của quý khách đã quá hạn đổi trả.
   Thời hạn đổi trả là {RETURN_WINDOW_DAYS} ngày kể từ ngày giao hàng.
   Quý khách đã quá hạn {days_overdue} ngày.

🏷️ CHI TIẾT ĐƠN HÀNG (THAM KHẢO):
   - Sản phẩm: {order.get('category', 'N/A')} ({order.get('product_id', 'N/A')})
   - Số lượng: {quantity}
   - Thành tiền: ${total_amount:,.2f}

📞 HỖ TRỢ:
   Nếu có thắc mắc, vui lòng liên hệ bộ phận chăm sóc khách hàng.
{'='*55}
"""

    return f"LỖI: Không tìm thấy đơn hàng với mã '{order_id}'"


# =============================================================================
# TOOL REGISTRY - Danh sách các tools được đăng ký cho ReAct Agent
# =============================================================================

AVAILABLE_TOOLS: Dict[str, callable] = {
    "search_order_by_id": search_order_by_id,
    "check_return_eligibility": check_return_eligibility,
}

"""
Đăng ký các tools để ReAct Agent có thể gọi.

Mỗi tool được định nghĩa bởi:
    - Tên tool (key): Tên duy nhất để Agent gọi
    - Hàm xử lý (value): Hàm Python thực thi logic của tool

Cách sử dụng trong Agent:
    1. Agent nhận yêu cầu từ người dùng
    2. Agent xác định tool cần gọi
    3. Agent gọi AVAILABLE_TOOLS[tool_name](**arguments)
    4. Nhận kết quả và phản hồi người dùng

Tools hiện có:
    - search_order_by_id: Tra cứu đơn hàng
    - check_return_eligibility: Kiểm tra điều kiện đổi trả
"""
