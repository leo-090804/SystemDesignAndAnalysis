import tkinter as tk
from tkinter import messagebox, ttk
# Thêm import cho PIL nếu cần hiển thị ảnh (cần cài đặt: pip install Pillow)
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Thư viện Pillow chưa được cài đặt. Ảnh sẽ không hiển thị.")
    # Định nghĩa ImageTk như một lớp giả để tránh lỗi nếu Pillow không có
    class ImageTk:
        @staticmethod
        def PhotoImage(img):
            return None # Trả về None nếu không có Pillow

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ứng dụng Trao đổi Đồ cũ Trường học")
        self.geometry("800x600") # Kích thước cửa sổ ban đầu

        # Lưu thông tin người dùng đăng nhập
        self.current_user = None

        # Tạo các frame chính
        self.create_widgets()

    def create_widgets(self):
        # Frame đăng nhập (hiển thị ban đầu)
        self.login_frame = tk.Frame(self)
        self.setup_login_frame()
        self.login_frame.pack(pady=20)

        # Frame đăng ký (ẩn ban đầu)
        self.register_frame = tk.Frame(self)
        # setup_register_frame() sẽ được gọi khi nhấn nút Đăng ký

        # Frame chính sau khi đăng nhập (sẽ được hiển thị sau)
        self.main_frame = tk.Frame(self)
        # setup_main_frame() sẽ được gọi sau khi đăng nhập thành công

    def setup_login_frame(self):
        # Xóa widget cũ nếu có (khi quay lại từ đăng ký)
        for widget in self.login_frame.winfo_children():
            widget.destroy()

        tk.Label(self.login_frame, text="Đăng nhập", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)

        tk.Label(self.login_frame, text="Tên đăng nhập:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.username_entry = tk.Entry(self.login_frame, width=30)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self.login_frame, text="Mật khẩu:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.password_entry = tk.Entry(self.login_frame, show="*", width=30)
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)

        button_frame = tk.Frame(self.login_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        login_button = tk.Button(button_frame, text="Đăng nhập", command=self.handle_login)
        login_button.pack(side=tk.LEFT, padx=5)

        register_button = tk.Button(button_frame, text="Đăng ký", command=self.show_register_view)
        register_button.pack(side=tk.LEFT, padx=5)

    def setup_register_frame(self):
         # Xóa widget cũ nếu có
        for widget in self.register_frame.winfo_children():
            widget.destroy()

        tk.Label(self.register_frame, text="Đăng ký tài khoản mới", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)

        tk.Label(self.register_frame, text="Tên đăng nhập*:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.reg_username_entry = tk.Entry(self.register_frame, width=30)
        self.reg_username_entry.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(self.register_frame, text="Mật khẩu*:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.reg_password_entry = tk.Entry(self.register_frame, show="*", width=30)
        self.reg_password_entry.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(self.register_frame, text="Xác nhận mật khẩu*:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.reg_confirm_password_entry = tk.Entry(self.register_frame, show="*", width=30)
        self.reg_confirm_password_entry.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(self.register_frame, text="Họ và tên*:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.reg_name_entry = tk.Entry(self.register_frame, width=30)
        self.reg_name_entry.grid(row=4, column=1, padx=5, pady=5)

        tk.Label(self.register_frame, text="Vai trò*:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.reg_role_var = tk.StringVar(self.register_frame)
        self.reg_role_var.set("student") # Giá trị mặc định
        role_options = ["student", "teacher"] # Chỉ cho phép đăng ký 2 vai trò này
        role_menu = ttk.Combobox(self.register_frame, textvariable=self.reg_role_var, values=role_options, state="readonly", width=27)
        role_menu.grid(row=5, column=1, padx=5, pady=5)
        role_menu.bind("<<ComboboxSelected>>", self.toggle_role_specific_fields) # Gọi hàm khi thay đổi vai trò

        # Các trường dành riêng cho vai trò (ẩn/hiện tùy chọn)
        self.reg_grade_label = tk.Label(self.register_frame, text="Lớp (học sinh)*:") # Thêm * nếu bắt buộc
        self.reg_grade_entry = tk.Entry(self.register_frame, width=30)

        # Trường Tổ chức (tùy chọn, cho cả student và teacher)
        self.reg_org_label = tk.Label(self.register_frame, text="Tổ chức (nếu có):")
        self.reg_org_entry = tk.Entry(self.register_frame, width=30)


        # Đặt các trường này vào grid ban đầu
        # Hàng 6: Lớp (chỉ hiện cho student)
        self.reg_grade_label.grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.reg_grade_entry.grid(row=6, column=1, padx=5, pady=5)
        # Hàng 7: Tổ chức (hiện cho cả student và teacher)
        self.reg_org_label.grid(row=7, column=0, padx=5, pady=5, sticky="w")
        self.reg_org_entry.grid(row=7, column=1, padx=5, pady=5)

        # Gọi toggle_role_specific_fields để đảm bảo trạng thái ban đầu đúng
        self.toggle_role_specific_fields()


        button_frame = tk.Frame(self.register_frame)
        # Cập nhật row cho button_frame (ví dụ: row=8)
        button_frame.grid(row=8, column=0, columnspan=2, pady=10)

        register_action_button = tk.Button(button_frame, text="Đăng ký", command=self.handle_registration)
        register_action_button.pack(side=tk.LEFT, padx=5)

        back_button = tk.Button(button_frame, text="Quay lại Đăng nhập", command=self.show_login_view_from_register)
        back_button.pack(side=tk.LEFT, padx=5)

    def toggle_role_specific_fields(self, event=None):
        """Ẩn/hiện các trường Lớp dựa trên vai trò được chọn."""
        # Kiểm tra xem các widget đã được tạo chưa
        if not hasattr(self, 'reg_role_var'):
             return
        selected_role = self.reg_role_var.get()

        # Trường Tổ chức luôn hiển thị ở hàng 7 (hoặc vị trí mong muốn)
        self.reg_org_label.grid(row=7, column=0, padx=5, pady=5, sticky="w")
        self.reg_org_entry.grid(row=7, column=1, padx=5, pady=5)

        if selected_role == "student":
            # Hiện trường Lớp ở hàng 6
            self.reg_grade_label.grid(row=6, column=0, padx=5, pady=5, sticky="w")
            self.reg_grade_entry.grid(row=6, column=1, padx=5, pady=5)
        elif selected_role == "teacher":
            # Ẩn trường Lớp
            self.reg_grade_label.grid_forget()
            self.reg_grade_entry.grid_forget()
        else: # Trường hợp khác (nếu có)
            self.reg_grade_label.grid_forget()
            self.reg_grade_entry.grid_forget()

    def show_register_view(self):
        self.login_frame.pack_forget()
        self.setup_register_frame() # Tạo lại widget để đảm bảo sạch sẽ
        self.register_frame.pack(pady=20)

    def show_login_view_from_register(self):
        self.register_frame.pack_forget()
        self.setup_login_frame() # Tạo lại widget
        self.login_frame.pack(pady=20)

    def handle_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Lỗi đăng nhập", "Vui lòng nhập tên đăng nhập và mật khẩu.")
            return

        # --- Tích hợp kiểm tra đăng nhập với database ---
        # (Sẽ được thêm trong main.py hoặc gọi hàm từ database.py)
        print(f"Đang cố gắng đăng nhập với: {username}") # Tạm thời in ra
        # user = database.get_user_by_username(username)
        # if user and database.check_password(user['password_hash'], password):
        #     self.current_user = user
        #     messagebox.showinfo("Thành công", f"Chào mừng {self.current_user['name']}!")
        #     self.show_main_view()
        # else:
        #     messagebox.showerror("Lỗi đăng nhập", "Tên đăng nhập hoặc mật khẩu không đúng.")
        # --- Kết thúc phần tích hợp ---

        # Giả lập đăng nhập thành công để test UI
        if username == "admin" and password == "admin123": # Tạm thời dùng tk/mk mặc định
             self.current_user = {'id': 1, 'username': 'admin', 'role': 'admin', 'name': 'Quản trị viên'} # Dữ liệu mẫu
             messagebox.showinfo("Thành công", f"Chào mừng {self.current_user['name']}!")
             self.show_main_view()
        else:
             messagebox.showerror("Lỗi đăng nhập", "Tên đăng nhập hoặc mật khẩu không đúng (Thử admin/admin123).")

    def handle_registration(self):
        # Logic xử lý đăng ký sẽ được đặt trong main.py
        # Ở đây chỉ gọi phương thức đó (sẽ được override trong lớp con)
        print("Nút đăng ký được nhấn")
        pass

    def show_main_view(self):
        self.login_frame.pack_forget() # Ẩn frame đăng nhập
        self.setup_main_frame()
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def setup_main_frame(self):
        # Xóa các widget cũ trong main_frame nếu có
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Thanh menu (hoặc các nút điều hướng chính)
        top_bar = tk.Frame(self.main_frame, bd=1, relief=tk.RAISED)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top_bar, text=f"Người dùng: {self.current_user['name']} ({self.current_user['role']})").pack(side=tk.LEFT, padx=10)
        logout_button = tk.Button(top_bar, text="Đăng xuất", command=self.handle_logout)
        logout_button.pack(side=tk.RIGHT, padx=10)

        # Khu vực nội dung chính (sử dụng Notebook - Tab)
        notebook = ttk.Notebook(self.main_frame)

        # Tab Trang chủ/Danh sách đồ
        items_tab = ttk.Frame(notebook)
        notebook.add(items_tab, text='Danh sách Đồ')
        self.setup_items_tab(items_tab)

        # Tab Đăng đồ mới
        post_item_tab = ttk.Frame(notebook)
        notebook.add(post_item_tab, text='Đăng đồ mới')
        # Gọi hàm setup với dữ liệu categories (sẽ được truyền từ MainApplication)
        self.setup_post_item_tab(post_item_tab)

        # Tab Đồ của tôi (chỉ cho student/teacher)
        if self.current_user and self.current_user['role'] in ['student', 'teacher']:
            my_items_tab = ttk.Frame(notebook)
            notebook.add(my_items_tab, text='Đồ của tôi')
            self.setup_my_items_tab(my_items_tab) # Gọi hàm setup mới

        # Tab Hồ sơ cá nhân
        if self.current_user and self.current_user['role'] in ['student', 'teacher']:
            profile_tab = ttk.Frame(notebook)
            notebook.add(profile_tab, text='Hồ sơ')
            self.setup_profile_tab(profile_tab) # Gọi hàm setup

        # Tab Chiến dịch/Hoạt động
        campaigns_tab = ttk.Frame(notebook)
        notebook.add(campaigns_tab, text='Chiến dịch')
        self.setup_campaigns_tab(campaigns_tab)

        # Tab Quản lý (chỉ hiển thị cho admin)
        if self.current_user and self.current_user['role'] == 'admin':
            admin_tab = ttk.Frame(notebook)
            notebook.add(admin_tab, text='Quản lý (Admin)')
            self.setup_admin_tab(admin_tab)

        notebook.pack(expand=True, fill='both', pady=5)

    def setup_items_tab(self, tab):
        """Thiết lập giao diện cho tab Danh sách Đồ."""
        # Frame chứa bộ lọc (nếu có) và nút làm mới
        top_frame = tk.Frame(tab)
        top_frame.pack(pady=5, padx=10, fill=tk.X)

        # TODO: Thêm các widget lọc (theo danh mục, giá,...)
        tk.Label(top_frame, text="Bộ lọc: (Sắp có)").pack(side=tk.LEFT, padx=5)

        refresh_button = tk.Button(top_frame, text="Làm mới", command=self.load_approved_items_view)
        refresh_button.pack(side=tk.RIGHT, padx=5)

        # Frame chứa Treeview và Scrollbar
        tree_frame = tk.Frame(tab)
        tree_frame.pack(pady=(0, 10), padx=10, fill=tk.BOTH, expand=True)

        # Scrollbar
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = tk.Scrollbar(tree_frame, orient='horizontal')
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview để hiển thị danh sách đồ đã duyệt
        self.approved_items_tree = ttk.Treeview(tree_frame,
                                                columns=("id", "name", "category", "seller", "price", "approved_date"),
                                                show="headings",
                                                yscrollcommand=tree_scroll_y.set,
                                                xscrollcommand=tree_scroll_x.set)

        # Định nghĩa các cột
        self.approved_items_tree.heading("id", text="ID")
        self.approved_items_tree.heading("name", text="Tên đồ")
        self.approved_items_tree.heading("category", text="Danh mục")
        self.approved_items_tree.heading("seller", text="Người bán/Tặng")
        self.approved_items_tree.heading("price", text="Giá (VNĐ)")
        self.approved_items_tree.heading("approved_date", text="Ngày duyệt")

        # Định dạng cột
        self.approved_items_tree.column("id", width=40, anchor=tk.CENTER)
        self.approved_items_tree.column("name", width=250)
        self.approved_items_tree.column("category", width=120)
        self.approved_items_tree.column("seller", width=150)
        self.approved_items_tree.column("price", width=100, anchor=tk.E)
        self.approved_items_tree.column("approved_date", width=120)

        # Bind sự kiện double-click
        self.approved_items_tree.bind("<Double-1>", self.show_approved_item_details)

        self.approved_items_tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.approved_items_tree.yview)
        tree_scroll_x.config(command=self.approved_items_tree.xview)

        # Load dữ liệu ban đầu (sẽ gọi từ MainApplication)
        # self.load_approved_items_view()

    def setup_post_item_tab(self, tab):
        # Xóa widget cũ nếu có
        for widget in tab.winfo_children():
            widget.destroy()

        # Lưu trữ đường dẫn ảnh đã chọn
        self.selected_image_path = tk.StringVar(tab)

        form_frame = tk.Frame(tab)
        form_frame.pack(pady=10, padx=10, fill=tk.X)

        tk.Label(form_frame, text="Tên món đồ*:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.item_name_entry = tk.Entry(form_frame, width=50)
        self.item_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tk.Label(form_frame, text="Danh mục*:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.item_category_var = tk.StringVar(form_frame)
        # Dữ liệu categories sẽ được load từ DB và truyền vào đây
        self.item_category_combobox = ttk.Combobox(form_frame, textvariable=self.item_category_var, state="readonly", width=47)
        self.item_category_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        # Cần gọi hàm load_categories_into_combobox từ MainApplication

        tk.Label(form_frame, text="Mô tả:").grid(row=2, column=0, padx=5, pady=5, sticky="nw")
        self.item_description_text = tk.Text(form_frame, width=50, height=5)
        self.item_description_text.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        tk.Label(form_frame, text="Giá (VNĐ)*:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.item_price_entry = tk.Entry(form_frame, width=20)
        self.item_price_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        tk.Label(form_frame, text="(Nhập 0 nếu quyên góp/cho tặng)").grid(row=3, column=1, padx=(150, 5), pady=5, sticky="w")


        tk.Label(form_frame, text="Hình ảnh:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        image_frame = tk.Frame(form_frame)
        image_frame.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        select_image_button = tk.Button(image_frame, text="Chọn ảnh...", command=self.handle_select_image)
        select_image_button.pack(side=tk.LEFT)
        self.image_path_label = tk.Label(image_frame, textvariable=self.selected_image_path, relief=tk.SUNKEN, width=40, anchor='w')
        self.image_path_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)


        post_button = tk.Button(tab, text="Đăng bài", command=self.handle_post_item)
        post_button.pack(pady=15)

        # Cấu hình cột thứ 2 co giãn
        form_frame.columnconfigure(1, weight=1)

    def load_categories_into_combobox(self, categories):
        """Nạp danh sách categories vào Combobox."""
        self.categories_data = categories # Lưu lại để lấy ID sau này
        category_names = [cat['name'] for cat in categories]
        self.item_category_combobox['values'] = category_names
        if category_names:
            self.item_category_var.set(category_names[0]) # Chọn giá trị đầu tiên làm mặc định

    def handle_select_image(self):
        # Logic chọn ảnh sẽ được đặt trong main.py
        print("Nút chọn ảnh được nhấn")
        pass

    def handle_post_item(self):
        # Logic đăng bài sẽ được đặt trong main.py
        print("Nút đăng bài được nhấn")
        pass

    def clear_post_item_form(self):
        """Xóa dữ liệu trên form đăng bài."""
        self.item_name_entry.delete(0, tk.END)
        self.item_description_text.delete("1.0", tk.END)
        self.item_price_entry.delete(0, tk.END)
        self.selected_image_path.set("")
        # Reset combobox về giá trị đầu tiên nếu có
        if self.item_category_combobox['values']:
             self.item_category_var.set(self.item_category_combobox['values'][0])
        else:
             self.item_category_var.set("")

    def setup_campaigns_tab(self, tab):
        tk.Label(tab, text="Danh sách các chiến dịch/hoạt động đang diễn ra").pack(pady=10)
        # TODO: Hiển thị danh sách chiến dịch
        # TODO: Cho phép xem chi tiết, tham gia (nếu là user), tạo mới (nếu là admin/tổ chức)

    def setup_admin_tab(self, tab):
         notebook = ttk.Notebook(tab)

         # Sub-tab Quản lý người dùng
         user_mgmt_tab = ttk.Frame(notebook)
         notebook.add(user_mgmt_tab, text='Quản lý Người dùng')
         self.setup_user_management_tab(user_mgmt_tab)

         # Sub-tab Duyệt bài đăng
         item_approval_tab = ttk.Frame(notebook)
         notebook.add(item_approval_tab, text='Duyệt Bài đăng')
         self.setup_item_approval_tab(item_approval_tab) # Gọi hàm setup riêng

         # Sub-tab Quản lý Danh mục
         category_mgmt_tab = ttk.Frame(notebook)
         notebook.add(category_mgmt_tab, text='Quản lý Danh mục')
         self.setup_category_management_tab(category_mgmt_tab) # Gọi hàm setup riêng (sẽ tạo sau)


         # Sub-tab Báo cáo
         reports_tab = ttk.Frame(notebook)
         notebook.add(reports_tab, text='Báo cáo')
         tk.Label(reports_tab, text="Xem thống kê và báo cáo").pack(pady=5) # Tạm thời
         # TODO: Thêm các loại báo cáo cơ bản

         notebook.pack(expand=True, fill='both', pady=5)

    def setup_user_management_tab(self, tab):
        """Thiết lập giao diện cho tab Quản lý Người dùng."""
        # Frame chứa Treeview và Scrollbar
        tree_frame = tk.Frame(tab)
        tree_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Scrollbar
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = tk.Scrollbar(tree_frame, orient='horizontal')
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview để hiển thị danh sách người dùng
        self.user_tree = ttk.Treeview(tree_frame,
                                      columns=("id", "username", "name", "role", "grade", "org", "status", "created"),
                                      show="headings",
                                      yscrollcommand=tree_scroll_y.set,
                                      xscrollcommand=tree_scroll_x.set)

        # Định nghĩa các cột
        self.user_tree.heading("id", text="ID")
        self.user_tree.heading("username", text="Tên ĐN")
        self.user_tree.heading("name", text="Họ Tên")
        self.user_tree.heading("role", text="Vai trò")
        self.user_tree.heading("grade", text="Lớp")
        self.user_tree.heading("org", text="Tổ chức")
        self.user_tree.heading("status", text="Trạng thái")
        self.user_tree.heading("created", text="Ngày tạo")

        # Định dạng cột (chiều rộng)
        self.user_tree.column("id", width=40, anchor=tk.CENTER)
        self.user_tree.column("username", width=100)
        self.user_tree.column("name", width=150)
        self.user_tree.column("role", width=80, anchor=tk.CENTER)
        self.user_tree.column("grade", width=60, anchor=tk.CENTER)
        self.user_tree.column("org", width=100)
        self.user_tree.column("status", width=80, anchor=tk.CENTER)
        self.user_tree.column("created", width=120)

        self.user_tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.user_tree.yview)
        tree_scroll_x.config(command=self.user_tree.xview)

        # Frame chứa các nút hành động
        action_frame = tk.Frame(tab)
        action_frame.pack(pady=5, padx=10, fill=tk.X)

        refresh_button = tk.Button(action_frame, text="Làm mới", command=self.load_users_to_admin_view)
        refresh_button.pack(side=tk.LEFT, padx=5)

        toggle_active_button = tk.Button(action_frame, text="Khóa/Mở khóa", command=self.handle_toggle_user_status)
        toggle_active_button.pack(side=tk.LEFT, padx=5)

        delete_button = tk.Button(action_frame, text="Xóa người dùng", command=self.handle_delete_user, fg="red") # Thêm nút Xóa
        delete_button.pack(side=tk.LEFT, padx=5)

        # TODO: Thêm các nút khác nếu cần (Sửa...)

        # Load dữ liệu ban đầu (sẽ được gọi từ MainApplication)
        # self.load_users_to_admin_view()

    def setup_item_approval_tab(self, tab):
        """Thiết lập giao diện cho tab Duyệt Bài đăng."""
        # Frame chứa Treeview và Scrollbar
        tree_frame = tk.Frame(tab)
        tree_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Scrollbar
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = tk.Scrollbar(tree_frame, orient='horizontal')
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview để hiển thị danh sách đồ chờ duyệt
        self.pending_items_tree = ttk.Treeview(tree_frame,
                                               columns=("id", "name", "category", "user", "price", "created"),
                                               show="headings",
                                               yscrollcommand=tree_scroll_y.set,
                                               xscrollcommand=tree_scroll_x.set)

        # Định nghĩa các cột
        self.pending_items_tree.heading("id", text="ID")
        self.pending_items_tree.heading("name", text="Tên đồ")
        self.pending_items_tree.heading("category", text="Danh mục")
        self.pending_items_tree.heading("user", text="Người đăng")
        self.pending_items_tree.heading("price", text="Giá (VNĐ)")
        self.pending_items_tree.heading("created", text="Ngày đăng")

        # Định dạng cột
        self.pending_items_tree.column("id", width=40, anchor=tk.CENTER)
        self.pending_items_tree.column("name", width=200)
        self.pending_items_tree.column("category", width=120)
        self.pending_items_tree.column("user", width=100)
        self.pending_items_tree.column("price", width=80, anchor=tk.E)
        self.pending_items_tree.column("created", width=120)

        # Bind sự kiện double-click
        self.pending_items_tree.bind("<Double-1>", self.show_pending_item_details)

        self.pending_items_tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.pending_items_tree.yview)
        tree_scroll_x.config(command=self.pending_items_tree.xview)

        # Frame chứa các nút hành động
        action_frame = tk.Frame(tab)
        action_frame.pack(pady=5, padx=10, fill=tk.X)

        refresh_button = tk.Button(action_frame, text="Làm mới", command=self.load_pending_items_view)
        refresh_button.pack(side=tk.LEFT, padx=5)

        approve_button = tk.Button(action_frame, text="Duyệt", command=self.handle_approve_item, fg="green")
        approve_button.pack(side=tk.LEFT, padx=5)

        reject_button = tk.Button(action_frame, text="Từ chối", command=self.handle_reject_item, fg="red")
        reject_button.pack(side=tk.LEFT, padx=5)

        # Load dữ liệu ban đầu (sẽ gọi từ MainApplication)
        # self.load_pending_items_view()

    def setup_category_management_tab(self, tab):
         # Placeholder - Sẽ thêm giao diện quản lý danh mục sau
         tk.Label(tab, text="Chức năng Quản lý Danh mục đang phát triển").pack(pady=20)
         pass

    def setup_profile_tab(self, tab):
        """Thiết lập giao diện cho tab Hồ sơ cá nhân."""
        profile_frame = tk.Frame(tab)
        profile_frame.pack(pady=20, padx=20)

        tk.Label(profile_frame, text="Thông tin Hồ sơ", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # Các trường thông tin (hiển thị và cho phép sửa)
        tk.Label(profile_frame, text="Tên đăng nhập:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.profile_username_label = tk.Label(profile_frame, text="", width=30, anchor="w") # Không cho sửa username
        self.profile_username_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        tk.Label(profile_frame, text="Họ và tên*:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.profile_name_entry = tk.Entry(profile_frame, width=30)
        self.profile_name_entry.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(profile_frame, text="Vai trò:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.profile_role_label = tk.Label(profile_frame, text="", width=30, anchor="w") # Không cho sửa vai trò
        self.profile_role_label.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Trường Lớp (chỉ hiển thị cho student)
        self.profile_grade_label = tk.Label(profile_frame, text="Lớp:")
        self.profile_grade_entry = tk.Entry(profile_frame, width=30)

        # Trường Tổ chức (hiển thị cho student và teacher)
        self.profile_org_label = tk.Label(profile_frame, text="Tổ chức:")
        self.profile_org_entry = tk.Entry(profile_frame, width=30)

        # Các nút hành động
        button_frame = tk.Frame(profile_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=15) # Row có thể thay đổi

        save_profile_button = tk.Button(button_frame, text="Lưu thay đổi hồ sơ", command=self.handle_update_profile)
        save_profile_button.pack(side=tk.LEFT, padx=10)

        change_password_button = tk.Button(button_frame, text="Đổi mật khẩu", command=self.handle_change_password)
        change_password_button.pack(side=tk.LEFT, padx=10)

        # Load dữ liệu ban đầu (sẽ gọi từ MainApplication)
        # self.load_profile_data()

    def load_profile_data(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu load profile data")
        pass

    def handle_update_profile(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu cập nhật profile")
        pass

    def handle_change_password(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu đổi mật khẩu")
        pass

    def handle_delete_user(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu xóa user")
        pass

    def load_users_to_admin_view(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu load users")
        pass

    def handle_toggle_user_status(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu khóa/mở khóa user")
        pass

    def load_pending_items_view(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu load pending items")
        pass

    def handle_approve_item(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu duyệt item")
        pass

    def handle_reject_item(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu từ chối item")
        pass

    def handle_logout(self):
        self.current_user = None
        self.main_frame.pack_forget() # Ẩn frame chính
        # Đảm bảo quay về màn hình đăng nhập khi logout
        self.register_frame.pack_forget() # Ẩn luôn frame đăng ký nếu đang mở
        self.setup_login_frame() # Tạo lại widget đăng nhập
        self.login_frame.pack(pady=20) # Hiển thị lại frame đăng nhập

    def setup_my_items_tab(self, tab):
        """Thiết lập giao diện cho tab Đồ của tôi."""
        # Frame chứa Treeview và Scrollbar
        tree_frame = tk.Frame(tab)
        tree_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Scrollbar
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = tk.Scrollbar(tree_frame, orient='horizontal')
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview để hiển thị danh sách đồ đã đăng
        self.my_items_tree = ttk.Treeview(tree_frame,
                                          columns=("id", "name", "category", "price", "status", "created"),
                                          show="headings",
                                          yscrollcommand=tree_scroll_y.set,
                                          xscrollcommand=tree_scroll_x.set)

        # Định nghĩa các cột
        self.my_items_tree.heading("id", text="ID")
        self.my_items_tree.heading("name", text="Tên đồ")
        self.my_items_tree.heading("category", text="Danh mục")
        self.my_items_tree.heading("price", text="Giá (VNĐ)")
        self.my_items_tree.heading("status", text="Trạng thái")
        self.my_items_tree.heading("created", text="Ngày đăng")

        # Định dạng cột
        self.my_items_tree.column("id", width=40, anchor=tk.CENTER)
        self.my_items_tree.column("name", width=200)
        self.my_items_tree.column("category", width=120)
        self.my_items_tree.column("price", width=80, anchor=tk.E)
        self.my_items_tree.column("status", width=100, anchor=tk.CENTER)
        self.my_items_tree.column("created", width=120)

        self.my_items_tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.my_items_tree.yview)
        tree_scroll_x.config(command=self.my_items_tree.xview)

        # Frame chứa các nút hành động
        action_frame = tk.Frame(tab)
        action_frame.pack(pady=5, padx=10, fill=tk.X)

        refresh_button = tk.Button(action_frame, text="Làm mới", command=self.load_my_items_view)
        refresh_button.pack(side=tk.LEFT, padx=5)

        edit_button = tk.Button(action_frame, text="Sửa", command=self.handle_edit_my_item)
        edit_button.pack(side=tk.LEFT, padx=5)

        delete_button = tk.Button(action_frame, text="Xóa", command=self.handle_delete_my_item, fg="red")
        delete_button.pack(side=tk.LEFT, padx=5)

        # Load dữ liệu ban đầu (sẽ gọi từ MainApplication)
        # self.load_my_items_view()

    def load_my_items_view(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu load my items")
        pass

    def handle_edit_my_item(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu sửa item")
        pass

    def handle_delete_my_item(self):
        # Placeholder - Logic sẽ ở MainApplication
        print("UI: Yêu cầu xóa item")
        pass

    def load_approved_items_view(self):
         # Placeholder - Logic sẽ ở MainApplication
         print("UI: Yêu cầu load approved items")
         pass

    def show_approved_item_details(self, event):
         # Placeholder - Logic sẽ ở MainApplication
         print("UI: Yêu cầu hiển thị chi tiết item đã duyệt")
         pass

    def show_pending_item_details(self, event):
         # Placeholder - Logic sẽ ở MainApplication
         print("UI: Yêu cầu hiển thị chi tiết item chờ duyệt")
         pass

# Các hàm xử lý sự kiện khác (đăng bài, duyệt bài, ...) sẽ được thêm vào đây
# và gọi các hàm tương ứng trong database.py
