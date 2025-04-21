import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, ttk # Đảm bảo ttk được import
import database
import ui # Import lớp Application từ ui.py
import os # Cần cho xử lý đường dẫn ảnh
# Thêm import cho PIL
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # Định nghĩa ImageTk giả nếu cần
    class ImageTk:
        @staticmethod
        def PhotoImage(img):
            return None

class PasswordChangeDialog(simpledialog.Dialog):
    """Hộp thoại tùy chỉnh để đổi mật khẩu."""
    def body(self, master):
        tk.Label(master, text="Mật khẩu hiện tại:").grid(row=0, sticky="w")
        tk.Label(master, text="Mật khẩu mới:").grid(row=1, sticky="w")
        tk.Label(master, text="Xác nhận mật khẩu mới:").grid(row=2, sticky="w")

        self.current_password_entry = tk.Entry(master, show="*")
        self.new_password_entry = tk.Entry(master, show="*")
        self.confirm_password_entry = tk.Entry(master, show="*")

        self.current_password_entry.grid(row=0, column=1)
        self.new_password_entry.grid(row=1, column=1)
        self.confirm_password_entry.grid(row=2, column=1)
        return self.current_password_entry # initial focus

    def apply(self):
        current_pw = self.current_password_entry.get()
        new_pw = self.new_password_entry.get()
        confirm_pw = self.confirm_password_entry.get()

        if not current_pw or not new_pw or not confirm_pw:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đầy đủ các trường.", parent=self)
            self.result = None # Prevent dialog closing
            return

        if new_pw != confirm_pw:
            messagebox.showwarning("Mật khẩu không khớp", "Mật khẩu mới và xác nhận không khớp.", parent=self)
            self.result = None # Prevent dialog closing
            return

        # Trả về tuple các mật khẩu để xử lý bên ngoài
        self.result = (current_pw, new_pw)


# --- Cập nhật lớp Application trong ui.py để tích hợp database ---
class MainApplication(ui.Application):
    def __init__(self):
        # Khởi tạo cơ sở dữ liệu trước khi khởi tạo UI
        database.initialize_database()
        self.all_categories = [] # Lưu trữ categories đã load
        super().__init__() # Gọi __init__ của lớp cha (ui.Application)

    def handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Lỗi đăng nhập", "Vui lòng nhập tên đăng nhập và mật khẩu.")
            return

        user_data = database.get_user_by_username(username)

        if user_data and database.check_password(user_data['password_hash'], password):
            if user_data['is_active']:
                self.current_user = user_data # Lưu thông tin người dùng (dạng dict)
                messagebox.showinfo("Thành công", f"Chào mừng {self.current_user['name']}!")
                # Load categories sau khi đăng nhập thành công
                self.load_categories()
                self.show_main_view()
            else:
                 messagebox.showerror("Lỗi đăng nhập", "Tài khoản này đã bị khóa.")
        else:
            messagebox.showerror("Lỗi đăng nhập", "Tên đăng nhập hoặc mật khẩu không đúng.")

    def load_categories(self):
        """Lấy danh sách categories từ DB."""
        self.all_categories = database.get_all_categories()
        print("Categories loaded:", self.all_categories) # Debug

    def setup_post_item_tab(self, tab):
        """Override để truyền categories vào UI."""
        super().setup_post_item_tab(tab) # Gọi hàm setup gốc trong ui.py
        # Nạp dữ liệu categories vào combobox
        if hasattr(self, 'item_category_combobox'): # Kiểm tra widget đã tồn tại chưa
             self.load_categories_into_combobox(self.all_categories)

    def handle_select_image(self):
        """Mở hộp thoại chọn file ảnh."""
        # Xác định thư mục gốc của dự án để lưu ảnh (ví dụ: assets/images)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        image_dir = os.path.join(base_dir, "assets", "images")
        os.makedirs(image_dir, exist_ok=True) # Tạo thư mục nếu chưa có

        file_path = filedialog.askopenfilename(
            title="Chọn ảnh cho món đồ",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            # Lưu đường dẫn tương đối hoặc chỉ tên file nếu muốn copy vào thư mục assets
            # Ở đây tạm lưu đường dẫn tuyệt đối, cần cải thiện sau (ví dụ copy file)
            self.selected_image_path.set(file_path)
            print(f"Selected image: {file_path}")

    def handle_post_item(self):
        """Xử lý logic khi người dùng nhấn nút Đăng bài."""
        if not self.current_user:
            messagebox.showerror("Lỗi", "Vui lòng đăng nhập để đăng bài.")
            return

        name = self.item_name_entry.get().strip()
        selected_category_name = self.item_category_var.get()
        description = self.item_description_text.get("1.0", tk.END).strip()
        price_str = self.item_price_entry.get().strip()
        image_path = self.selected_image_path.get() # Lấy đường dẫn từ biến

        # --- Validation ---
        if not name or not selected_category_name or not price_str:
            messagebox.showerror("Lỗi đăng bài", "Vui lòng điền đầy đủ Tên món đồ, Danh mục và Giá.")
            return

        try:
            price = float(price_str)
            if price < 0:
                raise ValueError("Giá không thể âm.")
        except ValueError:
            messagebox.showerror("Lỗi đăng bài", "Giá phải là một số hợp lệ (ví dụ: 50000 hoặc 0).")
            return

        # Tìm category_id từ tên đã chọn
        category_id = None
        for cat in self.all_categories:
            if cat['name'] == selected_category_name:
                category_id = cat['id']
                break

        if category_id is None:
             messagebox.showerror("Lỗi đăng bài", "Danh mục không hợp lệ.")
             return

        user_id = self.current_user['id']

        # --- Gọi hàm add_item từ database ---
        success, message, item_id = database.add_item(user_id, category_id, name, description, image_path, price)

        if success:
            messagebox.showinfo("Thành công", message)
            self.clear_post_item_form() # Xóa form sau khi đăng thành công
        else:
            messagebox.showerror("Lỗi đăng bài", message)

    def handle_registration(self):
        """Xử lý logic khi người dùng nhấn nút Đăng ký."""
        username = self.reg_username_entry.get()
        password = self.reg_password_entry.get()
        confirm_password = self.reg_confirm_password_entry.get()
        name = self.reg_name_entry.get()
        role = self.reg_role_var.get()
        grade = None
        organization = self.reg_org_entry.get().strip() # Lấy giá trị Tổ chức
        if not organization: # Nếu trống thì lưu là None
            organization = None

        # Lấy giá trị grade nếu là student
        if role == "student":
            grade = self.reg_grade_entry.get()
        # elif role == "teacher": # Không cần làm gì thêm cho teacher

        # --- Validation cơ bản ---
        if not username or not password or not confirm_password or not name or not role:
            messagebox.showerror("Lỗi đăng ký", "Vui lòng điền đầy đủ các trường bắt buộc (*).")
            return

        if password != confirm_password:
            messagebox.showerror("Lỗi đăng ký", "Mật khẩu và xác nhận mật khẩu không khớp.")
            return

        # Cập nhật kiểm tra bắt buộc cho Lớp nếu cần
        if role == "student" and not grade:
             messagebox.showerror("Lỗi đăng ký", "Vui lòng nhập Lớp cho học sinh.")
             return

        # --- Gọi hàm add_user từ database (đã cập nhật) ---
        success, message = database.add_user(username, password, role, name, grade, organization) # grade và organization sẽ là None nếu là teacher

        if success:
            messagebox.showinfo("Thành công", message + "\nBạn có thể đăng nhập ngay bây giờ.")
            # Xóa các trường trong form đăng ký
            self.reg_username_entry.delete(0, tk.END)
            self.reg_password_entry.delete(0, tk.END)
            self.reg_confirm_password_entry.delete(0, tk.END)
            self.reg_name_entry.delete(0, tk.END)
            self.reg_grade_entry.delete(0, tk.END)
            self.reg_org_entry.delete(0, tk.END) # Xóa trường organization
            # Quay lại màn hình đăng nhập
            self.show_login_view_from_register()
        else:
            messagebox.showerror("Lỗi đăng ký", message)

    def setup_admin_tab(self, tab):
        """Override để load dữ liệu admin khi setup tab."""
        super().setup_admin_tab(tab)
        # Load dữ liệu người dùng và pending items
        if hasattr(self, 'user_tree'):
             self.load_users_to_admin_view()
        if hasattr(self, 'pending_items_tree'):
             self.load_pending_items_view()

    def load_users_to_admin_view(self):
        """Lấy dữ liệu người dùng từ DB và hiển thị trong Treeview."""
        if not hasattr(self, 'user_tree'):
            print("Lỗi: user_tree chưa được tạo.")
            return

        # Xóa dữ liệu cũ trong Treeview
        for item in self.user_tree.get_children():
            self.user_tree.delete(item)

        try:
            all_users = database.get_all_users()
            for user in all_users:
                # Bỏ qua admin hiện tại nếu cần (ví dụ: không cho tự khóa)
                if user['id'] == self.current_user['id']:
                    continue

                status_text = "Hoạt động" if user['is_active'] else "Đã khóa"
                # Chuyển đổi None thành chuỗi rỗng để hiển thị
                grade = user['grade'] if user['grade'] is not None else ""
                org = user['organization'] if user['organization'] is not None else ""
                # Format ngày tạo nếu cần
                created_at_str = user['created_at'][:16] if user['created_at'] else "" # Lấy YYYY-MM-DD HH:MM

                self.user_tree.insert("", tk.END, values=(
                    user['id'],
                    user['username'],
                    user['name'],
                    user['role'],
                    grade,
                    org,
                    status_text,
                    created_at_str
                ))
        except Exception as e:
            messagebox.showerror("Lỗi tải dữ liệu", f"Không thể tải danh sách người dùng: {e}")
            print(f"Lỗi khi tải users: {e}")

    def handle_toggle_user_status(self):
        """Xử lý việc khóa hoặc mở khóa tài khoản người dùng được chọn."""
        selected_items = self.user_tree.selection()
        if not selected_items:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một người dùng để khóa hoặc mở khóa.")
            return

        if len(selected_items) > 1:
             messagebox.showwarning("Chọn nhiều", "Vui lòng chỉ chọn một người dùng mỗi lần.")
             return

        selected_item = selected_items[0]
        user_values = self.user_tree.item(selected_item, 'values')
        user_id = user_values[0]
        current_status_text = user_values[6] # Lấy trạng thái hiện tại từ Treeview

        # Xác định trạng thái mới (đảo ngược)
        new_status_bool = False if current_status_text == "Hoạt động" else True
        action_text = "mở khóa" if new_status_bool else "khóa"

        # Hỏi xác nhận
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn {action_text} người dùng '{user_values[1]}' (ID: {user_id}) không?")

        if confirm:
            try:
                success, message = database.update_user_status(user_id, new_status_bool)
                if success:
                    messagebox.showinfo("Thành công", message)
                    # Làm mới danh sách người dùng
                    self.load_users_to_admin_view()
                else:
                    messagebox.showerror("Lỗi", message)
            except Exception as e:
                 messagebox.showerror("Lỗi hệ thống", f"Đã xảy ra lỗi khi cập nhật: {e}")

    def show_main_view(self):
        """Override để load dữ liệu phù hợp khi hiển thị main view."""
        super().show_main_view()
        self.load_approved_items_view() # Load danh sách đồ chung cho mọi người
        if self.current_user:
            if self.current_user['role'] in ['student', 'teacher']:
                self.load_profile_data()
                self.load_my_items_view()
            elif self.current_user['role'] == 'admin':
                 self.load_users_to_admin_view()
                 self.load_pending_items_view() # Load pending items cho admin

    def setup_profile_tab(self, tab):
        """Override để load dữ liệu hồ sơ khi setup tab."""
        super().setup_profile_tab(tab)
        # Không cần gọi load_profile_data ở đây nữa vì đã gọi trong show_main_view

    def load_profile_data(self):
        """Nạp dữ liệu người dùng hiện tại vào tab Hồ sơ."""
        if not self.current_user or not hasattr(self, 'profile_username_label'):
            return # Chưa đăng nhập hoặc tab chưa sẵn sàng

        user_id = self.current_user['id']
        # Lấy dữ liệu mới nhất từ DB phòng trường hợp có thay đổi ngầm
        user_data = database.get_user_by_username(self.current_user['username'])
        if not user_data:
             messagebox.showerror("Lỗi", "Không thể tải thông tin người dùng.")
             self.handle_logout() # Đăng xuất nếu không tìm thấy user
             return
        self.current_user = user_data # Cập nhật dữ liệu user hiện tại

        # Điền thông tin vào các label và entry
        self.profile_username_label.config(text=self.current_user['username'])
        self.profile_name_entry.delete(0, tk.END)
        self.profile_name_entry.insert(0, self.current_user['name'])
        self.profile_role_label.config(text=self.current_user['role'])

        # Xóa và điền lại các trường grade/org
        self.profile_grade_entry.delete(0, tk.END)
        self.profile_org_entry.delete(0, tk.END)

        # Ẩn/hiện và điền dữ liệu cho grade/org dựa trên vai trò
        if self.current_user['role'] == 'student':
            self.profile_grade_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
            self.profile_grade_entry.grid(row=4, column=1, padx=5, pady=5)
            if self.current_user['grade']:
                self.profile_grade_entry.insert(0, self.current_user['grade'])

            self.profile_org_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
            self.profile_org_entry.grid(row=5, column=1, padx=5, pady=5)
            if self.current_user['organization']:
                self.profile_org_entry.insert(0, self.current_user['organization'])
        elif self.current_user['role'] == 'teacher':
            self.profile_grade_label.grid_forget()
            self.profile_grade_entry.grid_forget()

            self.profile_org_label.grid(row=4, column=0, padx=5, pady=5, sticky="w") # Đẩy lên row 4
            self.profile_org_entry.grid(row=4, column=1, padx=5, pady=5) # Đẩy lên row 4
            if self.current_user['organization']:
                self.profile_org_entry.insert(0, self.current_user['organization'])
        else: # Admin hoặc vai trò khác
             self.profile_grade_label.grid_forget()
             self.profile_grade_entry.grid_forget()
             self.profile_org_label.grid_forget()
             self.profile_org_entry.grid_forget()

    def handle_update_profile(self):
        """Xử lý lưu thay đổi thông tin hồ sơ."""
        if not self.current_user:
            return

        user_id = self.current_user['id']
        new_name = self.profile_name_entry.get().strip()
        new_grade = None
        new_org = None

        if not new_name:
            messagebox.showerror("Lỗi", "Họ và tên không được để trống.")
            return

        # Lấy grade/org tùy theo vai trò
        if self.current_user['role'] == 'student':
            new_grade = self.profile_grade_entry.get().strip()
            new_org = self.profile_org_entry.get().strip()
            if not new_grade: # Kiểm tra nếu lớp là bắt buộc
                 messagebox.showerror("Lỗi", "Lớp không được để trống.")
                 return
        elif self.current_user['role'] == 'teacher':
             new_org = self.profile_org_entry.get().strip()

        # Chuyển chuỗi rỗng thành None để lưu vào DB
        new_grade = new_grade if new_grade else None
        new_org = new_org if new_org else None

        success, message = database.update_user_profile(user_id, new_name, new_grade, new_org)

        if success:
            messagebox.showinfo("Thành công", message)
            # Cập nhật lại thông tin user hiện tại và thanh top_bar
            self.current_user['name'] = new_name
            self.current_user['grade'] = new_grade
            self.current_user['organization'] = new_org
            # Cập nhật label trên top_bar (cần truy cập label đó - giả sử nó có tên self.top_bar_user_label)
            # Hoặc đơn giản là load lại profile data để cập nhật UI
            self.load_profile_data()
            # Cập nhật thanh top bar (cần tìm widget label trong top_bar)
            for widget in self.main_frame.winfo_children():
                if isinstance(widget, tk.Frame) and widget.winfo_class() == 'Frame': # Tìm top_bar frame
                    for label in widget.winfo_children():
                        if isinstance(label, tk.Label) and label.cget("text").startswith("Người dùng:"):
                            label.config(text=f"Người dùng: {self.current_user['name']} ({self.current_user['role']})")
                            break
                    break

        else:
            messagebox.showerror("Lỗi", message)

    def handle_change_password(self):
        """Mở hộp thoại và xử lý đổi mật khẩu."""
        if not self.current_user:
            return

        dialog = PasswordChangeDialog(self, "Đổi mật khẩu")
        if dialog.result:
            current_pw, new_pw = dialog.result
            user_id = self.current_user['id']
            username = self.current_user['username']

            # Kiểm tra mật khẩu hiện tại
            user_data = database.get_user_by_username(username) # Lấy lại hash mới nhất
            if not user_data or not database.check_password(user_data['password_hash'], current_pw):
                messagebox.showerror("Lỗi", "Mật khẩu hiện tại không đúng.", parent=self) # parent=self để hiện trên dialog
                return

            # Cập nhật mật khẩu mới
            success, message = database.update_user_password(user_id, new_pw)
            if success:
                messagebox.showinfo("Thành công", message)
            else:
                messagebox.showerror("Lỗi", message)


    def handle_delete_user(self):
        """Xử lý xóa người dùng được chọn bởi Admin."""
        selected_items = self.user_tree.selection()
        if not selected_items:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một người dùng để xóa.")
            return

        if len(selected_items) > 1:
             messagebox.showwarning("Chọn nhiều", "Vui lòng chỉ chọn một người dùng mỗi lần để xóa.")
             return

        selected_item = selected_items[0]
        user_values = self.user_tree.item(selected_item, 'values')
        user_id = user_values[0]
        username = user_values[1]

        # Hỏi xác nhận lần nữa, nhấn mạnh hậu quả
        confirm = messagebox.askyesno("Xác nhận XÓA", f"!!! CẢNH BÁO !!!\nBạn có chắc chắn muốn XÓA vĩnh viễn người dùng '{username}' (ID: {user_id}) không?\nHành động này KHÔNG THỂ hoàn tác và có thể ảnh hưởng đến dữ liệu liên quan.", icon='warning')

        if confirm:
            try:
                success, message = database.delete_user(user_id)
                if success:
                    messagebox.showinfo("Thành công", message)
                    # Làm mới danh sách người dùng
                    self.load_users_to_admin_view()
                else:
                    # Hiển thị lỗi cụ thể từ database.delete_user
                    messagebox.showerror("Lỗi xóa", message)
            except Exception as e:
                 messagebox.showerror("Lỗi hệ thống", f"Đã xảy ra lỗi khi xóa: {e}")

    def setup_my_items_tab(self, tab):
        """Override để load dữ liệu khi setup tab."""
        super().setup_my_items_tab(tab)
        # Không cần gọi load ở đây nếu đã gọi trong show_main_view

    def load_my_items_view(self):
        """Lấy danh sách đồ của người dùng hiện tại và hiển thị."""
        if not self.current_user or not hasattr(self, 'my_items_tree'):
            return # Chưa đăng nhập hoặc tab chưa sẵn sàng

        # Xóa dữ liệu cũ
        for item in self.my_items_tree.get_children():
            self.my_items_tree.delete(item)

        try:
            user_id = self.current_user['id']
            my_items = database.get_items_by_user_id(user_id)
            for item in my_items:
                # Format giá tiền
                price_str = f"{item['price']:,.0f} VNĐ" if item['price'] > 0 else "Miễn phí"
                # Format ngày tạo
                created_at_str = item['created_at'][:16] if item['created_at'] else ""

                self.my_items_tree.insert("", tk.END, iid=item['id'], values=( # Sử dụng item['id'] làm iid
                    item['id'],
                    item['name'],
                    item['category_name'],
                    price_str,
                    item['status'],
                    created_at_str
                ))
        except Exception as e:
            messagebox.showerror("Lỗi tải dữ liệu", f"Không thể tải danh sách đồ của bạn: {e}")
            print(f"Lỗi khi tải my_items: {e}")

    def handle_edit_my_item(self):
        """Xử lý khi nhấn nút Sửa món đồ."""
        selected_items = self.my_items_tree.selection()
        if not selected_items:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một món đồ để sửa.")
            return

        if len(selected_items) > 1:
             messagebox.showwarning("Chọn nhiều", "Vui lòng chỉ chọn một món đồ mỗi lần để sửa.")
             return

        item_id = selected_items[0] # Treeview iid chính là item_id
        # Lấy thông tin chi tiết của item từ DB để điền vào form sửa
        # (Cần thêm hàm get_item_by_id trong database.py)
        # item_details = database.get_item_by_id(item_id) # Giả sử có hàm này

        # --- Tạm thời chỉ in ra ID ---
        print(f"Yêu cầu sửa item có ID: {item_id}")
        messagebox.showinfo("Chức năng đang phát triển", f"Chức năng sửa món đồ (ID: {item_id}) sẽ được cập nhật sau.")

        # --- Hướng phát triển: ---
        # 1. Tạo hàm get_item_by_id(item_id) trong database.py
        # 2. Lấy item_details = database.get_item_by_id(item_id)
        # 3. Kiểm tra item_details có tồn tại và thuộc user hiện tại không.
        # 4. Mở một cửa sổ mới (Toplevel) hoặc chuyển sang tab "Đăng đồ mới"
        #    và điền các thông tin từ item_details vào các trường entry, combobox, text.
        # 5. Thay đổi nút "Đăng bài" thành "Cập nhật" và thay đổi command của nó
        #    để gọi hàm database.update_item(item_id, user_id, ...).
        # 6. Sau khi cập nhật thành công, đóng cửa sổ sửa hoặc quay lại tab "Đồ của tôi" và làm mới danh sách.


    def handle_delete_my_item(self):
        """Xử lý khi nhấn nút Xóa món đồ."""
        selected_items = self.my_items_tree.selection()
        if not selected_items:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một món đồ để xóa.")
            return

        if len(selected_items) > 1:
             messagebox.showwarning("Chọn nhiều", "Vui lòng chỉ chọn một món đồ mỗi lần để xóa.")
             return

        item_id = selected_items[0] # Treeview iid chính là item_id
        item_values = self.my_items_tree.item(item_id, 'values')
        item_name = item_values[1] # Lấy tên đồ từ treeview

        confirm = messagebox.askyesno("Xác nhận Xóa", f"Bạn có chắc chắn muốn xóa món đồ '{item_name}' (ID: {item_id}) không?")

        if confirm:
            try:
                user_id = self.current_user['id']
                success, message = database.delete_item(item_id, user_id)
                if success:
                    messagebox.showinfo("Thành công", message)
                    self.load_my_items_view() # Làm mới danh sách
                else:
                    messagebox.showerror("Lỗi xóa", message)
            except Exception as e:
                 messagebox.showerror("Lỗi hệ thống", f"Đã xảy ra lỗi khi xóa: {e}")

    def load_pending_items_view(self):
        """Lấy danh sách đồ chờ duyệt và hiển thị trong Treeview của Admin."""
        if not self.current_user or self.current_user['role'] != 'admin' or not hasattr(self, 'pending_items_tree'):
            return # Chỉ admin mới xem được và tab phải tồn tại

        # Xóa dữ liệu cũ
        for item in self.pending_items_tree.get_children():
            self.pending_items_tree.delete(item)

        try:
            pending_items = database.get_pending_items()
            for item in pending_items:
                # Format giá tiền
                price_str = f"{item['price']:,.0f} VNĐ" if item['price'] > 0 else "Miễn phí"
                # Format ngày tạo
                created_at_str = item['created_at'][:16] if item['created_at'] else ""

                self.pending_items_tree.insert("", tk.END, iid=item['id'], values=( # Sử dụng item['id'] làm iid
                    item['id'],
                    item['name'],
                    item['category_name'],
                    item['user_username'],
                    price_str,
                    created_at_str
                ))
        except Exception as e:
            messagebox.showerror("Lỗi tải dữ liệu", f"Không thể tải danh sách đồ chờ duyệt: {e}")
            print(f"Lỗi khi tải pending_items: {e}")

    def handle_approve_item(self):
        """Xử lý khi Admin nhấn nút Duyệt."""
        self._process_item_approval('approved')

    def handle_reject_item(self):
        """Xử lý khi Admin nhấn nút Từ chối."""
        self._process_item_approval('rejected')

    def _process_item_approval(self, new_status):
        """Hàm chung để xử lý duyệt hoặc từ chối item."""
        if not self.current_user or self.current_user['role'] != 'admin':
            messagebox.showerror("Lỗi quyền", "Chỉ quản trị viên mới có quyền thực hiện hành động này.")
            return

        selected_items = self.pending_items_tree.selection()
        if not selected_items:
            action_text = "duyệt" if new_status == 'approved' else "từ chối"
            messagebox.showwarning("Chưa chọn", f"Vui lòng chọn một món đồ để {action_text}.")
            return

        if len(selected_items) > 1:
             messagebox.showwarning("Chọn nhiều", "Vui lòng chỉ xử lý một món đồ mỗi lần.")
             return

        item_id = selected_items[0] # Treeview iid chính là item_id
        item_values = self.pending_items_tree.item(item_id, 'values')
        item_name = item_values[1]

        action_text_confirm = "DUYỆT" if new_status == 'approved' else "TỪ CHỐI"
        confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn {action_text_confirm} món đồ '{item_name}' (ID: {item_id}) không?")

        if confirm:
            try:
                admin_id = self.current_user['id']
                success, message = database.update_item_status(item_id, new_status, admin_id)
                if success:
                    messagebox.showinfo("Thành công", message)
                    self.load_pending_items_view() # Làm mới danh sách chờ duyệt
                    self.load_approved_items_view() # Làm mới danh sách đồ đã duyệt trên trang chính
                else:
                    messagebox.showerror("Lỗi", message)
            except Exception as e:
                 messagebox.showerror("Lỗi hệ thống", f"Đã xảy ra lỗi khi xử lý: {e}")

    def setup_items_tab(self, tab):
        """Override để load dữ liệu khi setup tab."""
        super().setup_items_tab(tab)
        # Không cần gọi load ở đây nếu đã gọi trong show_main_view

    def load_approved_items_view(self):
        """Lấy danh sách đồ đã duyệt và hiển thị trên tab chính."""
        if not hasattr(self, 'approved_items_tree'):
            return # Tab chưa sẵn sàng

        # Xóa dữ liệu cũ
        for item in self.approved_items_tree.get_children():
            self.approved_items_tree.delete(item)

        try:
            approved_items = database.get_approved_items()
            for item in approved_items:
                # Format giá tiền
                price_str = f"{item['price']:,.0f} VNĐ" if item['price'] > 0 else "Miễn phí"
                # Format ngày duyệt
                approved_at_str = item['approved_at'][:16] if item['approved_at'] else ""

                self.approved_items_tree.insert("", tk.END, iid=item['id'], values=( # Sử dụng item['id'] làm iid
                    item['id'],
                    item['name'],
                    item['category_name'],
                    item['seller_name'],
                    price_str,
                    approved_at_str
                ))
        except Exception as e:
            messagebox.showerror("Lỗi tải dữ liệu", f"Không thể tải danh sách đồ: {e}")
            print(f"Lỗi khi tải approved_items: {e}")

    def show_approved_item_details(self, event):
        """Xử lý sự kiện double-click trên cây danh sách đồ đã duyệt."""
        tree = event.widget
        selected_items = tree.selection()
        if not selected_items:
            return
        item_id = selected_items[0] # iid chính là item_id
        self._display_item_details_window(item_id)

    def show_pending_item_details(self, event):
        """Xử lý sự kiện double-click trên cây danh sách đồ chờ duyệt."""
        tree = event.widget
        selected_items = tree.selection()
        if not selected_items:
            return
        item_id = selected_items[0] # iid chính là item_id
        self._display_item_details_window(item_id)

    def _display_item_details_window(self, item_id):
        """Lấy dữ liệu và hiển thị cửa sổ chi tiết món đồ."""
        try:
            item_details = database.get_item_details_by_id(item_id)
            if not item_details:
                messagebox.showerror("Lỗi", f"Không tìm thấy thông tin chi tiết cho món đồ ID: {item_id}")
                return

            # Tạo cửa sổ Toplevel mới
            details_window = tk.Toplevel(self)
            details_window.title(f"Chi tiết: {item_details['name']}")
            details_window.geometry("600x500") # Kích thước có thể điều chỉnh

            # Frame chính trong cửa sổ mới
            main_frame = ttk.Frame(details_window, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Frame bên trái cho ảnh
            image_frame = ttk.Frame(main_frame, width=250)
            image_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
            image_frame.pack_propagate(False) # Ngăn frame co lại theo ảnh

            # Frame bên phải cho thông tin text
            info_frame = ttk.Frame(main_frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # --- Hiển thị ảnh ---
            img_label = ttk.Label(image_frame, text="Đang tải ảnh..." if PIL_AVAILABLE else "Ảnh không khả dụng (thiếu Pillow)")
            img_label.pack(pady=10)
            img_display = None # Giữ tham chiếu đến ảnh

            if PIL_AVAILABLE and item_details['image_path'] and os.path.exists(item_details['image_path']):
                try:
                    img = Image.open(item_details['image_path'])
                    # Resize ảnh để vừa với frame (ví dụ: chiều rộng tối đa 230)
                    max_width = 230
                    img_ratio = img.height / img.width
                    new_width = min(img.width, max_width)
                    new_height = int(new_width * img_ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    img_display = ImageTk.PhotoImage(img)
                    img_label.config(image=img_display, text="") # Hiển thị ảnh
                    img_label.image = img_display # Giữ tham chiếu quan trọng!
                except Exception as e:
                    img_label.config(text=f"Lỗi tải ảnh:\n{e}")
                    print(f"Lỗi tải ảnh {item_details['image_path']}: {e}")
            elif item_details['image_path']:
                 img_label.config(text="Không tìm thấy file ảnh.")


            # --- Hiển thị thông tin text ---
            row_num = 0
            def add_info_row(label_text, value_text):
                nonlocal row_num
                ttk.Label(info_frame, text=label_text, font=('Arial', 10, 'bold')).grid(row=row_num, column=0, sticky="nw", padx=5, pady=2)
                # Dùng Text widget cho mô tả để có thể scroll và wrap
                if label_text == "Mô tả:":
                    # Gỡ bỏ background=info_frame.cget('background')
                    desc_text = tk.Text(info_frame, height=5, width=40, wrap=tk.WORD, relief=tk.FLAT)
                    desc_text.insert(tk.END, value_text if value_text else "")
                    desc_text.config(state=tk.DISABLED) # Không cho sửa
                    desc_text.grid(row=row_num, column=1, sticky="nsew", padx=5, pady=2)
                    # Thêm scrollbar cho Text nếu cần
                    # scroll = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=desc_text.yview)
                    # scroll.grid(row=row_num, column=2, sticky='ns')
                    # desc_text['yscrollcommand'] = scroll.set
                else:
                    ttk.Label(info_frame, text=value_text if value_text else "N/A", wraplength=300, justify=tk.LEFT).grid(row=row_num, column=1, sticky="nw", padx=5, pady=2)
                row_num += 1

            add_info_row("Tên món đồ:", item_details['name'])
            add_info_row("Danh mục:", item_details['category_name'])
            price_str = f"{item_details['price']:,.0f} VNĐ" if item_details['price'] > 0 else "Miễn phí"
            add_info_row("Giá:", price_str)
            # add_info_row("Trạng thái:", item_details['status'])
            add_info_row("Mô tả:", item_details['description'])
            add_info_row("Người đăng:", f"{item_details['user_name']} ({item_details['user_username']})")
            # Hiển thị thêm thông tin người đăng nếu cần (ví dụ: lớp, tổ chức)
            if item_details['user_organization']:
                 add_info_row("Tổ chức (người đăng):", item_details['user_organization'])

            add_info_row("Ngày đăng:", item_details['created_at'][:16] if item_details['created_at'] else "N/A")
            if item_details['status'] == 'approved' and item_details['approved_at']:
                add_info_row("Ngày duyệt:", item_details['approved_at'][:16])

            # Cho phép cột 1 của info_frame co giãn
            info_frame.columnconfigure(1, weight=1)
            # Cho phép hàng chứa mô tả co giãn
            desc_row_index = [i for i, child in enumerate(info_frame.winfo_children()) if isinstance(child, tk.Text)]
            if desc_row_index:
                info_frame.rowconfigure(desc_row_index[0], weight=1)


            # Nút đóng
            close_button = ttk.Button(details_window, text="Đóng", command=details_window.destroy)
            close_button.pack(pady=(0, 10))

            # Đưa cửa sổ lên trên cùng và focus
            details_window.transient(self)
            details_window.grab_set()
            self.wait_window(details_window)

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể hiển thị chi tiết món đồ: {e}")
            print(f"Lỗi hiển thị chi tiết item {item_id}: {e}")

# --- Hàm main để chạy ứng dụng ---
if __name__ == "__main__":
    # Chạy initialize_database một lần nữa để đảm bảo cột mới được thêm
    # database.initialize_database() # Có thể gọi ở đây hoặc chạy database.py riêng
    app = MainApplication()
    app.mainloop()
