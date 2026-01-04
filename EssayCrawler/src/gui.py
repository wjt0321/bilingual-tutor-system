import customtkinter as ctk
import threading
import sqlite3
import tkinter as tk
from tkinter import ttk
from src.main import EssayCrawlerSystem

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("作文自动爬取工具")
        self.geometry("900x600")

        self.system = EssayCrawlerSystem()
        self.system.log_callback = self.update_log

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="爬取工具", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_dashboard = ctk.CTkButton(self.sidebar_frame, text="控制台", command=self.show_dashboard)
        self.btn_dashboard.grid(row=1, column=0, padx=20, pady=10)
        
        self.btn_library = ctk.CTkButton(self.sidebar_frame, text="文章库", command=self.show_library)
        self.btn_library.grid(row=2, column=0, padx=20, pady=10)

        # Main Frames
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.library_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")

        self.setup_dashboard()
        self.setup_library()

        self.show_dashboard()

    def setup_dashboard(self):
        self.dashboard_frame.grid_columnconfigure(0, weight=1)
        
        # Controls
        self.control_frame = ctk.CTkFrame(self.dashboard_frame)
        self.control_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        
        self.start_btn = ctk.CTkButton(self.control_frame, text="立即开始爬取", command=self.start_crawling)
        self.start_btn.pack(side="left", padx=20, pady=20)
        
        self.status_label = ctk.CTkLabel(self.control_frame, text="状态: 就绪")
        self.status_label.pack(side="left", padx=20)

        # Log Area
        self.log_box = ctk.CTkTextbox(self.dashboard_frame, width=400, height=300)
        self.log_box.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.log_box.insert("0.0", "System initialized...\n")

    def setup_library(self):
        self.library_frame.grid_columnconfigure(0, weight=1)
        
        # Refresh Button
        self.refresh_btn = ctk.CTkButton(self.library_frame, text="刷新列表", command=self.load_articles)
        self.refresh_btn.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Treeview (using standard tk for table)
        style = ttk.Style()
        style.theme_use("clam")
        
        self.tree = ttk.Treeview(self.library_frame, columns=("ID", "Title", "Category", "Words", "Date"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Title", text="标题")
        self.tree.heading("Category", text="分类")
        self.tree.heading("Words", text="字数")
        self.tree.heading("Date", text="时间")
        
        self.tree.column("ID", width=50)
        self.tree.column("Title", width=300)
        
        self.tree.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")

    def show_dashboard(self):
        self.library_frame.grid_forget()
        self.dashboard_frame.grid(row=0, column=1, sticky="nsew")

    def show_library(self):
        self.dashboard_frame.grid_forget()
        self.library_frame.grid(row=0, column=1, sticky="nsew")
        self.load_articles()

    def update_log(self, message):
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")

    def start_crawling(self):
        self.status_label.configure(text="状态: 正在运行...")
        self.start_btn.configure(state="disabled")
        
        thread = threading.Thread(target=self.run_crawler_thread)
        thread.daemon = True
        thread.start()

    def run_crawler_thread(self):
        try:
            self.system.run_single_job()
            self.status_label.configure(text="状态: 完成")
        except Exception as e:
            self.update_log(f"Error: {e}")
            self.status_label.configure(text="状态: 出错")
        finally:
            self.start_btn.configure(state="normal")

    def load_articles(self):
        # Clear current items
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        try:
            conn = sqlite3.connect(self.system.config['storage']['db_path'])
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, category, word_count, crawled_at FROM articles ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()
            for row in rows:
                self.tree.insert("", "end", values=row)
            conn.close()
        except Exception as e:
            self.update_log(f"DB Error: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
