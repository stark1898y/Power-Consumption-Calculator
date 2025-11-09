# main.py
"""
PowerConsume 功耗计算器
支持多种电池类型，计算设备续航时间或所需电池容量。
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import tkinter.simpledialog as simpledialog
import math
import json
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import platform
from fpdf import FPDF, YPos, XPos
import os
from datetime import datetime
import sys


import matplotlib.pyplot as plt

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
        self.root.title("PowerConsume 功耗计算器")
        # self.root.geometry("1200x800")
        self.root.geometry("1400x900")  # 从 1200x800 增大到 1400x900
        self.root.configure(bg="#f0f0f0")

        # 初始化电池老化模型参数
        self.battery_aging_model = {
            "linear": {"name": "线性衰减", "params": {"rate": 0.02}},
            "exponential": {"name": "指数衰减", "params": {"rate": 0.05}},
            "step": {"name": "阶跃衰减", "params": {"threshold": 0.8, "drop": 0.1}}
        }
        self.selected_aging_model = "linear"

        # 初始化放电曲线参数
        self.discharge_curve = {
            "model": "linear",
            "custom_points": [(0, 1.0), (0.5, 0.9), (1.0, 0.8)]
        }

        # 创建主框架并设置 grid 权重
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)

        # 设置行权重：让结果区域获得更多空间
        for i in range(9):  # 总共9行
            if i == 8:  # 最后一行（结果区域）权重最大
                main_frame.rowconfigure(i, weight=3)
            else:
                main_frame.rowconfigure(i, weight=0)

        # ==================== 电池信息区域 ====================
        battery_frame = ttk.LabelFrame(main_frame, text="电池信息", padding="10")
        battery_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # 第1行：电池类型、经验系数、老化模型
        ttk.Label(battery_frame, text="电池类型:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.battery_type_var = tk.StringVar(value="锂电池")
        battery_combo = ttk.Combobox(
            battery_frame,
            textvariable=self.battery_type_var,
            values=["锂电池", "一次性锂亚电池", "碱性干电池"],
            state="readonly",
            width=15
        )
        battery_combo.grid(row=0, column=1, padx=5, pady=5)
        battery_combo.bind("<<ComboboxSelected>>", self.on_battery_type_change)

        ttk.Label(battery_frame, text="经验系数:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.experience_factor_var = tk.StringVar(value="0.7")
        ttk.Entry(battery_frame, textvariable=self.experience_factor_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(battery_frame, text="老化模型:").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        self.aging_model_var = tk.StringVar(value="线性衰减")
        aging_models = [model["name"] for model in self.battery_aging_model.values()]
        aging_combo = ttk.Combobox(
            battery_frame,
            textvariable=self.aging_model_var,
            values=aging_models,
            state="readonly",
            width=15
        )
        aging_combo.grid(row=0, column=5, padx=5, pady=5)
        aging_combo.bind("<<ComboboxSelected>>", self.on_aging_model_change)

        # 第2行：串联/并联
        ttk.Label(battery_frame, text="串联个数:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.series_count_var = tk.StringVar(value="1")
        ttk.Entry(battery_frame, textvariable=self.series_count_var, width=5).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(battery_frame, text="并联个数:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.parallel_count_var = tk.StringVar(value="1")
        ttk.Entry(battery_frame, textvariable=self.parallel_count_var, width=5).grid(row=1, column=3, padx=5, pady=5)

        # 第3行：单节参数
        ttk.Label(battery_frame, text="单节电压 (V):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.cell_voltage_var = tk.StringVar(value="3.6")
        ttk.Entry(battery_frame, textvariable=self.cell_voltage_var, width=10).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(battery_frame, text="终止电压 (V):").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.end_voltage_var = tk.StringVar(value="3.0")
        ttk.Entry(battery_frame, textvariable=self.end_voltage_var, width=10).grid(row=2, column=3, padx=5, pady=5)

        ttk.Label(battery_frame, text="单节容量 (mAh)(从起始电压放电至终止电压的可用容量):").grid(row=2, column=4, sticky="w", padx=5, pady=5)
        self.cell_capacity_var = tk.StringVar(value="19000")
        ttk.Entry(battery_frame, textvariable=self.cell_capacity_var, width=10).grid(row=2, column=5, padx=5, pady=5)

        # 第4行：总参数（只读）
        ttk.Label(battery_frame, text="总电压 (V):").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.total_voltage_var = tk.StringVar(value="3.6")
        ttk.Entry(battery_frame, textvariable=self.total_voltage_var, width=10, state="readonly").grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(battery_frame, text="总终止电压 (V):").grid(row=3, column=2, sticky="w", padx=5, pady=5)
        self.total_end_voltage_var = tk.StringVar(value="3.0")
        ttk.Entry(battery_frame, textvariable=self.total_end_voltage_var, width=10, state="readonly").grid(row=3, column=3, padx=5, pady=5)

        ttk.Label(battery_frame, text="总容量 (mAh):").grid(row=3, column=4, sticky="w", padx=5, pady=5)
        self.total_capacity_var = tk.StringVar(value="19000")
        ttk.Entry(battery_frame, textvariable=self.total_capacity_var, width=10, state="readonly").grid(row=3, column=5, padx=5, pady=5)

        # 绑定变化事件
        self.series_count_var.trace_add("write", self.update_total_values)
        self.parallel_count_var.trace_add("write", self.update_total_values)
        self.cell_voltage_var.trace_add("write", self.update_total_values)
        self.cell_capacity_var.trace_add("write", self.update_total_values)

        # ==================== 工作模式设置 ====================
        mode_frame = ttk.LabelFrame(main_frame, text="工作模式设置", padding="5")
        mode_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        table_container = ttk.Frame(mode_frame)
        table_container.pack(fill="x", pady=2)
        table_container.pack_propagate(False)
        table_container.configure(height=120)

        self.mode_table = ttk.Treeview(
            table_container,
            columns=("mode", "current_unit", "current_value", "duration_unit", "duration_value", "times_per_day"),
            show="headings",
            height=5
        )
        self.mode_table.heading("mode", text="模式")
        self.mode_table.column("mode", width=70, anchor="center")

        self.mode_table.heading("current_unit", text="电流单位")
        self.mode_table.column("current_unit", width=50, anchor="center")

        self.mode_table.heading("current_value", text="平均电流")
        self.mode_table.column("current_value", width=65, anchor="center")

        self.mode_table.heading("duration_unit", text="时长单位")
        self.mode_table.column("duration_unit", width=50, anchor="center")

        self.mode_table.heading("duration_value", text="时长值")
        self.mode_table.column("duration_value", width=65, anchor="center")

        self.mode_table.heading("times_per_day", text="每天次数")
        self.mode_table.column("times_per_day", width=65, anchor="center")

        xscroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.mode_table.xview)
        self.mode_table.configure(xscrollcommand=xscroll.set)
        self.mode_table.pack(side="top", fill="x")
        xscroll.pack(side="bottom", fill="x")

        self.setup_double_click_edit()

        btn_frame = ttk.Frame(mode_frame)
        btn_frame.pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="添加模式", command=self.add_mode).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除模式", command=self.delete_mode).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="清空模式", command=self.clear_modes).pack(side="left", padx=2)

        # ==================== 计算模式选择 ====================
        calc_frame = ttk.LabelFrame(main_frame, text="计算模式", padding="10")
        calc_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

        self.calc_mode = tk.StringVar(value="续航时间")
        ttk.Radiobutton(calc_frame, text="计算续航时间", variable=self.calc_mode, value="续航时间").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Radiobutton(calc_frame, text="计算所需容量", variable=self.calc_mode, value="所需容量").grid(row=0, column=1, sticky="w", padx=5)

        # ==================== 输入区域 ====================
        calc_area = ttk.Frame(main_frame)
        calc_area.grid(row=3, column=0, sticky="ew", padx=5, pady=5)

        ttk.Label(calc_area, text="输入:").grid(row=0, column=0, sticky="e", padx=5)
        self.input_var = tk.StringVar(value="5000")
        ttk.Entry(calc_area, textvariable=self.input_var, width=10).grid(row=0, column=1, padx=5)

        ttk.Label(calc_area, text="单位:").grid(row=0, column=2, sticky="w", padx=5)
        self.unit_var = tk.StringVar(value="天")
        unit_combo = ttk.Combobox(calc_area, textvariable=self.unit_var, values=["天", "h", "min"], width=5, state="readonly")
        unit_combo.grid(row=0, column=3, padx=5)

        ttk.Label(calc_area, text="(续航时间) 或 mAh (容量)").grid(row=0, column=4, sticky="w", padx=5)

        ttk.Button(calc_area, text="计算", command=self.calculate).grid(row=0, column=5, padx=10, sticky="e")

        # ==================== 操作按钮 ====================
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=4, column=0, sticky="ew", padx=5, pady=5)

        ttk.Button(action_frame, text="导出结果", command=self.export_result).pack(side="left", padx=5)
        ttk.Button(action_frame, text="保存配置", command=self.save_config).pack(side="left", padx=5)
        ttk.Button(action_frame, text="加载配置", command=self.load_config).pack(side="left", padx=5)
        ttk.Button(action_frame, text="导出PDF", command=self.export_pdf).pack(side="left", padx=5)
        ttk.Button(action_frame, text="显示图表", command=self.show_chart).pack(side="left", padx=5)

        # ==================== 结果展示 ====================
        result_frame = ttk.LabelFrame(main_frame, text="计算结果", padding="10")
        result_frame.grid(row=8, column=0, sticky="nsew", padx=5, pady=5)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            font=("Arial", 11),
            width=180,
            height=35,
            bg="white",
            relief="solid",
            padx=10,
            pady=10
        )
        self.result_text.grid(row=0, column=0, sticky="nsew")
        self.result_text.configure(state="disabled")
        # self.result_text.pack(fill="both", expand=True)
        # self.result_text.configure(state="disabled")

        # 初始化示例数据
        self.add_example_data()

    def show_about(self):
        """显示关于对话框"""
        about_text = (
            "PowerConsume 功耗计算器\n"
            "版本: 1.0.0\n"
            # "编译时间: 2025-04-05 10:30\n"
            # 用 datetime.now() 动态获取编译时间，但通常建议写死或从构建脚本注入。
            "作者: Yzy\n"
            "功能: 电池续航与容量计算"
        )
        messagebox.showinfo("关于", about_text)

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
            "锂电池": {"voltage": 3.6, "end_voltage": 3.0, "capacity": 19000, "series": 1, "parallel": 1},
            "一次性锂亚电池": {"voltage": 3.6, "end_voltage": 2.0, "capacity": 19000, "series": 1, "parallel": 2},
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
        self.mode_table.insert("", "end", values=("检测", "mA", "30", "s", "30.0", "48"))
        self.mode_table.insert("", "end", values=("上传", "mA", "40", "s", "20.0", "1"))
        self.mode_table.insert("", "end", values=("拍照+上传", "mA", "100", "s", "60.0", "1"))
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
        input_seconds = convert_to_seconds(input_ms, unit)
        average_voltage = (voltage + end_voltage) / 2
        total_energy_mwh = capacity * average_voltage
        usable_energy_mwh = total_energy_mwh * experience_factor
        days = usable_energy_mwh / daily_total_energy
        hours = days * 24
        years = days / 365.25

        result = f"总电压: {voltage:.2f} V\n"
        result += f"总容量: {capacity:.2f} mAh\n"
        result += f"平均电压: {average_voltage:.2f} V\n"
        result += f"总能量: {total_energy_mwh:.2f} mWh\n"
        result += f"可用能量: {usable_energy_mwh:.2f} mWh (×{experience_factor})\n"
        result += f"每日功耗: {daily_total_energy:.4f} mWh\n"
        result += f"可使用时间: {hours:.2f} 小时 ({days:.2f} 天, {years:.2f} 年)\n\n"
        result += "工作模式详情:\n"
        for mode in modes:
            result += f"  - {mode['name']}: {mode['current_ma']:.2f} mA, "
            result += f"{mode['seconds']:.2f} s, {mode['daily_energy_mwh']:.4f} mWh/天\n"

        self.display_result(result)
        self.last_calculation_result = {
            "type": "battery_life",
            "voltage": voltage,
            "capacity": capacity,
            "average_voltage": average_voltage,
            "total_energy_mwh": total_energy_mwh,
            "usable_energy_mwh": usable_energy_mwh,
            "experience_factor": experience_factor,
            "daily_total_energy": daily_total_energy,
            "days": days,
            "hours": hours,
            "years": years,
            "modes": modes
        }

    def _calculate_required_capacity(self, input_ms, voltage, experience_factor,
                                    daily_total_energy, modes, end_voltage):
        """计算所需电池容量"""
        input_seconds = convert_to_seconds(input_ms, "s")  # 转换为秒
        required_energy_mwh = daily_total_energy * (input_seconds / 86400)
        average_voltage = (voltage + end_voltage) / 2
        required_capacity = required_energy_mwh / (average_voltage * experience_factor)

        result = f"目标续航: {input_ms:.2f} ms ({input_seconds:.2f} 秒)\n"
        result += f"每日功耗: {daily_total_energy:.4f} mWh\n"
        result += f"所需容量: {required_capacity:.2f} mAh\n"
        result += f"(考虑了 {experience_factor} 的经验系数和平均电压)\n\n"
        result += "工作模式详情:\n"
        for mode in modes:
            result += f"  - {mode['name']}: {mode['current_ma']:.2f} mA, "
            result += f"{mode['seconds']:.2f} s, {mode['daily_energy_mwh']:.4f} mWh/天\n"

        self.display_result(result)
        self.last_calculation_result = {
            "type": "required_capacity",
            "input_ms": input_ms,
            "input_seconds": input_seconds,
            "voltage": voltage,
            "average_voltage": average_voltage,
            "experience_factor": experience_factor,
            "daily_total_energy": daily_total_energy,
            "required_energy_mwh": required_energy_mwh,
            "required_capacity": required_capacity,
            "modes": modes
        }

    def display_result(self, result):
        """显示计算结果"""
        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        self.result_text.configure(state="disabled")

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
        """导出计算结果为 PDF（完全支持中文，包含功耗分布图表）"""
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        result_text = self.result_text.get(1.0, tk.END).strip()
        if not result_text:
            messagebox.showwarning("警告", "没有计算结果可导出")
            return

        modes = []
        for item in self.mode_table.get_children():
            values = self.mode_table.item(item, "values")
            if len(values) >= 6:
                modes.append(values)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"功耗计算结果_{timestamp}.pdf"
        file_path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        try:
            pdf = FPDF()
            pdf.add_page()

            # === 关键修复：使用支持中文的字体 ===
            # 1. 优先尝试系统黑体（SimHei） - Windows 默认中文字体
            chinese_font = 'simhei'
            system_font_path = 'C:/Windows/Fonts/simhei.ttf'

            # 2. 检查系统字体是否存在
            if os.path.exists(system_font_path):
                print(f"使用系统字体: {system_font_path}")
                # ✅ 关键修复：同时注册常规字体和加粗字体
                pdf.add_font(chinese_font, '', system_font_path)  # 常规字体
                pdf.add_font(chinese_font, 'B', system_font_path)  # 加粗字体
            else:
                # 3. 如果系统字体不存在，尝试使用项目内字体
                project_font_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "fonts",
                    "simhei.ttf"
                )

                if os.path.exists(project_font_path):
                    print(f"使用项目内字体: {project_font_path}")
                    # ✅ 同时注册常规字体和加粗字体
                    pdf.add_font(chinese_font, '', project_font_path)
                    pdf.add_font(chinese_font, 'B', project_font_path)
                else:
                    # 4. 最后备选：使用系统宋体（SimSun）
                    fallback_font_path = 'C:/Windows/Fonts/simsun.ttc'
                    if os.path.exists(fallback_font_path):
                        print(f"使用备选字体: {fallback_font_path}")
                        # ✅ 同时注册常规字体和加粗字体
                        pdf.add_font(chinese_font, '', fallback_font_path)
                        pdf.add_font(chinese_font, 'B', fallback_font_path)
                    else:
                        # 5. 如果所有字体都失败，使用默认字体（不支持中文）
                        print("警告：无法加载中文字体，将使用Helvetica")
                        pdf.set_font('Helvetica', '', 12)
                        raise Exception("无法加载中文字体，PDF可能无法显示中文")

            # === 设置中文字体 ===
            pdf.set_font(chinese_font, '', 12)  # 常规字体

            # === 标题（加粗） ===
            pdf.set_font(chinese_font, 'B', 16)
            pdf.cell(0, 10, "PowerConsume 功耗计算结果", align="C", new_y=YPos.NEXT)
            pdf.ln(8)

            # === 原始结果文本（自动换行）===
            pdf.set_font(chinese_font, '', 11)
            for line in result_text.split('\n'):
                if line.strip() == "":
                    pdf.ln(4)
                else:
                    pdf.multi_cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            # === 工作模式表格 ===
            if modes:
                pdf.ln(10)
                # 表格标题（加粗）
                pdf.set_font(chinese_font, 'B', 12)
                pdf.cell(0, 10, "工作模式详情", new_y=YPos.NEXT)
                pdf.set_font(chinese_font, '', 10)

                col_widths = [30, 25, 25, 25, 25, 25]
                headers = ["模式", "电流值", "电流单位", "时长值", "时长单位", "每天次数"]

                # 表头
                for header, width in zip(headers, col_widths):
                    pdf.cell(width, 10, header, border=1, align="C")
                pdf.ln()

                # 数据行
                for mode in modes:
                    pdf.cell(col_widths[0], 10, str(mode[0]), border=1, align="C")
                    pdf.cell(col_widths[1], 10, str(mode[2]), border=1, align="C")
                    pdf.cell(col_widths[2], 10, str(mode[1]), border=1, align="C")
                    pdf.cell(col_widths[3], 10, str(mode[4]), border=1, align="C")
                    pdf.cell(col_widths[4], 10, str(mode[3]), border=1, align="C")
                    pdf.cell(col_widths[5], 10, str(mode[5]), border=1, align="C")
                    pdf.ln()

            # === 添加功耗分布图表 ===
            # 1. 创建图表
            fig, ax = plt.subplots(figsize=(10, 6))

            # 2. 准备数据
            mode_names = [mode[0] for mode in modes]
            energy_values = [float(mode[4]) * float(mode[5]) for mode in modes]

            # 3. 绘制柱状图
            bars = ax.bar(mode_names, energy_values,
                          color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'])

            # 4. 添加数值标签
            for bar, value in zip(bars, energy_values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(energy_values) * 0.01, f'{value:.2f}',
                        ha='center', va='bottom', fontsize=8)

            # 5. 设置图表属性
            ax.set_xlabel('工作模式', fontsize=10)
            ax.set_ylabel('每日能耗 (mWh)', fontsize=10)
            ax.set_title('功耗分布图', fontsize=12)
            ax.grid(axis='y', alpha=0.3)

            # 6. 旋转x轴标签以避免重叠
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=9)

            # 7. 调整布局
            plt.tight_layout()

            # 8. 保存图表为临时图片
            chart_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"chart_{timestamp}.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')

            # 9. 添加图片到PDF
            pdf.ln(10)
            pdf.set_font(chinese_font, 'B', 12)
            pdf.cell(0, 10, "功耗分布图", new_y=YPos.NEXT)
            pdf.image(chart_path, x=10, y=None, w=180)

            # 10. 清理临时图片
            plt.close(fig)  # 关闭图表以释放内存
            os.remove(chart_path)

            pdf.output(file_path)
            messagebox.showinfo("成功", f"PDF 已成功导出至：\n{file_path}")

        except Exception as e:
            messagebox.showerror("导出失败", f"生成 PDF 时出错：\n{str(e)}")

    def show_chart(self):
        """显示功耗分布图"""
        if not hasattr(self, 'last_calculation_result'):
            messagebox.showwarning("警告", "请先执行计算")
            return

        result = self.last_calculation_result
        modes = result['modes']
        names = [mode['name'] for mode in modes]
        daily_energy_mwh = [mode['daily_energy_mwh'] for mode in modes]

        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(names, daily_energy_mwh, color=['red', 'blue', 'green', 'orange'], alpha=0.7)

        # 添加数值标签
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width()/2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords='offset points',
                        ha='center', va='bottom')

        ax.set_xlabel('工作模式')
        ax.set_ylabel('每日能耗 (mWh)')
        ax.set_title('功耗分布图')
        ax.grid(axis='y', alpha=0.3)

        # 显示图表
        chart_window = tk.Toplevel(self.root)
        chart_window.title("功耗分布图")
        chart_window.geometry("800x600")

        canvas = FigureCanvasTkAgg(fig, chart_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = PowerConsumeCalculator(root)
    root.mainloop()
