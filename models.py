
class User:
    def __init__(self, id, username, password_hash, role, name, grade=None, subject=None, is_active=True):
        self.id = id
        self.username = username
        self.password_hash = password_hash # Lưu trữ hash của mật khẩu, không lưu mật khẩu gốc
        self.role = role # 'admin', 'teacher', 'student'
        self.name = name
        self.grade = grade # Lớp (cho học sinh)
        self.subject = subject # Môn dạy (cho giáo viên)
        self.is_active = is_active

class Category:
    def __init__(self, id, name, description=""):
        self.id = id
        self.name = name
        self.description = description

class Item:
    def __init__(self, id, user_id, category_id, name, description, image_path, price, status, created_at, approved_at=None):
        self.id = id
        self.user_id = user_id # ID của người đăng
        self.category_id = category_id
        self.name = name
        self.description = description
        self.image_path = image_path # Đường dẫn tới ảnh
        self.price = price # Có thể là 0 nếu quyên góp/trao đổi không phí
        self.status = status # 'pending', 'approved', 'rejected', 'exchanged', 'donated', 'sold'
        self.created_at = created_at
        self.approved_at = approved_at

class Campaign:
    def __init__(self, id, name, description, start_date, end_date, created_by_user_id, type):
        self.id = id
        self.name = name
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.created_by_user_id = created_by_user_id # ID người tạo (Admin/Nhà trường/CLB...)
        self.type = type # 'fundraising', 'donation', 'exchange_event'

class ItemCampaignLink:
     def __init__(self, item_id, campaign_id, joined_at):
         self.item_id = item_id
         self.campaign_id = campaign_id
         self.joined_at = joined_at

class Transaction:
     def __init__(self, id, item_id, buyer_user_id, seller_user_id, transaction_type, amount, transaction_date, campaign_id=None):
         self.id = id
         self.item_id = item_id
         self.buyer_user_id = buyer_user_id # Có thể là None nếu là quyên góp
         self.seller_user_id = seller_user_id
         self.transaction_type = transaction_type # 'sale', 'donation', 'exchange_fee'
         self.amount = amount # Số tiền giao dịch hoặc phí
         self.transaction_date = transaction_date
         self.campaign_id = campaign_id # Liên kết tới chiến dịch nếu có
