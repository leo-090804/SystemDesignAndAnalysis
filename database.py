import sqlite3
import os
import hashlib # Để hash mật khẩu
import datetime # Cần cho add_item
import random # Thêm thư viện random

DATABASE_NAME = "school_exchange.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_NAME)

def get_db_connection():
    """Tạo kết nối tới cơ sở dữ liệu SQLite."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row # Trả về kết quả dạng dictionary-like
    return conn

def hash_password(password):
    """Hash mật khẩu sử dụng SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_unique_user_id(cursor):
    """Tạo một ID người dùng ngẫu nhiên 9 chữ số duy nhất."""
    while True:
        user_id = random.randint(100000000, 999999999)
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            return user_id

def initialize_database():
    """Khởi tạo cơ sở dữ liệu và tạo các bảng nếu chưa tồn tại."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Bảng Users - Thay đổi định nghĩa cột id
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, -- Bỏ AUTOINCREMENT, giữ PRIMARY KEY
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
        name TEXT NOT NULL,
        grade TEXT,
        subject TEXT, -- Bỏ NOT NULL nếu giáo viên không cần nhập
        organization TEXT, -- Thêm cột tổ chức
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Bảng Categories
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    )
    """)

    # Bảng Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        image_path TEXT,
        price REAL DEFAULT 0,
        status TEXT NOT NULL CHECK(status IN ('pending', 'approved', 'rejected', 'exchanged', 'donated', 'sold')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    """)

    # Bảng Campaigns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        start_date DATE,
        end_date DATE,
        created_by_user_id INTEGER NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('fundraising', 'donation', 'exchange_event')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by_user_id) REFERENCES users (id)
    )
    """)

     # Bảng liên kết Items và Campaigns (Nhiều-Nhiều)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS item_campaign_link (
        item_id INTEGER NOT NULL,
        campaign_id INTEGER NOT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (item_id, campaign_id),
        FOREIGN KEY (item_id) REFERENCES items (id) ON DELETE CASCADE,
        FOREIGN KEY (campaign_id) REFERENCES campaigns (id) ON DELETE CASCADE
    )
    """)

    # Bảng Transactions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        buyer_user_id INTEGER, -- Có thể NULL cho quyên góp
        seller_user_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL CHECK(transaction_type IN ('sale', 'donation', 'exchange_fee')),
        amount REAL DEFAULT 0,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        campaign_id INTEGER, -- Liên kết tới chiến dịch nếu có
        FOREIGN KEY (item_id) REFERENCES items (id),
        FOREIGN KEY (buyer_user_id) REFERENCES users (id),
        FOREIGN KEY (seller_user_id) REFERENCES users (id),
        FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
    )
    """)

    # Thêm tài khoản admin mặc định nếu chưa có
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin_exists = cursor.fetchone()
    if not admin_exists:
        admin_pass_hash = hash_password("admin123") # Mật khẩu mặc định, nên thay đổi!
        admin_id = generate_unique_user_id(cursor) # Tạo ID ngẫu nhiên cho admin
        # Cập nhật INSERT cho admin (thêm id và giá trị NULL cho organization)
        cursor.execute("""
        INSERT INTO users (id, username, password_hash, role, name, is_active, organization)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (admin_id, 'admin', admin_pass_hash, 'admin', 'Quản trị viên', 1, None))
        print(f"Tài khoản admin mặc định đã được tạo (ID: {admin_id}, username: admin, password: admin123). Vui lòng đổi mật khẩu.")

    # Thêm một số danh mục mẫu nếu chưa có
    cursor.execute("SELECT id FROM categories")
    category_exists = cursor.fetchone()
    if not category_exists:
        default_categories = [
            ('Sách giáo khoa', 'Sách giáo khoa các lớp'),
            ('Truyện, Sách tham khảo', ''),
            ('Đồng phục', 'Quần áo đồng phục học sinh'),
            ('Dụng cụ học tập', 'Bút, thước, compa,...'),
            ('Đồ dùng cá nhân', ''),
            ('Khác', 'Các loại khác chưa phân loại')
        ]
        cursor.executemany("INSERT INTO categories (name, description) VALUES (?, ?)", default_categories)
        print("Đã thêm các danh mục mẫu.")

    conn.commit()

    # Kiểm tra và thêm cột 'organization' nếu chưa có (cho DB đã tồn tại)
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'organization' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN organization TEXT")
            conn.commit()
            print("Đã thêm cột 'organization' vào bảng 'users'.")
        # Kiểm tra lại cột subject, nếu cần thì cập nhật (phức tạp hơn, tạm bỏ qua)
    except Exception as e:
        print(f"Lỗi khi kiểm tra/cập nhật bảng users: {e}")

    conn.close()
    print("Cơ sở dữ liệu đã được khởi tạo/cập nhật thành công.")

# Các hàm CRUD khác sẽ được thêm vào đây (ví dụ: add_user, get_user, add_item, get_items, ...)
# Ví dụ:
def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()
    conn.close()
    # Chuyển đổi row thành đối tượng User nếu cần
    if user_row:
        # return User(**user_row) # Cần import User từ models
        return dict(user_row) # Hoặc trả về dict trước
    return None

def check_password(stored_hash, provided_password):
    """Kiểm tra mật khẩu nhập vào có khớp với hash đã lưu không."""
    return stored_hash == hash_password(provided_password)

# Cập nhật hàm add_user: thêm id ngẫu nhiên
def add_user(username, password, role, name, grade=None, organization=None):
    """Thêm người dùng mới vào cơ sở dữ liệu với ID ngẫu nhiên."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Kiểm tra xem username đã tồn tại chưa
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        return False, "Tên đăng nhập đã tồn tại."

    password_hash = hash_password(password)
    user_id = generate_unique_user_id(cursor) # Tạo ID ngẫu nhiên duy nhất

    try:
        # Cập nhật INSERT statement để bao gồm cả id
        cursor.execute("""
        INSERT INTO users (id, username, password_hash, role, name, grade, organization, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, username, password_hash, role, name, grade, organization, 1)) # Mặc định active
        conn.commit()
        conn.close()
        return True, "Đăng ký thành công."
    except sqlite3.IntegrityError as e:
        # Xử lý các lỗi ràng buộc khác nếu có (ví dụ: ID bị trùng dù đã kiểm tra - rất hiếm)
        conn.close()
        return False, f"Lỗi khi đăng ký: {e}"
    except Exception as e:
        conn.close()
        return False, f"Đã xảy ra lỗi không mong muốn: {e}"

def get_all_categories():
    """Lấy tất cả danh mục từ cơ sở dữ liệu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cursor.fetchall()
    conn.close()
    # Trả về list các dictionary hoặc tuple tùy ý, ở đây dùng dict
    return [dict(row) for row in categories]

def add_item(user_id, category_id, name, description, image_path, price):
    """Thêm một món đồ mới vào cơ sở dữ liệu với trạng thái 'pending'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO items (user_id, category_id, name, description, image_path, price, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, category_id, name, description, image_path, price, 'pending', datetime.datetime.now()))
        conn.commit()
        item_id = cursor.lastrowid # Lấy ID của item vừa thêm
        conn.close()
        return True, "Đăng bài thành công! Vui lòng chờ duyệt.", item_id
    except Exception as e:
        conn.close()
        return False, f"Lỗi khi đăng bài: {e}", None

def get_all_users():
    """Lấy danh sách tất cả người dùng (trừ admin hiện tại nếu muốn)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Lấy tất cả các cột cần thiết, sắp xếp theo username
    cursor.execute("""
        SELECT id, username, role, name, grade, organization, is_active, created_at
        FROM users
        ORDER BY username
    """)
    users = cursor.fetchall()
    conn.close()
    return [dict(row) for row in users]

def update_user_status(user_id, is_active):
    """Cập nhật trạng thái is_active của người dùng."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (is_active, user_id))
        conn.commit()
        updated_rows = cursor.rowcount
        conn.close()
        if updated_rows > 0:
            return True, "Cập nhật trạng thái người dùng thành công."
        else:
            return False, "Không tìm thấy người dùng hoặc trạng thái không đổi."
    except Exception as e:
        conn.close()
        return False, f"Lỗi khi cập nhật trạng thái: {e}"

def delete_user(user_id):
    """Xóa người dùng khỏi cơ sở dữ liệu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Bật hỗ trợ khóa ngoại để ràng buộc ON DELETE hoạt động (nếu có)
        conn.execute("PRAGMA foreign_keys = ON")
        # Cân nhắc xử lý các bản ghi liên quan (items, transactions, campaigns)
        # Ví dụ: Xóa các items của người dùng trước? Hoặc đặt user_id thành NULL?
        # Hiện tại, nếu có khóa ngoại ràng buộc (vd: item.user_id), việc xóa có thể lỗi
        # nếu không có ON DELETE CASCADE hoặc ON DELETE SET NULL.
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        deleted_rows = cursor.rowcount
        conn.close()
        if deleted_rows > 0:
            return True, "Xóa người dùng thành công."
        else:
            return False, "Không tìm thấy người dùng để xóa."
    except sqlite3.IntegrityError as e:
        # Lỗi này thường xảy ra nếu có khóa ngoại đang tham chiếu đến user này
        # và không có quy tắc ON DELETE phù hợp.
        conn.close()
        return False, f"Lỗi xóa người dùng: Có thể do người dùng này có dữ liệu liên quan (bài đăng, giao dịch,...). Lỗi: {e}"
    except Exception as e:
        conn.close()
        return False, f"Lỗi khi xóa người dùng: {e}"

def update_user_profile(user_id, name, grade, organization):
    """Cập nhật thông tin hồ sơ người dùng (không bao gồm mật khẩu)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE users
            SET name = ?, grade = ?, organization = ?
            WHERE id = ?
        """, (name, grade, organization, user_id))
        conn.commit()
        updated_rows = cursor.rowcount
        conn.close()
        if updated_rows > 0:
            return True, "Cập nhật hồ sơ thành công."
        else:
            # Có thể xảy ra nếu không tìm thấy user hoặc dữ liệu không thay đổi
             return False, "Không tìm thấy người dùng hoặc thông tin không thay đổi."
    except Exception as e:
        conn.close()
        return False, f"Lỗi khi cập nhật hồ sơ: {e}"

def update_user_password(user_id, new_password):
    """Cập nhật mật khẩu người dùng."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        new_password_hash = hash_password(new_password)
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
        conn.commit()
        updated_rows = cursor.rowcount
        conn.close()
        if updated_rows > 0:
            return True, "Đổi mật khẩu thành công."
        else:
            return False, "Không tìm thấy người dùng." # Hoặc lỗi khác
    except Exception as e:
        conn.close()
        return False, f"Lỗi khi đổi mật khẩu: {e}"

def get_items_by_user_id(user_id):
    """Lấy danh sách các món đồ đã đăng bởi một người dùng cụ thể."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Lấy thêm tên danh mục
    cursor.execute("""
        SELECT i.id, i.name, c.name as category_name, i.price, i.status, i.created_at, i.description, i.image_path, i.category_id
        FROM items i
        JOIN categories c ON i.category_id = c.id
        WHERE i.user_id = ?
        ORDER BY i.created_at DESC
    """, (user_id,))
    items = cursor.fetchall()
    conn.close()
    return [dict(row) for row in items]

def update_item(item_id, user_id, category_id, name, description, image_path, price):
    """Cập nhật thông tin một món đồ (chỉ chủ sở hữu mới được cập nhật)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Kiểm tra xem người dùng có phải chủ sở hữu không trước khi cập nhật
        cursor.execute("SELECT user_id FROM items WHERE id = ?", (item_id,))
        item_owner = cursor.fetchone()
        if not item_owner or item_owner['user_id'] != user_id:
            conn.close()
            return False, "Bạn không có quyền sửa món đồ này."

        # Chỉ cho phép sửa khi status là 'pending' hoặc 'approved'? (Tùy yêu cầu)
        # cursor.execute("SELECT status FROM items WHERE id = ?", (item_id,))
        # item_status = cursor.fetchone()
        # if item_status and item_status['status'] not in ['pending', 'approved']:
        #     conn.close()
        #     return False, f"Không thể sửa món đồ ở trạng thái '{item_status['status']}'."

        cursor.execute("""
            UPDATE items
            SET category_id = ?, name = ?, description = ?, image_path = ?, price = ?, status = 'pending' -- Reset status về pending sau khi sửa?
            WHERE id = ? AND user_id = ?
        """, (category_id, name, description, image_path, price, item_id, user_id))
        conn.commit()
        updated_rows = cursor.rowcount
        conn.close()
        if updated_rows > 0:
            return True, "Cập nhật món đồ thành công. Vui lòng chờ duyệt lại."
        else:
            return False, "Cập nhật thất bại hoặc không có thay đổi."
    except Exception as e:
        conn.close()
        return False, f"Lỗi khi cập nhật món đồ: {e}"

def delete_item(item_id, user_id):
    """Xóa một món đồ (chỉ chủ sở hữu hoặc admin mới được xóa)."""
    # Trong trường hợp này, chỉ cho chủ sở hữu xóa từ tab "Đồ của tôi"
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Bật khóa ngoại
        conn.execute("PRAGMA foreign_keys = ON")
        # Kiểm tra quyền sở hữu trước khi xóa
        cursor.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, user_id))
        conn.commit()
        deleted_rows = cursor.rowcount
        conn.close()
        if deleted_rows > 0:
            return True, "Xóa món đồ thành công."
        else:
            # Có thể do không tìm thấy item hoặc không đúng chủ sở hữu
            return False, "Xóa thất bại. Không tìm thấy món đồ hoặc bạn không có quyền xóa."
    except sqlite3.IntegrityError as e:
         # Ví dụ: Nếu item đã có trong transaction và không có ON DELETE SET NULL/CASCADE
         conn.close()
         return False, f"Lỗi xóa món đồ: Không thể xóa do có dữ liệu liên quan. Lỗi: {e}"
    except Exception as e:
        conn.close()
        return False, f"Lỗi khi xóa món đồ: {e}"

def get_pending_items():
    """Lấy danh sách các món đồ đang chờ duyệt (status='pending')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Lấy thêm thông tin người đăng và danh mục
    cursor.execute("""
        SELECT i.id, i.name, c.name as category_name, u.username as user_username, i.price, i.description, i.image_path, i.created_at
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN users u ON i.user_id = u.id
        WHERE i.status = 'pending'
        ORDER BY i.created_at ASC -- Ưu tiên duyệt bài cũ trước
    """)
    items = cursor.fetchall()
    conn.close()
    return [dict(row) for row in items]

def update_item_status(item_id, new_status, admin_id):
    """Cập nhật trạng thái của một món đồ (approved/rejected) bởi admin."""
    if new_status not in ['approved', 'rejected']:
        return False, "Trạng thái không hợp lệ."

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        approved_time = datetime.datetime.now() if new_status == 'approved' else None
        # Cần thêm cột admin_id vào bảng items để lưu ai đã duyệt? (Tùy chọn)
        # Hoặc ghi log vào bảng khác. Tạm thời chỉ cập nhật status và approved_at.
        cursor.execute("""
            UPDATE items
            SET status = ?, approved_at = ?
            WHERE id = ? AND status = 'pending' -- Chỉ cập nhật nếu đang pending
        """, (new_status, approved_time, item_id))
        conn.commit()
        updated_rows = cursor.rowcount
        conn.close()
        if updated_rows > 0:
            action = "Duyệt" if new_status == 'approved' else "Từ chối"
            return True, f"{action} món đồ thành công."
        else:
            return False, "Không tìm thấy món đồ đang chờ duyệt hoặc cập nhật thất bại."
    except Exception as e:
        conn.close()
        return False, f"Lỗi khi cập nhật trạng thái món đồ: {e}"

def get_approved_items():
    """Lấy danh sách các món đồ đã được duyệt (status='approved')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Lấy thêm thông tin người đăng và danh mục
    cursor.execute("""
        SELECT i.id, i.name, c.name as category_name, u.name as seller_name, i.price, i.description, i.image_path, i.approved_at
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN users u ON i.user_id = u.id
        WHERE i.status = 'approved'
        ORDER BY i.approved_at DESC -- Hiển thị đồ mới duyệt lên đầu
    """)
    items = cursor.fetchall()
    conn.close()
    return [dict(row) for row in items]

def get_item_details_by_id(item_id):
    """Lấy thông tin chi tiết của một món đồ dựa vào ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            i.id, i.name, i.description, i.price, i.status, i.image_path,
            i.created_at, i.approved_at,
            c.name as category_name,
            u.id as user_id, u.username as user_username, u.name as user_name, u.role as user_role, u.grade as user_grade, u.organization as user_organization
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN users u ON i.user_id = u.id
        WHERE i.id = ?
    """, (item_id,))
    item_details = cursor.fetchone()
    conn.close()
    if item_details:
        return dict(item_details)
    return None

if __name__ == '__main__':
    # Chạy file này trực tiếp để khởi tạo/cập nhật DB lần đầu
    # Đoạn mã kiểm tra và xóa file DB cũ đã được gỡ bỏ.
    initialize_database()
