"""
UI 现代化改造演示 —— CustomTkinter 方案
对比当前 Tkinter 风格和现代 CustomTkinter 风格
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

# ==================== 主题设置 ====================
ctk.set_appearance_mode("dark")      # 暗色模式
ctk.set_default_color_theme("blue")  # 蓝色主题

# ==================== 演示窗口 ====================
class ModernDemo:
    def __init__(self):
        self.win = ctk.CTk()
        self.win.title("UI 现代化改造演示 - CustomTkinter")
        self.win.geometry("1100x750")
        self.win.minsize(900, 600)

        # ========== 顶部工具栏 ==========
        toolbar = ctk.CTkFrame(self.win, height=40, corner_radius=0)
        toolbar.pack(fill=tk.X, side=tk.TOP)
        toolbar.pack_propagate(False)

        ctk.CTkLabel(toolbar, text="多视角切换管理器",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side=tk.LEFT, padx=15, pady=5)

        for text in ("一键启动", "全部停止", "监视器", "☰ 更多"):
            btn = ctk.CTkButton(toolbar, text=text, width=90, height=30)
            btn.pack(side=tk.LEFT, padx=5, pady=5)

        # 主题切换
        theme_menu = ctk.CTkOptionMenu(toolbar, values=["深色", "浅色", "蓝色"],
                                       command=lambda v: self._switch_theme(v),
                                       width=80, height=30)
        theme_menu.pack(side=tk.RIGHT, padx=15, pady=5)

        # ========== 主内容区 ==========
        main = ctk.CTkFrame(self.win)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ----- 左侧: 选手仓库 -----
        left_frame = ctk.CTkFrame(main)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ctk.CTkLabel(left_frame, text="选手仓库",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor=tk.W, padx=10, pady=(10, 5))

        # 选手表格 (用 ScrollableFrame 模拟)
        store_frame = ctk.CTkScrollableFrame(left_frame, height=250)
        store_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 模拟选手数据
        players = [
            ("meuyou1", "Twitch", "1", "● 推流中"),
            ("lyasyaa", "Twitch", "2", "✕ 离线"),
            ("甜药", "B站", "8", "🌐 网页"),
            ("猫猫", "B站", "e", "🌐 网页"),
            ("抖音测试", "抖音", "f", "🌐 网页"),
            ("刘", "B站", "g", "🌐 网页"),
            ("imperialhal__", "Twitch", "9", "● 推流中"),
            ("aceu", "Twitch", "a", "✕ 离线"),
        ]
        for name, plat, hotkey, status in players:
            row = ctk.CTkFrame(store_frame, height=36, fg_color="transparent")
            row.pack(fill=tk.X, padx=3, pady=1)
            ctk.CTkLabel(row, text=f"☐", width=20).pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=name, width=100, anchor=tk.W,
                         font=ctk.CTkFont(size=12)).pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=plat, width=60,
                         fg_color=("#3B8ED0", "#1F6AA5") if plat=="Twitch" else ("#FB8C00", "#BF6A00"),
                         corner_radius=8, height=22).pack(side=tk.LEFT, padx=5)
            ctk.CTkLabel(row, text=hotkey, width=30).pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=status, width=80).pack(side=tk.LEFT)

        # 底部操作按钮
        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="+ 添加", width=70, height=28).pack(side=tk.LEFT, padx=2)
        ctk.CTkButton(btn_frame, text="✎ 编辑", width=70, height=28,
                      fg_color="transparent", border_width=1).pack(side=tk.LEFT, padx=2)
        ctk.CTkButton(btn_frame, text="✕ 删除", width=70, height=28,
                      fg_color="transparent", border_width=1,
                      text_color=("#D32F2F", "#EF5350")).pack(side=tk.LEFT, padx=2)

        # ----- 右侧: 视角列表 + 当前视角 + 日志 -----
        right_frame = ctk.CTkFrame(main)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # 视角列表
        ctk.CTkLabel(right_frame, text="活跃视角",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor=tk.W, padx=10, pady=(10, 5))

        pool_frame = ctk.CTkScrollableFrame(right_frame, height=150)
        pool_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for i, (name, _) in enumerate([("甜药 (8)", "bilibili"), ("刘 (g)", "bilibili")]):
            row = ctk.CTkFrame(pool_frame, height=32, fg_color="transparent")
            row.pack(fill=tk.X, padx=3, pady=1)
            ctk.CTkLabel(row, text=f"#{i+1}", width=30).pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=name, anchor=tk.W,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 当前视角
        current_frame = ctk.CTkFrame(right_frame, height=70, corner_radius=8)
        current_frame.pack(fill=tk.X, padx=10, pady=10)
        current_frame.pack_propagate(False)
        ctk.CTkLabel(current_frame, text="当前视角",
                     font=ctk.CTkFont(size=11)).pack(anchor=tk.W, padx=15, pady=(10, 0))
        self.current_label = ctk.CTkLabel(current_frame, text="甜药 (8级 - B站)",
                                          font=ctk.CTkFont(size=20, weight="bold"),
                                          text_color=("#3B8ED0", "#4DA6FF"))
        self.current_label.pack(anchor=tk.W, padx=15, pady=(0, 10))

        # 日志窗口
        ctk.CTkLabel(right_frame, text="系统日志",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(anchor=tk.W, padx=10, pady=(5, 2))

        self.log_box = ctk.CTkTextbox(right_frame, height=120, font=ctk.CTkFont(size=11))
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_box.insert("1.0", "[系统] 配置文件加载成功\n"
                                    "[系统] OBS 连接成功\n"
                                    "[系统] MediaMTX 已启动 (player1-50)\n"
                                    "[系统] [监视器-B站-步骤6] VLC 已启动: 刘\n")

        # ----- 状态栏 -----
        status = ctk.CTkFrame(self.win, height=28, corner_radius=0)
        status.pack(fill=tk.X, side=tk.BOTTOM)
        status.pack_propagate(False)
        ctk.CTkLabel(status, text="OBS: 已连接  |  MediaMTX: 运行中  |  快捷键: Alt+数字键",
                     font=ctk.CTkFont(size=10)).pack(side=tk.LEFT, padx=15)

    def _switch_theme(self, mode):
        if mode == "深色":
            ctk.set_appearance_mode("dark")
        elif mode == "浅色":
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("dark")

    def run(self):
        self.win.mainloop()


if __name__ == "__main__":
    demo = ModernDemo()
    demo.run()