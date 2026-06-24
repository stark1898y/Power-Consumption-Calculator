# main.py
"""
PowerConsume 功耗计算器
支持多种电池类型，计算设备续航时间或所需电池容量。
"""

# ==================== 版本信息 ====================
__version__ = "1.0.0"
__author__ = "Yzy"
__license__ = "MIT"

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import tkinter.simpledialog as simpledialog
import math
import json
# ==================== 颜色方案 ====================
COLORS = {
    "primary": "#667eea",       # 主色调 - 蓝紫
    "primary_dark": "#5a67d8",
    "secondary": "#764ba2",     # 辅助色 - 紫
    "accent": "#e67e22",        # 强调色 - 橙
    "success": "#48bb78",       # 成功 - 绿
    "danger": "#e53e3e",        # 危险 - 红
    "bg": "#f7fafc",            # 背景 - 浅灰
    "card_bg": "#ffffff",       # 卡片背景
    "text": "#2d3748",          # 主文字
    "text_light": "#718096",    # 次要文字
    "border": "#e2e8f0",        # 边框
    "header_start": "#667eea",  # 标题渐变起始
    "header_end": "#764ba2",    # 标题渐变结束
}

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import platform
from fpdf import FPDF, YPos, XPos
import os
from datetime import datetime
import sys
import webbrowser

# 全局设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def get_chinese_font_path():
    system = platform.system().lower()
    if system == "windows":
        return r"C:\Windows\Fonts\simhei.ttf"
    elif system == "darwin":  # macOS
        return "/System/Library/Fonts/PingFang.ttc"
    else:  # Linux
        return "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    return None

def convert_to_seconds(value: float, unit: str) -> float:
    """将任意单位的时间转换为秒"""
    if unit == "ms":
        return value / 1000
    elif unit == "min":
        return value * 60
    elif unit == "h":
        return value * 3600
    elif unit == "天":
        return value * 24 * 3600
    else:  # s
        return value


def convert_from_seconds(seconds: float, unit: str) -> float:
    """将秒转换为指定单位"""
    if unit == "ms":
        return seconds * 1000
    elif unit == "min":
        return seconds / 60
    elif unit == "h":
        return seconds / 3600
    elif unit == "天":
        return seconds / (24 * 3600)
    else:  # s
        return seconds


class PowerConsumeCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title(f"PowerConsume 功耗计算器 v{__version__}")
        self.root.geometry("1400x950")
        self.root.configure(bg=COLORS["bg"])
        self.root.minsize(1200, 800)

        # 初始化电池老化模型参数
        self.battery_aging_model = {
            "linear": {"name": "线性衰减", "params": {"rate": 0.02}},
            "exponential": {"name": "指数衰减", "params": {"rate": 0.05}},
            "step": {"name": "阶跃衰减", "params": {"threshold": 0.8, "drop": 0.1}}
        }
        self.selected_aging_model = "linear"
        self.discharge_curve = {"model": "linear", "custom_points": [(0, 1.0), (0.5, 0.9), (1.0, 0.8)]}

        # 设置样式
        self.setup_styles()

        # ==================== 标题横幅 ====================
        header = tk.Frame(root, bg=COLORS["primary"], height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="⚡ PowerConsume 功耗计算器",
            font=("Microsoft YaHei UI", 20, "bold"),
            fg="white", bg=COLORS["primary"]
        ).pack(side="left", padx=25, pady=15)

        tk.Label(
            header, text=f"v{__version__}",
            font=("Arial", 11),
            fg="#b8c4ff", bg=COLORS["primary"]
        ).pack(side="left", pady=15)

        # 右侧按钮
        btn_frame = tk.Frame(header, bg=COLORS["primary"])
        btn_frame.pack(side="right", padx=20, pady=15)
        self._make_header_btn(btn_frame, "关于", self.show_about).pack(side="right", padx=5)

        # ==================== 可滚动主区域 ====================
        container = ttk.Frame(root)
        container.pack(fill="both", expand=True, padx=15, pady=(10, 0))

        canvas = tk.Canvas(container, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        main_frame = ttk.Frame(canvas, padding="5")

        main_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 让 main_frame 宽度跟随 Canvas 自适应
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        main_frame.columnconfigure(0, weight=1)

        # ==================== 电池信息卡片 ====================
        battery_card = self._make_card(main_frame, "🔋 电池信息")
        battery_card.grid(row=0, column=0, sticky="ew", padx=5, pady=6)

        battery_inner = ttk.Frame(battery_card.body, style="Card.TFrame")
        battery_inner.pack(fill="x", padx=10, pady=(0, 10))
        # 让偶数列（标签列）和奇数列（输入列）均匀分布
        for c in range(6):
            battery_inner.columnconfigure(c, weight=1 if c % 2 == 1 else 0)

        # Row 0: 电池类型、经验系数、老化模型
        self._make_label(battery_inner, "电池类型:", 0, 0)
        self.battery_type_var = tk.StringVar(value="锂电池")
        battery_combo = ttk.Combobox(battery_inner, textvariable=self.battery_type_var,
                                     values=["锂电池", "一次性锂亚电池", "碱性干电池"],
                                     state="readonly", style="Custom.TCombobox")
        battery_combo.grid(row=0, column=1, padx=8, pady=5, sticky="ew")
        battery_combo.bind("<<ComboboxSelected>>", self.on_battery_type_change)

        self._make_label(battery_inner, "经验系数:", 0, 2)
        self.experience_factor_var = tk.StringVar(value="0.7")
        ttk.Entry(battery_inner, textvariable=self.experience_factor_var,
                  style="Custom.TEntry").grid(row=0, column=3, padx=8, pady=5, sticky="ew")

        self._make_label(battery_inner, "老化模型:", 0, 4)
        self.aging_model_var = tk.StringVar(value="线性衰减")
        aging_combo = ttk.Combobox(battery_inner, textvariable=self.aging_model_var,
                                   values=[m["name"] for m in self.battery_aging_model.values()],
                                   state="readonly", style="Custom.TCombobox")
        aging_combo.grid(row=0, column=5, padx=8, pady=5, sticky="ew")
        aging_combo.bind("<<ComboboxSelected>>", self.on_aging_model_change)

        # Row 1: 串联/并联
        self._make_label(battery_inner, "串联个数:", 1, 0)
        self.series_count_var = tk.StringVar(value="1")
        ttk.Entry(battery_inner, textvariable=self.series_count_var,
                  style="Custom.TEntry").grid(row=1, column=1, padx=8, pady=5, sticky="ew")

        self._make_label(battery_inner, "并联个数:", 1, 2)
        self.parallel_count_var = tk.StringVar(value="1")
        ttk.Entry(battery_inner, textvariable=self.parallel_count_var,
                  style="Custom.TEntry").grid(row=1, column=3, padx=8, pady=5, sticky="ew")

        # Row 2: 单节参数
        self._make_label(battery_inner, "单节电压 (V):", 2, 0)
        self.cell_voltage_var = tk.StringVar(value="3.6")
        ttk.Entry(battery_inner, textvariable=self.cell_voltage_var,
                  style="Custom.TEntry").grid(row=2, column=1, padx=8, pady=5, sticky="ew")

        self._make_label(battery_inner, "终止电压 (V):", 2, 2)
        self.end_voltage_var = tk.StringVar(value="3.0")
        ttk.Entry(battery_inner, textvariable=self.end_voltage_var,
                  style="Custom.TEntry").grid(row=2, column=3, padx=8, pady=5, sticky="ew")

        self._make_label(battery_inner, "单节容量 (mAh):", 2, 4)
        self.cell_capacity_var = tk.StringVar(value="19000")
        ttk.Entry(battery_inner, textvariable=self.cell_capacity_var,
                  style="Custom.TEntry").grid(row=2, column=5, padx=8, pady=5, sticky="ew")

        # Row 3: 总参数（只读，高亮显示）
        self._make_label(battery_inner, "总电压 (V):", 3, 0)
        self.total_voltage_var = tk.StringVar(value="3.6")
        ttk.Entry(battery_inner, textvariable=self.total_voltage_var,
                  style="Readonly.TEntry", state="readonly").grid(row=3, column=1, padx=8, pady=5, sticky="ew")

        self._make_label(battery_inner, "总终止电压 (V):", 3, 2)
        self.total_end_voltage_var = tk.StringVar(value="3.0")
        ttk.Entry(battery_inner, textvariable=self.total_end_voltage_var,
                  style="Readonly.TEntry", state="readonly").grid(row=3, column=3, padx=8, pady=5, sticky="ew")

        self._make_label(battery_inner, "总容量 (mAh):", 3, 4)
        self.total_capacity_var = tk.StringVar(value="19000")
        ttk.Entry(battery_inner, textvariable=self.total_capacity_var,
                  style="Readonly.TEntry", state="readonly").grid(row=3, column=5, padx=8, pady=5, sticky="ew")

        self.series_count_var.trace_add("write", self.update_total_values)
        self.parallel_count_var.trace_add("write", self.update_total_values)
        self.cell_voltage_var.trace_add("write", self.update_total_values)
        self.cell_capacity_var.trace_add("write", self.update_total_values)

        # ==================== 工作模式卡片 ====================
        mode_card = self._make_card(main_frame, "⚙️ 工作模式设置")
        mode_card.grid(row=1, column=0, sticky="ew", padx=5, pady=6)

        table_container = ttk.Frame(mode_card.body, style="Card.TFrame")
        table_container.pack(fill="both", padx=10, pady=(0, 5), expand=True)
        table_container.pack_propagate(False)
        table_container.configure(height=150)

        self.mode_table = ttk.Treeview(
            table_container,
            columns=("mode", "current_unit", "current_value", "duration_unit", "duration_value", "times_per_day"),
            show="headings", height=5, style="Custom.Treeview"
        )
        for col, text, w in [
            ("mode", "模式", 90), ("current_unit", "电流单位", 70),
            ("current_value", "平均电流", 80), ("duration_unit", "时长单位", 70),
            ("duration_value", "时长值", 80), ("times_per_day", "每天次数", 80)
        ]:
            self.mode_table.heading(col, text=text)
            self.mode_table.column(col, width=w, anchor="center")

        xscroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.mode_table.xview)
        self.mode_table.configure(xscrollcommand=xscroll.set)
        self.mode_table.pack(side="top", fill="x")
        xscroll.pack(side="bottom", fill="x")

        self.setup_double_click_edit()

        # 添加/删除模式按钮
        mode_btn_frame = ttk.Frame(mode_card.body, style="Card.TFrame")
        mode_btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        self._make_action_btn(mode_btn_frame, "➕ 添加模式", self.add_mode, "success").pack(side="left", padx=3)
        self._make_action_btn(mode_btn_frame, "➖ 删除模式", self.delete_mode, "danger").pack(side="left", padx=3)
        self._make_action_btn(mode_btn_frame, "🗑️ 清空模式", self.clear_modes, "danger").pack(side="left", padx=3)

        # ==================== 计算模式 + 输入 卡片 ====================
        calc_card = self._make_card(main_frame, "📊 计算设置")
        calc_card.grid(row=2, column=0, sticky="ew", padx=5, pady=6)

        calc_inner = ttk.Frame(calc_card.body, style="Card.TFrame")
        calc_inner.pack(fill="x", padx=10, pady=(0, 10))

        # 计算模式单选
        self.calc_mode = tk.StringVar(value="续航时间")
        ttk.Radiobutton(calc_inner, text="🔋 计算续航时间", variable=self.calc_mode,
                        value="续航时间", style="Custom.TRadiobutton").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        ttk.Radiobutton(calc_inner, text="📏 计算所需容量", variable=self.calc_mode,
                        value="所需容量", style="Custom.TRadiobutton").grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # 输入区域
        self._make_label(calc_inner, "输入值:", 1, 0)
        self.input_var = tk.StringVar(value="5000")
        ttk.Entry(calc_inner, textvariable=self.input_var,
                  style="Custom.TEntry").grid(row=1, column=1, padx=8, pady=5, sticky="ew")

        self._make_label(calc_inner, "单位:", 1, 2)
        self.unit_var = tk.StringVar(value="天")
        ttk.Combobox(calc_inner, textvariable=self.unit_var, values=["天", "h", "min"],
                     state="readonly", style="Custom.TCombobox").grid(row=1, column=3, padx=8, pady=5, sticky="ew")

        ttk.Label(calc_inner, text="(续航时间) 或 mAh (容量)",
                  font=("Arial", 9), foreground=COLORS["text_light"],
                  background=COLORS["card_bg"]).grid(row=1, column=4, padx=8, sticky="w")

        # 主计算按钮
        calc_btn = tk.Button(
            calc_inner, text="🧮 计 算", font=("Microsoft YaHei UI", 12, "bold"),
            fg="white", bg=COLORS["primary"], activebackground=COLORS["primary_dark"],
            activeforeground="white", relief="flat", cursor="hand2",
            padx=30, pady=6, command=self.calculate
        )
        calc_btn.grid(row=0, column=5, rowspan=2, padx=20, pady=5, sticky="e")
        calc_inner.columnconfigure(5, weight=1)

        # ==================== 操作按钮栏 ====================
        action_card = ttk.Frame(main_frame, style="Card.TFrame")
        action_card.grid(row=3, column=0, sticky="ew", padx=5, pady=6)

        for text, cmd, color_key in [
            ("📄 导出结果", self.export_result, "primary"),
            ("💾 保存配置", self.save_config, "success"),
            ("📂 加载配置", self.load_config, "success"),
            ("📑 导出 PDF", self.export_pdf, "accent"),
            ("📈 显示图表", self.show_chart, "secondary"),
            ("🗑️ 清空结果", self.clear_results, "danger"),
        ]:
            self._make_action_btn(action_card, text, cmd, color_key).pack(side="left", padx=4, pady=8)

        # ==================== 结果展示卡片 ====================
        result_card = self._make_card(main_frame, "📋 计算结果")
        result_card.grid(row=4, column=0, sticky="nsew", padx=5, pady=6)
        main_frame.rowconfigure(4, weight=1)

        # 左侧彩色指示条（放在 body 内部）
        indicator = tk.Frame(result_card.body, bg=COLORS["primary"], width=4)
        indicator.pack(side="left", fill="y", padx=(0, 0))

        result_inner = ttk.Frame(result_card.body, style="Card.TFrame")
        result_inner.pack(fill="both", expand=True, padx=5, pady=5)
        result_inner.columnconfigure(0, weight=1)
        result_inner.rowconfigure(0, weight=1)

        self.result_text = scrolledtext.ScrolledText(
            result_inner, wrap=tk.WORD,
            font=("Consolas", 11), fg=COLORS["text"],
            bg=COLORS["card_bg"], relief="flat",
            padx=15, pady=10, spacing1=2, spacing3=2,
            selectbackground=COLORS["primary"], selectforeground="white"
        )
        self.result_text.grid(row=0, column=0, sticky="nsew")
        self.result_text.configure(state="disabled")

        # 配置结果区域的标签样式
        self.result_text.tag_configure("title", font=("Microsoft YaHei UI", 13, "bold"),
                                       foreground=COLORS["primary"], spacing3=8)
        self.result_text.tag_configure("highlight", font=("Consolas", 12, "bold"),
                                       foreground=COLORS["accent"])
        self.result_text.tag_configure("success", font=("Consolas", 14, "bold"),
                                       foreground=COLORS["success"])
        self.result_text.tag_configure("label", foreground=COLORS["text_light"])
        self.result_text.tag_configure("value", font=("Consolas", 11, "bold"),
                                       foreground=COLORS["text"])
        self.result_text.tag_configure("separator", foreground=COLORS["border"])

        # 初始化示例数据
        self.add_example_data()

        # ==================== 底部状态栏 ====================
        status_frame = tk.Frame(root, bg=COLORS["border"], height=30)
        status_frame.pack(side="bottom", fill="x")
        status_frame.pack_propagate(False)

        tk.Label(
            status_frame,
            text=f"PowerConsume Calculator v{__version__}  © 2025 {__author__}  |  MIT License",
            font=("Arial", 9), fg=COLORS["text_light"], bg=COLORS["border"]
        ).pack(side="left", padx=15)

        tk.Label(status_frame, text="|", font=("Arial", 9),
                 fg="#cccccc", bg=COLORS["border"]).pack(side="right", padx=5)

        gitee_lbl = tk.Label(status_frame, text="Gitee", font=("Arial", 9, "underline"),
                             fg="#c71d23", bg=COLORS["border"], cursor="hand2")
        gitee_lbl.pack(side="right")
        gitee_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://gitee.com/stark1898/power-consumption-calculator"))

        github_lbl = tk.Label(status_frame, text="GitHub", font=("Arial", 9, "underline"),
                              fg=COLORS["primary"], bg=COLORS["border"], cursor="hand2")
        github_lbl.pack(side="right", padx=(0, 8))
        github_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/stark1898y/Power-Consumption-Calculator"))

    def show_about(self):
        """显示关于对话框"""
        about_text = (
            f"PowerConsume 功耗计算器\n"
            f"版本: v{__version__}\n"
            f"作者: {__author__}\n"
            f"许可证: {__license__}\n\n"
            f"功能: 电池续航与容量计算\n"
            f"支持: 锂电池 / 锂亚电池 / 碱性干电池\n"
            f"      串并联配置 / 多工作模式 / PDF导出\n\n"
            f"GitHub: github.com/stark1898y/Power-Consumption-Calculator\n"
            f"Gitee:  gitee.com/stark1898/power-consumption-calculator"
        )
        messagebox.showinfo("关于", about_text)

    # ==================== 样式和辅助方法 ====================

    def setup_styles(self):
        """设置 ttk 样式主题"""
        style = ttk.Style()
        style.theme_use("clam")

        # 全局
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"],
                        font=("Microsoft YaHei UI", 10))

        # 卡片框架
        style.configure("Card.TFrame", background=COLORS["card_bg"])
        style.configure("Card.TLabelframe", background=COLORS["card_bg"],
                        foreground=COLORS["text"], font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Card.TLabelframe.Label", background=COLORS["card_bg"],
                        foreground=COLORS["primary"], font=("Microsoft YaHei UI", 11, "bold"))

        # 输入框
        style.configure("Custom.TEntry", fieldbackground="white", borderwidth=2,
                        relief="solid", padding=5)
        style.map("Custom.TEntry",
                  fieldbackground=[("focus", "#fff5f0")],
                  bordercolor=[("focus", COLORS["primary"])])

        # 只读输入框
        style.configure("Readonly.TEntry", fieldbackground="#f0f4ff",
                        foreground=COLORS["primary"], borderwidth=2,
                        relief="solid", padding=5, font=("Consolas", 10, "bold"))

        # 下拉框
        style.configure("Custom.TCombobox", fieldbackground="white",
                        borderwidth=2, relief="solid", padding=5)
        style.map("Custom.TCombobox",
                  fieldbackground=[("focus", "#fff5f0")],
                  bordercolor=[("focus", COLORS["primary"])])

        # 单选按钮
        style.configure("Custom.TRadiobutton", background=COLORS["card_bg"],
                        font=("Microsoft YaHei UI", 10), padding=5)
        style.map("Custom.TRadiobutton",
                  foreground=[("selected", COLORS["primary"])])

        # Treeview 表格
        style.configure("Custom.Treeview", background="white",
                        fieldbackground="white", rowheight=28,
                        font=("Microsoft YaHei UI", 10))
        style.configure("Custom.Treeview.Heading",
                        background=COLORS["primary"], foreground="white",
                        font=("Microsoft YaHei UI", 10, "bold"), relief="flat")
        style.map("Custom.Treeview",
                  background=[("selected", COLORS["primary"])],
                  foreground=[("selected", "white")])
        style.map("Custom.Treeview.Heading",
                  background=[("active", COLORS["primary_dark"])])

    def _make_card(self, parent, title):
        """创建卡片式容器，返回 outer（用于布局），通过 card.body 访问内容区"""
        outer = tk.Frame(parent, bg=COLORS["border"], padx=1, pady=1)
        inner = tk.Frame(outer, bg=COLORS["card_bg"])
        inner.pack(fill="both", expand=True)
        outer.body = inner  # 暴露内容区给调用者

        # 标题栏
        header = tk.Frame(inner, bg=COLORS["card_bg"], height=35)
        header.pack(fill="x", padx=12, pady=(10, 5))
        header.pack_propagate(False)

        # 左侧色条
        tk.Frame(header, bg=COLORS["primary"], width=4).pack(side="left", fill="y", padx=(0, 8))
        tk.Label(header, text=title, font=("Microsoft YaHei UI", 11, "bold"),
                 fg=COLORS["text"], bg=COLORS["card_bg"]).pack(side="left")

        return outer

    def _make_label(self, parent, text, row, col):
        """创建统一样式的标签"""
        lbl = tk.Label(parent, text=text, font=("Microsoft YaHei UI", 10),
                       fg=COLORS["text_light"], bg=COLORS["card_bg"])
        lbl.grid(row=row, column=col, sticky="e", padx=(10, 2), pady=5)
        return lbl

    def _make_header_btn(self, parent, text, cmd):
        """标题栏按钮"""
        btn = tk.Button(parent, text=text, font=("Arial", 10),
                        fg="white", bg=COLORS["secondary"],
                        activebackground="#8e44ad", activeforeground="white",
                        relief="flat", cursor="hand2", padx=12, pady=3, command=cmd)
        return btn

    def _make_action_btn(self, parent, text, cmd, color_key="primary"):
        """操作按钮"""
        color = COLORS.get(color_key, COLORS["primary"])
        btn = tk.Button(parent, text=text, font=("Microsoft YaHei UI", 9),
                        fg="white", bg=color, activebackground=color,
                        activeforeground="white", relief="flat", cursor="hand2",
                        padx=10, pady=5, command=cmd)
        btn.configure(borderwidth=0)
        # hover 效果
        darker = self._darken_color(color, 0.85)
        btn.bind("<Enter>", lambda e: btn.configure(bg=darker))
        btn.bind("<Leave>", lambda e: btn.configure(bg=color))
        return btn

    @staticmethod
    def _darken_color(hex_color, factor=0.85):
        """将颜色变暗"""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def update_total_values(self, *args):
        """更新总电压、总容量和总终止电压"""
        try:
            series = int(self.series_count_var.get())
            parallel = int(self.parallel_count_var.get())
            cell_voltage = float(self.cell_voltage_var.get())
            cell_capacity = float(self.cell_capacity_var.get())
            end_voltage = float(self.end_voltage_var.get())

            total_voltage = cell_voltage * series
            total_capacity = cell_capacity * parallel
            total_end_voltage = end_voltage * series

            self.total_voltage_var.set(f"{total_voltage:.2f}")
            self.total_capacity_var.set(f"{total_capacity:.2f}")
            self.total_end_voltage_var.set(f"{total_end_voltage:.2f}")

        except ValueError:
            pass  # 忽略无效输入

    def on_battery_type_change(self, event=None):
        """根据电池类型自动填充默认参数"""
        battery_type = self.battery_type_var.get()
        default_settings = {
            "锂电池": {"voltage": 4.2, "end_voltage": 3.6, "capacity": 3500, "series": 1, "parallel": 1},
            "一次性锂亚电池": {"voltage": 3.6, "end_voltage": 3.3, "capacity": 19000, "series": 1, "parallel": 2},
            "碱性干电池": {"voltage": 1.5, "end_voltage": 1.0, "capacity": 2700, "series": 2, "parallel": 1}
        }

        if battery_type in default_settings:
            setting = default_settings[battery_type]
            self.cell_voltage_var.set(str(setting["voltage"]))
            self.end_voltage_var.set(str(setting["end_voltage"]))
            self.cell_capacity_var.set(str(setting["capacity"]))
            self.series_count_var.set(str(setting["series"]))
            self.parallel_count_var.set(str(setting["parallel"]))
            self.update_total_values()

    def on_aging_model_change(self, event=None):
        """根据选择的老化模型更新内部状态"""
        selected_name = self.aging_model_var.get()
        for key, model in self.battery_aging_model.items():
            if model["name"] == selected_name:
                self.selected_aging_model = key
                break

    def setup_double_click_edit(self):
        """双击编辑表格内容"""
        self.mode_table.bind("<Double-1>", self.on_double_click)
        self.mode_table.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        """点击列弹出单位下拉菜单"""
        col = self.mode_table.identify_column(event.x)
        item = self.mode_table.identify_row(event.y)
        if not item or col not in ("#2", "#4"):
            return

        values = self.mode_table.item(item, "values")
        current_value = values[1] if col == "#2" else values[3]

        options = ["uA", "mA"] if col == "#2" else ["ms", "s", "min", "h"]

        combo = ttk.Combobox(
            self.mode_table,
            values=options,
            width=5,
            state="readonly"
        )
        combo.set(current_value)

        x, y, w, h = self.mode_table.bbox(item, col)
        combo.place(x=x + 5, y=y + 5, width=w - 10, height=h - 5)

        def on_select(event):
            selected = combo.get()
            new_values = list(values)
            if col == "#2":
                new_values[1] = selected
            else:
                original_duration = float(new_values[4])
                old_unit = current_value
                seconds = convert_to_seconds(original_duration, old_unit)
                new_duration = convert_from_seconds(seconds, selected)
                new_values[3] = selected
                new_values[4] = new_duration
            self.mode_table.item(item, values=new_values)
            self.update_sleep_duration()
            combo.destroy()

        combo.bind("<<ComboboxSelected>>", on_select)
        combo.focus()

    def on_double_click(self, event):
        """双击编辑数值"""
        col = self.mode_table.identify_column(event.x)
        item = self.mode_table.identify_row(event.y)
        if not item:
            return

        values = self.mode_table.item(item, "values")
        column_index = None
        if col == "#3": column_index = 2
        elif col == "#5": column_index = 4
        elif col == "#6": column_index = 5
        if column_index is None:
            return

        current_value = str(values[column_index])
        entry = tk.Entry(self.mode_table, width=10, justify="center")
        entry.insert(0, current_value)

        x, y, w, h = self.mode_table.bbox(item, col)
        entry.place(x=x + 5, y=y + 5, width=w - 10, height=h - 5)

        def save_value(event=None):
            try:
                value = float(entry.get())
                if column_index == 5:
                    value = int(value)
                new_values = list(values)
                new_values[column_index] = value
                self.mode_table.item(item, values=new_values)
                entry.destroy()
                self.update_sleep_duration()
            except ValueError:
                messagebox.showerror("错误", "请输入有效数字")
                entry.destroy()

        entry.bind("<Return>", save_value)
        entry.bind("<FocusOut>", save_value)
        entry.bind("<Escape>", lambda e: entry.destroy())
        entry.focus()

    def add_mode(self):
        """添加一个新工作模式"""
        item_id = self.mode_table.insert("", "end",
                                         values=("模式" + str(len(self.mode_table.get_children()) + 1), "mA", "0", "s", "0", "1"))
        self.mode_table.selection_set(item_id)
        self.mode_table.focus(item_id)
        self.update_sleep_duration()

    def delete_mode(self):
        """删除选中的工作模式"""
        selected_items = self.mode_table.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的工作模式")
            return
        for item in selected_items:
            self.mode_table.delete(item)
        self.update_sleep_duration()

    def clear_modes(self):
        """清空所有工作模式"""
        self.mode_table.delete(*self.mode_table.get_children())
        self.update_sleep_duration()

    def add_example_data(self):
        """初始化示例数据"""
        self.mode_table.insert("", "end", values=("检测", "mA", "40", "s", "30.0", "48"))
        self.mode_table.insert("", "end", values=("上传", "mA", "50", "s", "20.0", "1"))
        self.mode_table.insert("", "end", values=("拍照+上传", "mA", "250", "s", "60.0", "1"))
        self.mode_table.insert("", "end", values=("休眠", "uA", "30", "s", "0", "1"))
        self.update_sleep_duration()

    def update_sleep_duration(self):
        """自动计算并更新休眠时间"""
        total_active_time = 0
        sleep_item = None
        total_time_per_day = 24 * 3600

        for item in self.mode_table.get_children():
            values = self.mode_table.item(item, "values")
            if len(values) < 6:
                continue
            if values[0] == "休眠":
                sleep_item = item
                continue
            try:
                duration_value = float(values[4])
                duration_unit = values[3]
                times_per_day = int(values[5])
                seconds = convert_to_seconds(duration_value, duration_unit)
                total_active_time += seconds * times_per_day
            except:
                continue

        if sleep_item:
            sleep_duration_seconds = max(0, total_time_per_day - total_active_time)
            sleep_values = self.mode_table.item(sleep_item, "values")
            sleep_unit = sleep_values[3]
            sleep_duration = convert_from_seconds(sleep_duration_seconds, sleep_unit)
            new_values = list(sleep_values)
            new_values[4] = sleep_duration
            self.mode_table.item(sleep_item, values=new_values)

    def calculate(self):
        """执行功耗计算"""
        try:
            series = int(self.series_count_var.get())
            parallel = int(self.parallel_count_var.get())
            cell_voltage = float(self.cell_voltage_var.get())
            end_voltage = float(self.end_voltage_var.get())
            cell_capacity = float(self.cell_capacity_var.get())
            experience_factor = float(self.experience_factor_var.get())

            total_voltage = cell_voltage * series
            total_capacity = cell_capacity * parallel
            average_voltage = (total_voltage + end_voltage * series) / 2

            if total_voltage <= 0 or end_voltage <= 0 or total_capacity <= 0:
                raise ValueError("电池参数必须为正数")
            if not (0 < experience_factor <= 1):
                raise ValueError("经验系数应在0到1之间")

            modes = self._get_mode_data(average_voltage)
            if not modes:
                messagebox.showwarning("警告", "请至少添加一个工作模式")
                return

            daily_total_energy = sum(mode['daily_energy_mwh'] for mode in modes)

            if self.calc_mode.get() == "续航时间":
                input_value = float(self.input_var.get())
                unit = self.unit_var.get()
                if input_value <= 0:
                    raise ValueError("输入值必须为正数")
                self._calculate_battery_life(
                    total_voltage, total_capacity, experience_factor,
                    daily_total_energy, modes, input_value, unit, end_voltage
                )
            elif self.calc_mode.get() == "所需容量":
                input_value = float(self.input_var.get())
                if input_value <= 0:
                    raise ValueError("输入值必须为正数")
                self._calculate_required_capacity(
                    input_value, total_voltage, experience_factor,
                    daily_total_energy, modes, end_voltage
                )

        except Exception as e:
            messagebox.showerror("错误", f"计算失败: {str(e)}")

    def _get_mode_data(self, voltage):
        """解析工作模式数据"""
        modes = []
        for item in self.mode_table.get_children():
            values = self.mode_table.item(item, "values")
            if len(values) < 6:
                continue
            try:
                current_unit = values[1]
                current_value = float(values[2])
                duration_unit = values[3]
                duration_value = float(values[4])
                times_per_day = int(values[5])

                current_ma = current_value / 1000 if current_unit == "uA" else current_value
                seconds = convert_to_seconds(duration_value, duration_unit)

                energy_per_cycle_mwh = (current_ma * seconds * voltage) / 3600
                daily_energy_mwh = energy_per_cycle_mwh * times_per_day

                modes.append({
                    'name': values[0],
                    'current_ma': current_ma,
                    'seconds': seconds,
                    'times_per_day': times_per_day,
                    'energy_per_cycle_mwh': energy_per_cycle_mwh,
                    'daily_energy_mwh': daily_energy_mwh
                })
            except Exception as e:
                print(f"解析模式失败: {e}")
                continue
        return modes

    def _calculate_battery_life(self, voltage, capacity, experience_factor,
                                daily_total_energy, modes, input_ms, unit, end_voltage):
        """计算电池续航时间"""
        average_voltage = (voltage + end_voltage) / 2
        total_energy_mwh = capacity * average_voltage
        usable_energy_mwh = total_energy_mwh * experience_factor
        days = usable_energy_mwh / daily_total_energy
        hours = days * 24
        years = days / 365.25

        # 使用富文本显示结果
        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)

        self.result_text.insert(tk.END, "  🔋 续航时间计算结果\n\n", "title")
        self.result_text.insert(tk.END, "─" * 50 + "\n", "separator")
        self.result_text.insert(tk.END, "  电池参数\n", "label")
        self.result_text.insert(tk.END, f"    总电压:     ", "label")
        self.result_text.insert(tk.END, f"{voltage:.2f} V\n", "value")
        self.result_text.insert(tk.END, f"    总容量:     ", "label")
        self.result_text.insert(tk.END, f"{capacity:.2f} mAh\n", "value")
        self.result_text.insert(tk.END, f"    平均电压:   ", "label")
        self.result_text.insert(tk.END, f"{average_voltage:.2f} V\n", "value")
        self.result_text.insert(tk.END, f"    总能量:     ", "label")
        self.result_text.insert(tk.END, f"{total_energy_mwh:.2f} mWh\n", "value")
        self.result_text.insert(tk.END, f"    可用能量:   ", "label")
        self.result_text.insert(tk.END, f"{usable_energy_mwh:.2f} mWh", "value")
        self.result_text.insert(tk.END, f"  (×{experience_factor})\n\n", "label")

        self.result_text.insert(tk.END, "─" * 50 + "\n", "separator")
        self.result_text.insert(tk.END, f"  每日功耗:   ", "label")
        self.result_text.insert(tk.END, f"{daily_total_energy:.4f} mWh\n\n", "highlight")

        self.result_text.insert(tk.END, "═" * 50 + "\n", "separator")
        self.result_text.insert(tk.END, f"  可使用时间: ", "label")
        self.result_text.insert(tk.END, f"{hours:.2f} 小时  ({days:.2f} 天, {years:.2f} 年)\n", "success")
        self.result_text.insert(tk.END, "═" * 50 + "\n\n", "separator")

        self.result_text.insert(tk.END, "  工作模式详情:\n", "label")
        for mode in modes:
            self.result_text.insert(tk.END, f"    • {mode['name']}: ", "value")
            self.result_text.insert(tk.END,
                f"{mode['current_ma']:.2f} mA, {mode['seconds']:.2f} s, {mode['daily_energy_mwh']:.4f} mWh/天\n", "label")

        self.result_text.configure(state="disabled")

        self.last_calculation_result = {
            "type": "battery_life", "voltage": voltage, "capacity": capacity,
            "average_voltage": average_voltage, "total_energy_mwh": total_energy_mwh,
            "usable_energy_mwh": usable_energy_mwh, "experience_factor": experience_factor,
            "daily_total_energy": daily_total_energy, "days": days, "hours": hours,
            "years": years, "modes": modes
        }

    def _calculate_required_capacity(self, input_ms, voltage, experience_factor,
                                    daily_total_energy, modes, end_voltage):
        """计算所需电池容量"""
        input_seconds = convert_to_seconds(input_ms, "s")
        required_energy_mwh = daily_total_energy * (input_seconds / 86400)
        average_voltage = (voltage + end_voltage) / 2
        required_capacity = required_energy_mwh / (average_voltage * experience_factor)

        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)

        self.result_text.insert(tk.END, "  📏 所需容量计算结果\n\n", "title")
        self.result_text.insert(tk.END, "─" * 50 + "\n", "separator")
        self.result_text.insert(tk.END, "  输入参数\n", "label")
        self.result_text.insert(tk.END, f"    目标续航:   ", "label")
        self.result_text.insert(tk.END, f"{input_ms:.2f} 天  ({input_seconds:.2f} 秒)\n", "value")
        self.result_text.insert(tk.END, f"    每日功耗:   ", "label")
        self.result_text.insert(tk.END, f"{daily_total_energy:.4f} mWh\n\n", "highlight")

        self.result_text.insert(tk.END, "═" * 50 + "\n", "separator")
        self.result_text.insert(tk.END, f"  所需容量:   ", "label")
        self.result_text.insert(tk.END, f"{required_capacity:.2f} mAh\n", "success")
        self.result_text.insert(tk.END, f"  (考虑了 {experience_factor} 的经验系数)\n", "label")
        self.result_text.insert(tk.END, "═" * 50 + "\n\n", "separator")

        self.result_text.insert(tk.END, "  工作模式详情:\n", "label")
        for mode in modes:
            self.result_text.insert(tk.END, f"    • {mode['name']}: ", "value")
            self.result_text.insert(tk.END,
                f"{mode['current_ma']:.2f} mA, {mode['seconds']:.2f} s, {mode['daily_energy_mwh']:.4f} mWh/天\n", "label")

        self.result_text.configure(state="disabled")

        self.last_calculation_result = {
            "type": "required_capacity", "input_ms": input_ms,
            "input_seconds": input_seconds, "voltage": voltage,
            "average_voltage": average_voltage, "experience_factor": experience_factor,
            "daily_total_energy": daily_total_energy,
            "required_energy_mwh": required_energy_mwh,
            "required_capacity": required_capacity, "modes": modes
        }

    def display_result(self, result):
        """显示计算结果"""
        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        self.result_text.configure(state="disabled")
    def clear_results(self):
        """清空计算结果"""
        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)
        self.result_text.configure(state="disabled")
        # 清空最后的计算结果存储
        if hasattr(self, 'last_calculation_result'):
            delattr(self, 'last_calculation_result')

    def export_result(self):
        """导出计算结果到文本文件"""
        result_text = self.result_text.get(1.0, tk.END)
        if not result_text.strip():
            messagebox.showwarning("警告", "没有结果可导出")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result_text)
                messagebox.showinfo("成功", f"结果已导出到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {str(e)}")

    def save_config(self):
        """保存当前配置到JSON文件"""
        config = {
            "battery_info": {
                "type": self.battery_type_var.get(),
                "experience_factor": self.experience_factor_var.get(),
                "series_count": self.series_count_var.get(),
                "parallel_count": self.parallel_count_var.get(),
                "cell_voltage": self.cell_voltage_var.get(),
                "end_voltage": self.end_voltage_var.get(),
                "cell_capacity": self.cell_capacity_var.get()
            },
            "aging_model": self.selected_aging_model,
            "discharge_curve": self.discharge_curve,
            "calc_mode": self.calc_mode.get(),
            "input_value": self.input_var.get(),
            "input_unit": self.unit_var.get(),
            "modes": []
        }

        # 保存工作模式
        for item in self.mode_table.get_children():
            values = self.mode_table.item(item, "values")
            if len(values) >= 6:
                config["modes"].append({
                    "mode": values[0],
                    "current_unit": values[1],
                    "current_value": values[2],
                    "duration_unit": values[3],
                    "duration_value": values[4],
                    "times_per_day": values[5]
                })

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("成功", f"配置已保存到:\n{file_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {str(e)}")

    def load_config(self):
        """从JSON文件加载配置"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 加载电池信息
                battery_info = config.get("battery_info", {})
                self.battery_type_var.set(battery_info.get("type", "锂电池"))
                self.experience_factor_var.set(battery_info.get("experience_factor", "0.7"))
                self.series_count_var.set(battery_info.get("series_count", "1"))
                self.parallel_count_var.set(battery_info.get("parallel_count", "1"))
                self.cell_voltage_var.set(battery_info.get("cell_voltage", "3.6"))
                self.end_voltage_var.set(battery_info.get("end_voltage", "3.0"))
                self.cell_capacity_var.set(battery_info.get("cell_capacity", "19000"))

                # 更新总值
                self.update_total_values()

                # 加载老化模型
                self.selected_aging_model = config.get("aging_model", "linear")
                aging_model_name = self.battery_aging_model[self.selected_aging_model]["name"]
                self.aging_model_var.set(aging_model_name)

                # 加载放电曲线
                self.discharge_curve = config.get("discharge_curve", {
                    "model": "linear",
                    "custom_points": [(0, 1.0), (0.5, 0.9), (1.0, 0.8)]
                })

                # 加载计算模式
                self.calc_mode.set(config.get("calc_mode", "续航时间"))
                self.input_var.set(config.get("input_value", "5000"))
                self.unit_var.set(config.get("input_unit", "天"))

                # 加载工作模式
                self.mode_table.delete(*self.mode_table.get_children())
                modes = config.get("modes", [])
                for mode in modes:
                    self.mode_table.insert("", "end", values=(
                        mode.get("mode", ""),
                        mode.get("current_unit", "mA"),
                        mode.get("current_value", "0"),
                        mode.get("duration_unit", "s"),
                        mode.get("duration_value", "0"),
                        mode.get("times_per_day", "1")
                    ))

                messagebox.showinfo("成功", "配置已加载")
            except Exception as e:
                messagebox.showerror("错误", f"加载失败: {str(e)}")

    def export_pdf(self):
        """导出计算结果为 PDF（卡片式 UI 风格，含功耗分布图表）"""
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        if not hasattr(self, 'last_calculation_result') or not self.last_calculation_result:
            messagebox.showwarning("警告", "没有计算结果可导出，请先执行计算")
            return

        result = self.last_calculation_result
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"功耗计算结果_{timestamp}.pdf"
        file_path = filedialog.asksaveasfilename(
            initialfile=default_name, defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        try:
            # ==================== 字体加载 ====================
            chinese_font = 'simhei'
            font_loaded = False
            for fp in [
                'C:/Windows/Fonts/simhei.ttf',
                'C:/Windows/Fonts/msyh.ttc',
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "simhei.ttf"),
                'C:/Windows/Fonts/simsun.ttc',
            ]:
                if os.path.exists(fp):
                    pdf_tmp = FPDF()
                    pdf_tmp.add_font(chinese_font, '', fp)
                    font_loaded = True
                    break
            if not font_loaded:
                raise Exception("无法加载中文字体")

            # ==================== 创建 PDF ====================
            pdf = FPDF()
            pdf.add_font(chinese_font, '', fp)
            pdf.add_font(chinese_font, 'B', fp)
            pdf.set_auto_page_break(auto=True, margin=25)
            pdf.add_page()

            # ==================== 辅助函数 ====================
            PRIMARY = (102, 126, 234)     # #667eea
            SECONDARY = (118, 75, 162)    # #764ba2
            TEXT_DARK = (45, 55, 72)      # #2d3748
            TEXT_LIGHT = (113, 128, 150)  # #718096
            BG_LIGHT = (247, 250, 252)    # #f7fafc
            BORDER = (226, 232, 240)      # #e2e8f0
            SUCCESS = (72, 187, 120)      # #48bb78

            def draw_header_banner():
                """绘制顶部渐变风格横幅"""
                pdf.set_fill_color(*PRIMARY)
                pdf.rect(0, 0, 210, 32, 'F')
                pdf.set_fill_color(*SECONDARY)
                pdf.rect(140, 0, 70, 32, 'F')
                pdf.set_xy(10, 8)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font(chinese_font, 'B', 18)
                pdf.cell(120, 8, "PowerConsume 功耗计算结果", new_x=XPos.RIGHT)
                pdf.set_font(chinese_font, '', 10)
                pdf.set_xy(10, 20)
                pdf.cell(120, 6, f"v{__version__}  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                pdf.set_text_color(*TEXT_DARK)

            def draw_section_title(title, y=None):
                """绘制带左侧色条的章节标题"""
                if y: pdf.set_y(y)
                pdf.ln(6)
                cy = pdf.get_y()
                pdf.set_fill_color(*PRIMARY)
                pdf.rect(10, cy, 3, 8, 'F')
                pdf.set_x(16)
                pdf.set_font(chinese_font, 'B', 13)
                pdf.set_text_color(*PRIMARY)
                pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(*TEXT_DARK)
                pdf.ln(2)

            def draw_kv_row(label, value, bold_value=False):
                """绘制键值对行"""
                pdf.set_font(chinese_font, '', 10)
                pdf.set_text_color(*TEXT_LIGHT)
                pdf.cell(55, 7, label, new_x=XPos.RIGHT)
                pdf.set_text_color(*TEXT_DARK)
                pdf.set_font(chinese_font, 'B' if bold_value else '', 10)
                pdf.cell(0, 7, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            def draw_footer():
                """绘制页脚"""
                pdf.set_y(-20)
                pdf.set_draw_color(*BORDER)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                pdf.ln(3)
                pdf.set_font(chinese_font, '', 8)
                pdf.set_text_color(*TEXT_LIGHT)
                pdf.cell(95, 5, f"PowerConsume Calculator v{__version__}  |  MIT License")
                pdf.cell(0, 5, f"Page {pdf.page_no()}", align="R")
                pdf.set_text_color(*TEXT_DARK)

            # ==================== 第一页：标题 + 结果概览 ====================
            draw_header_banner()
            pdf.set_y(38)

            # --- 计算结果概要 ---
            calc_mode = result.get('type', '')
            if calc_mode == 'battery_life':
                draw_section_title("计算结果概要")

                # 大号结果高亮框
                days = result.get('days', 0)
                box_y = pdf.get_y()
                pdf.set_fill_color(*BG_LIGHT)
                pdf.rect(10, box_y, 190, 22, 'F')
                pdf.set_xy(15, box_y + 3)
                pdf.set_font(chinese_font, '', 10)
                pdf.set_text_color(*TEXT_LIGHT)
                pdf.cell(40, 7, "电池续航时间：")
                pdf.set_text_color(*SUCCESS)
                pdf.set_font(chinese_font, 'B', 18)
                pdf.cell(60, 7, f"{days:.1f} 天")
                pdf.set_text_color(*TEXT_DARK)
                pdf.set_font(chinese_font, '', 10)
                pdf.cell(0, 7, f"  ({days * 24:.0f} 小时 / {days / 365.25:.2f} 年)")
                pdf.set_xy(15, box_y + 13)
                pdf.set_text_color(*TEXT_LIGHT)
                pdf.cell(40, 7, "每日总能耗：")
                pdf.set_text_color(*TEXT_DARK)
                pdf.set_font(chinese_font, 'B', 11)
                pdf.cell(0, 7, f"{result.get('daily_total_energy', 0):.4f} mWh/天")
                pdf.set_y(box_y + 26)

                # 详细参数
                draw_section_title("电池参数")
                draw_kv_row("总电压", f"{result.get('voltage', 0):.2f} V")
                draw_kv_row("总容量", f"{result.get('capacity', 0):.1f} mAh")
                draw_kv_row("平均电压", f"{result.get('average_voltage', 0):.2f} V")
                draw_kv_row("总能量", f"{result.get('total_energy_mwh', 0):.1f} mWh")
                draw_kv_row("经验系数", f"{result.get('experience_factor', 0)}")
                draw_kv_row("可用能量", f"{result.get('usable_energy_mwh', 0):.1f} mWh", bold_value=True)

            elif calc_mode == 'required_capacity':
                draw_section_title("计算结果概要")

                req_cap = result.get('required_capacity', 0)
                box_y = pdf.get_y()
                pdf.set_fill_color(*BG_LIGHT)
                pdf.rect(10, box_y, 190, 22, 'F')
                pdf.set_xy(15, box_y + 3)
                pdf.set_font(chinese_font, '', 10)
                pdf.set_text_color(*TEXT_LIGHT)
                pdf.cell(50, 7, "所需电池容量：")
                pdf.set_text_color(*SUCCESS)
                pdf.set_font(chinese_font, 'B', 18)
                pdf.cell(0, 7, f"{req_cap:.1f} mAh")
                pdf.set_xy(15, box_y + 13)
                pdf.set_text_color(*TEXT_LIGHT)
                pdf.cell(50, 7, "所需能量：")
                pdf.set_text_color(*TEXT_DARK)
                pdf.set_font(chinese_font, 'B', 11)
                pdf.cell(0, 7, f"{result.get('required_energy_mwh', 0):.1f} mWh")
                pdf.set_y(box_y + 26)

                draw_section_title("输入参数")
                draw_kv_row("目标天数", f"{result.get('input_value', 0)} {result.get('input_unit', '天')}")
                draw_kv_row("总电压", f"{result.get('voltage', 0):.2f} V")
                draw_kv_row("平均电压", f"{result.get('average_voltage', 0):.2f} V")
                draw_kv_row("经验系数", f"{result.get('experience_factor', 0)}")
                draw_kv_row("每日总能耗", f"{result.get('daily_total_energy', 0):.4f} mWh")

            # ==================== 工作模式表格 ====================
            calc_modes = result.get('modes', [])
            if calc_modes:
                draw_section_title("工作模式详情")

                # 表头（彩色背景）
                col_widths = [28, 28, 18, 28, 18, 18, 24, 28]
                headers = ["模式", "电流", "单位", "时长", "单位", "次数", "单次能耗", "每日能耗"]
                pdf.set_fill_color(*PRIMARY)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font(chinese_font, 'B', 9)
                for h, w in zip(headers, col_widths):
                    pdf.cell(w, 8, h, border=1, fill=True, align="C")
                pdf.ln()

                # 数据行（交替背景色）
                pdf.set_text_color(*TEXT_DARK)
                pdf.set_font(chinese_font, '', 9)
                for i, m in enumerate(calc_modes):
                    if i % 2 == 0:
                        pdf.set_fill_color(*BG_LIGHT)
                    else:
                        pdf.set_fill_color(255, 255, 255)
                    cells = [
                        str(m['name']),
                        f"{m['current_ma']:.3f}",
                        "mA",
                        f"{m['seconds']:.1f}",
                        "s",
                        str(m['times_per_day']),
                        f"{m['energy_per_cycle_mwh']:.4f}",
                        f"{m['daily_energy_mwh']:.4f}",
                    ]
                    for c, w in zip(cells, col_widths):
                        pdf.cell(w, 7, c, border=1, fill=True, align="C")
                    pdf.ln()

                # 合计行
                pdf.set_font(chinese_font, 'B', 9)
                pdf.set_fill_color(230, 230, 240)
                total_daily = sum(m['daily_energy_mwh'] for m in calc_modes)
                pdf.cell(sum(col_widths[:6]), 7, "合计每日能耗", border=1, fill=True, align="C")
                pdf.cell(col_widths[6], 7, "", border=1, fill=True, align="C")
                pdf.cell(col_widths[7], 7, f"{total_daily:.4f}", border=1, fill=True, align="C")
                pdf.ln()

            # ==================== 功耗分布图表（紧跟表格） ====================
            if calc_modes:
                mode_names = [m['name'] for m in calc_modes]
                energy_values = [m['daily_energy_mwh'] for m in calc_modes]
                total_energy = sum(energy_values)
                percentages = [(e / total_energy * 100) if total_energy > 0 else 0 for e in energy_values]

                chart_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD',
                                '#667eea', '#e67e22', '#48bb78', '#e53e3e']
                bar_colors = chart_colors[:len(mode_names)]

                # 剩余空间不足时手动换页，关闭 auto_page_break 防止自动分页
                chart_needs_new_page = pdf.get_y() > 140
                if chart_needs_new_page:
                    pdf.add_page()
                    pdf.set_y(15)
                pdf.auto_page_break = False  # 关键：禁止自动分页

                draw_section_title("功耗分布分析")

                # 控制图表高度使其适配 A4 页面宽度
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 3))
                fig.suptitle('功耗分布分析', fontsize=12, fontweight='bold', y=0.98)

                # 柱状图
                bars = ax1.bar(mode_names, energy_values, color=bar_colors, edgecolor='#333',
                               linewidth=1, alpha=0.85, width=0.6)
                for i, bar in enumerate(bars):
                    h = bar.get_height()
                    lbl = f'{h:.4f}' if h < 0.01 else f'{h:.2f}'
                    ax1.annotate(lbl, xy=(bar.get_x() + bar.get_width() / 2, h),
                                 xytext=(0, 4), textcoords='offset points',
                                 ha='center', va='bottom', fontsize=8, fontweight='bold')
                ax1.set_xlabel('工作模式', fontsize=10)
                ax1.set_ylabel('每日能耗 (mWh)', fontsize=10)
                ax1.set_title('各模式每日能耗', fontsize=11, fontweight='bold')
                ax1.grid(axis='y', alpha=0.3, linestyle='--')
                ax1.spines['top'].set_visible(False)
                ax1.spines['right'].set_visible(False)
                plt.setp(ax1.get_xticklabels(), rotation=30, ha="right", fontsize=9)

                # 环形图
                wedges, texts, autotexts = ax2.pie(
                    energy_values, labels=mode_names, colors=bar_colors,
                    autopct=lambda pct: f'{pct:.1f}%' if pct >= 3 else '',
                    startangle=90, pctdistance=0.75,
                    wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
                    textprops=dict(fontsize=9))
                for at in autotexts:
                    at.set_fontsize(9); at.set_fontweight('bold'); at.set_color('white')
                ax2.set_title('能耗占比分布', fontsize=11, fontweight='bold')
                legend_labels = [f'{mode_names[i]}  {percentages[i]:.1f}%' for i in range(len(mode_names))]
                ax2.legend(wedges, legend_labels, title='工作模式', loc='center left',
                           bbox_to_anchor=(1.0, 0, 0.5, 1), fontsize=9, title_fontsize=10)

                plt.tight_layout()
                chart_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"chart_{timestamp}.png")
                fig.savefig(chart_path, dpi=200, bbox_inches='tight', pad_inches=0.2)
                plt.close(fig)

                # 显式控制图片高度，避免 fpdf2 自动分页产生空白页
                # A4 有效宽度约 190mm，图表 3 英寸高 @ 200dpi → 约 42mm
                pdf.image(chart_path, x=10, w=190, h=48)
                pdf.auto_page_break = True   # 恢复自动分页
                if os.path.exists(chart_path):
                    os.remove(chart_path)

            # 绘制所有页的页脚
            total_pages = pdf.pages_count
            for i in range(1, total_pages + 1):
                pdf.page = i
                draw_footer()

            pdf.output(file_path)
            messagebox.showinfo("成功", f"PDF 已成功导出至：\n{file_path}")

        except Exception as e:
            messagebox.showerror("导出失败", f"生成 PDF 时出错：\n{str(e)}")

    def show_chart(self):
        """显示功耗分布图（柱状图 + 环形图）"""
        if not hasattr(self, 'last_calculation_result'):
            messagebox.showwarning("警告", "请先执行计算")
            return

        result = self.last_calculation_result
        modes = result['modes']
        names = [mode['name'] for mode in modes]
        daily_energy_mwh = [mode['daily_energy_mwh'] for mode in modes]

        total_energy = sum(daily_energy_mwh)
        if total_energy == 0:
            messagebox.showwarning("警告", "每日总能耗为 0，无法绘制图表")
            return
        percentages = [e / total_energy * 100 for e in daily_energy_mwh]

        # 配色方案（与网页版一致）
        chart_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD',
                        '#667eea', '#e67e22', '#48bb78', '#e53e3e']
        bar_colors = chart_colors[:len(names)]
        border_colors = ['#c0392b', '#16a085', '#2980b9', '#27ae60', '#f39c12', '#8e44ad',
                         '#5a67d8', '#d35400', '#38a169', '#c0392b']

        # 创建双图表窗口
        chart_window = tk.Toplevel(self.root)
        chart_window.title(f"功耗分布图 - PowerConsume v{__version__}")
        chart_window.geometry("1200x550")
        chart_window.configure(bg=COLORS["bg"])

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), facecolor=COLORS["bg"])
        fig.suptitle('功耗分布分析', fontsize=16, fontweight='bold', y=0.98)

        # ============ 左侧：柱状图（标注数值）============
        bars = ax1.bar(names, daily_energy_mwh, color=bar_colors, edgecolor=border_colors,
                       linewidth=1.5, alpha=0.85, width=0.6)
        for i, bar in enumerate(bars):
            height = bar.get_height()
            label = f'{height:.4f}' if height < 0.01 else f'{height:.2f}'
            ax1.annotate(label,
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 5), textcoords='offset points',
                         ha='center', va='bottom', fontsize=11, fontweight='bold',
                         color=COLORS["text"])

        ax1.set_xlabel('工作模式', fontsize=12)
        ax1.set_ylabel('每日能耗 (mWh)', fontsize=12)
        ax1.set_title('各模式每日能耗', fontsize=14, fontweight='bold', pad=10)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        ax1.set_facecolor(COLORS["bg"])
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)

        # ============ 右侧：环形图（标注百分比）============
        wedges, texts, autotexts = ax2.pie(
            daily_energy_mwh, labels=names, colors=bar_colors,
            autopct=lambda pct: f'{pct:.1f}%' if pct >= 3 else '',
            startangle=90, pctdistance=0.75,
            wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2),
            textprops=dict(fontsize=11)
        )
        # 百分比文字样式
        for at in autotexts:
            at.set_fontsize(11)
            at.set_fontweight('bold')
            at.set_color('white')

        ax2.set_title('能耗占比分布', fontsize=14, fontweight='bold', pad=10)

        # 右侧图例：模式名 + 百分比
        legend_labels = [f'{names[i]}  {percentages[i]:.1f}%  ({daily_energy_mwh[i]:.2f} mWh)'
                         for i in range(len(names))]
        ax2.legend(wedges, legend_labels, title='工作模式', loc='center left',
                   bbox_to_anchor=(1.0, 0, 0.5, 1), fontsize=10, title_fontsize=11)

        plt.tight_layout(rect=[0, 0, 1, 0.94])

        canvas = FigureCanvasTkAgg(fig, chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

def on_closing():
    # 执行清理操作
    print("程序正在退出...")
    root.destroy()  # 销毁窗口
    sys.exit()      # 退出程序

if __name__ == "__main__":
    root = tk.Tk()
    app = PowerConsumeCalculator(root)
    root.protocol("WM_DELETE_WINDOW", on_closing)  # 绑定关闭事件
    root.mainloop()
