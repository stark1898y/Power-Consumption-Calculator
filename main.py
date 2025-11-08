# main.py
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import tkinter.simpledialog as simpledialog
import math


def convert_to_seconds(value, unit):
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


def convert_from_seconds(seconds, unit):
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
        self.root.geometry("950x800")
        self.root.configure(bg="#f0f0f0")

        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill="both", expand=True)

        # ==================== 电池信息区域 ====================
        battery_frame = ttk.LabelFrame(main_frame, text="电池信息", padding="10")
        battery_frame.pack(fill="x", pady=10)

        # 第一行：电池类型 和 经验系数
        ttk.Label(battery_frame, text="电池类型:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.battery_type_var = tk.StringVar(value="锂电池")
        battery_type_combo = ttk.Combobox(battery_frame, textvariable=self.battery_type_var,
                                        values=["锂电池", "一次性锂亚电池", "碱性干电池"],
                                        state="readonly", width=15)
        battery_type_combo.grid(row=0, column=1, padx=5, pady=5)
        battery_type_combo.bind("<<ComboboxSelected>>", self.on_battery_type_change)

        ttk.Label(battery_frame, text="经验系数:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.experience_factor_var = tk.StringVar(value="0.7")
        ttk.Entry(battery_frame, textvariable=self.experience_factor_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        # 第二行：串联、并联个数
        ttk.Label(battery_frame, text="串联个数:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.series_count_var = tk.StringVar(value="1")
        ttk.Entry(battery_frame, textvariable=self.series_count_var, width=5).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(battery_frame, text="并联个数:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.parallel_count_var = tk.StringVar(value="1")
        ttk.Entry(battery_frame, textvariable=self.parallel_count_var, width=5).grid(row=1, column=3, padx=5, pady=5)

        # 第三行：单节电压、终止电压、单节容量
        ttk.Label(battery_frame, text="单节电压 (V):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.cell_voltage_var = tk.StringVar(value="3.6")
        ttk.Entry(battery_frame, textvariable=self.cell_voltage_var, width=10).grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(battery_frame, text="终止电压 (V):").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.end_voltage_var = tk.StringVar(value="3.0")
        ttk.Entry(battery_frame, textvariable=self.end_voltage_var, width=10).grid(row=2, column=3, padx=5, pady=5)

        ttk.Label(battery_frame, text="单节容量 (mAh):").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.cell_capacity_var = tk.StringVar(value="19000")
        ttk.Entry(battery_frame, textvariable=self.cell_capacity_var, width=10).grid(row=3, column=1, padx=5, pady=5)

        # 总电压和总容量（只读）
        ttk.Label(battery_frame, text="总电压 (V):").grid(row=3, column=2, sticky="w", padx=5, pady=5)
        self.total_voltage_var = tk.StringVar(value="3.6")
        ttk.Entry(battery_frame, textvariable=self.total_voltage_var, width=10, state="readonly").grid(row=3, column=3, padx=5, pady=5)

        # 新增：总终止电压
        ttk.Label(battery_frame, text="总终止电压 (V):").grid(row=4, column=2, sticky="w", padx=5, pady=5)
        self.total_end_voltage_var = tk.StringVar(value="3.0")
        ttk.Entry(battery_frame, textvariable=self.total_end_voltage_var, width=10, state="readonly").grid(row=4, column=3, padx=5, pady=5)

        ttk.Label(battery_frame, text="总容量 (mAh):").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.total_capacity_var = tk.StringVar(value="19000")
        ttk.Entry(battery_frame, textvariable=self.total_capacity_var, width=10, state="readonly").grid(row=4, column=1, padx=5, pady=5)

        # 绑定变化事件
        self.series_count_var.trace_add("write", self.update_total_values)
        self.parallel_count_var.trace_add("write", self.update_total_values)
        self.cell_voltage_var.trace_add("write", self.update_total_values)
        self.cell_capacity_var.trace_add("write", self.update_total_values)

        # ==================== 工作模式设置 ====================
        mode_frame = ttk.LabelFrame(main_frame, text="工作模式设置", padding="5")
        mode_frame.pack(fill="x", pady=10)

        # 表格容器
        table_container = ttk.Frame(mode_frame)
        table_container.pack(fill="x", pady=2)
        table_container.pack_propagate(False)
        table_container.configure(height=120)

        self.mode_table = ttk.Treeview(table_container,
                                       columns=("mode", "current_unit", "current_value", "duration_unit",
                                                "duration_value", "times_per_day"), show="headings",
                                                height=5)
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
        calc_frame.pack(fill="x", pady=10)

        self.calc_mode = tk.StringVar(value="续航时间")
        ttk.Radiobutton(calc_frame, text="计算续航时间", variable=self.calc_mode, value="续航时间").grid(row=0,
                                                                                                         column=0,
                                                                                                         sticky="w",
                                                                                                         padx=5)
        ttk.Radiobutton(calc_frame, text="计算所需容量", variable=self.calc_mode, value="所需容量").grid(row=0,
                                                                                                         column=1,
                                                                                                         sticky="w",
                                                                                                         padx=5)

        # ==================== 输入区域 ====================
        calc_area = ttk.Frame(main_frame)
        calc_area.pack(fill="x", pady=10)

        ttk.Label(calc_area, text="输入:").grid(row=0, column=0, sticky="e", padx=5)
        self.input_var = tk.StringVar(value="5000")
        ttk.Entry(calc_area, textvariable=self.input_var, width=10).grid(row=0, column=1, padx=5)

        # 单位选择下拉框
        ttk.Label(calc_area, text="单位:").grid(row=0, column=2, sticky="w", padx=5)
        self.unit_var = tk.StringVar(value="天")
        unit_combo = ttk.Combobox(calc_area, textvariable=self.unit_var, values=["天", "h", "min"], width=5, state="readonly")
        unit_combo.grid(row=0, column=3, padx=5)

        ttk.Label(calc_area, text="(续航时间) 或 mAh (容量)").grid(row=0, column=4, sticky="w", padx=5)

        # 计算按钮放在同一行，靠右对齐
        ttk.Button(calc_area, text="计算", command=self.calculate).grid(row=0, column=5, padx=10, sticky="e")

        # ==================== 结果展示 ====================
        result_frame = ttk.LabelFrame(main_frame, text="计算结果", padding="10")
        result_frame.pack(fill="both", expand=True, pady=10)

        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            width=120,
            height=18,  # 加大高度
            bg="white",
            relief="solid",
            padx=5,
            pady=5
        )
        self.result_text.pack(fill="both", expand=True)
        self.result_text.configure(state="disabled")

        # 初始化示例数据
        self.add_example_data()

    def update_total_values(self, *args):
        """更新总电压和总容量"""
        try:
            series = int(self.series_count_var.get())
            parallel = int(self.parallel_count_var.get())
            cell_voltage = float(self.cell_voltage_var.get())
            cell_capacity = float(self.cell_capacity_var.get())
            end_voltage = float(self.end_voltage_var.get())

            total_voltage = cell_voltage * series
            total_capacity = cell_capacity * parallel
            total_end_voltage = end_voltage * series  # 串联时终止电压也叠加

            self.total_voltage_var.set(f"{total_voltage:.2f}")
            self.total_capacity_var.set(f"{total_capacity:.2f}")
            self.total_end_voltage_var.set(f"{total_end_voltage:.2f}")

        except ValueError:
            pass  # 忽略无效输入

    def on_battery_type_change(self, event=None):
        """根据电池类型设置默认参数"""
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

            # 更新总电压和容量
            self.update_total_values()

    def setup_double_click_edit(self):
        """双击编辑功能"""
        self.mode_table.bind("<Double-1>", self.on_double_click)
        self.mode_table.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        """点击列弹出下拉菜单"""
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
        item_id = self.mode_table.insert("", "end",
                                         values=("模式" + str(len(self.mode_table.get_children()) + 1), "mA", "0", "s",
                                                 "0", "1"))
        self.mode_table.selection_set(item_id)
        self.mode_table.focus(item_id)
        self.update_sleep_duration()

    def delete_mode(self):
        selected_items = self.mode_table.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的工作模式")
            return
        for item in selected_items:
            self.mode_table.delete(item)
        self.update_sleep_duration()

    def clear_modes(self):
        self.mode_table.delete(*self.mode_table.get_children())
        self.update_sleep_duration()

    def add_example_data(self):
        self.mode_table.insert("", "end", values=("检测", "mA", "30", "s", "30.0", "48"))
        self.mode_table.insert("", "end", values=("上传", "mA", "40", "s", "20.0", "1"))
        self.mode_table.insert("", "end", values=("拍照+上传", "mA", "100", "s", "60.0", "1"))
        self.mode_table.insert("", "end", values=("休眠", "uA", "30", "s", "0", "1"))
        self.update_sleep_duration()

    def update_sleep_duration(self):
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
        try:
            # 获取电池信息
            series = int(self.series_count_var.get())
            parallel = int(self.parallel_count_var.get())
            cell_voltage = float(self.cell_voltage_var.get())
            end_voltage = float(self.end_voltage_var.get())  # ✅ 获取终止电压
            cell_capacity = float(self.cell_capacity_var.get())
            experience_factor = float(self.experience_factor_var.get())

            total_voltage = cell_voltage * series
            total_capacity = cell_capacity * parallel
            average_voltage = (total_voltage + end_voltage * series) / 2  # ✅ 平均电压（串联后）

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
                    daily_total_energy, modes, input_value, unit,
                    end_voltage  # ✅ 显式传入
                )
            elif self.calc_mode.get() == "所需容量":
                input_value = float(self.input_var.get())
                if input_value <= 0:
                    raise ValueError("输入值必须为正数")
                self._calculate_required_capacity(
                    input_value, total_voltage, experience_factor,
                    daily_total_energy, modes,
                    end_voltage  # ✅ 显式传入
                )

        except Exception as e:
            messagebox.showerror("错误", f"计算失败: {str(e)}")

    def _get_mode_data(self, voltage):
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
            except:
                continue
        return modes

    def _calculate_battery_life(self, voltage, capacity, experience_factor,
                            daily_total_energy, modes, input_ms, unit, end_voltage):
        # 转换输入值为秒
        input_seconds = convert_to_seconds(input_ms, unit)

        # ✅ 使用平均电压计算总能量
        average_voltage = (voltage + end_voltage) / 2  # ✅ 正确计算平均电压
        total_energy_mwh = capacity * average_voltage  # 实际可用电能
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

    def _calculate_required_capacity(self, input_ms, voltage, experience_factor,
                                    daily_total_energy, modes, end_voltage):
        input_seconds = input_ms / 1000
        required_energy_mwh = daily_total_energy * (input_seconds / 86400)
        # ✅ 使用平均电压反推所需容量
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

    def display_result(self, result):
        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        self.result_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = PowerConsumeCalculator(root)
    root.mainloop()
