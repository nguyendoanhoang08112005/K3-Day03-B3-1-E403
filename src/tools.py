"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Nơi khai báo tất cả các "món đồ nghề" mà ReAct Agent có thể gọi.
"""

import csv
import os
from datetime import datetime

# Đường dẫn đến dataset
DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "Kaggle_Ecommerce Data.csv")


def _load_orders_data():
    """Đọc dữ liệu từ file CSV và trả về danh sách orders."""
    orders = []
    try:
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                orders.append(row)
    except FileNotFoundError:
        return []
    return orders


def search_order_by_id(order_id: str) -> str:
    """
    Tra cứu thông tin đơn hàng theo mã đơn hàng.

    Args:
        order_id (str): Mã đơn hàng cần tìm (Ví dụ: 'O100001')

    Returns:
        str: Thông tin chi tiết đơn hàng bao gồm:
            - Mã đơn hàng, Mã khách hàng, Mã sản phẩm
            - Danh mục, Đơn giá, Số lượng, Giảm giá
            - Thành tiền (Total Amount), Phí vận chuyển, Lợi nhuận
            - Ngày đặt, Ngày giao hàng
            - Phương thức thanh toán, Khu vực
            - Thông tin khách hàng (tuổi, giới tính)
            - Trạng thái đổi trả (nếu có)
    """
    orders = _load_orders_data()
    order_id_upper = order_id.upper()

    for order in orders:
        if order.get("order_id", "").upper() == order_id_upper:
            # Parse dữ liệu
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
    Chính sách: Được đổi trả trong vòng 3 ngày kể từ ngày giao hàng.

    Args:
        order_id (str): Mã đơn hàng cần kiểm tra (Ví dụ: 'O100001')

    Returns:
        str: Kết quả kiểm tra bao gồm:
            - Mã đơn hàng, Chi tiết sản phẩm (nếu đủ điều kiện)
            - Xác nhận có được phép đổi trả hay không
            - Thông báo cụ thể về trạng thái đổi trả
    """
    orders = _load_orders_data()
    order_id_upper = order_id.upper()

    for order in orders:
        if order.get("order_id", "").upper() == order_id_upper:
            # Parse delivered_date
            delivered_date_str = order.get("delivered_date", "")
            try:
                delivered_date = datetime.strptime(delivered_date_str, "%d/%m/%Y")
            except ValueError:
                return f"LỖI: Định dạng ngày giao hàng không hợp lệ trong đơn hàng '{order_id}'"

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
            if days_since_delivery <= 3:
                # Đủ điều kiện đổi trả
                remaining_days = 3 - days_since_delivery
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
                days_overdue = days_since_delivery - 3
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
   Thời hạn đổi trả là 3 ngày kể từ ngày giao hàng.
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


# Danh sách các tool được đăng ký để Agent sử dụng
AVAILABLE_TOOLS = {
    "search_order_by_id": search_order_by_id,
    "check_return_eligibility": check_return_eligibility,
}
