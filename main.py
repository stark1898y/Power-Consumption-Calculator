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
    else:  # s
        return seconds



class PowerConsumeCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("PowerConsume 功耗计算器")
        self.root.geometry("950x780")
        self.root.configure(bg="#f0f0f0")

        # 创建主框架
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill="both", expand=True)

        # 电池信息输入区域
        battery_frame = ttk.LabelFrame(main_frame, text="电池信息", padding="10")
        battery_frame.pack(fill="x", pady=10)

        # 添加电池类型选择
        ttk.Label(battery_frame, text="电池类型:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.battery_type_var = tk.StringVar(value="锂电池")
        battery_type_combo = ttk.Combobox(battery_frame, textvariable=self.battery_type_var,
                                        values=["锂电池", "一次性锂亚电池", "碱性干电池"],
                                        state="readonly", width=15)
        battery_type_combo.grid(row=2, column=1, padx=5, pady=5)
        battery_type_combo.bind("<<ComboboxSelected>>", self.on_battery_type_change)

        ttk.Label(battery_frame, text="电池电压 (V):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.voltage_var = tk.StringVar(value="3.6")
        ttk.Entry(battery_frame, textvariable=self.voltage_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        # 在 battery_frame 中添加终止电压
        ttk.Label(battery_frame, text="终止电压 (V):").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.end_voltage_var = tk.StringVar(value="3.0")
        ttk.Entry(battery_frame, textvariable=self.end_voltage_var, width=10).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(battery_frame, text="电池容量 (mAh):").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.capacity_var = tk.StringVar(value="19000")
        ttk.Entry(battery_frame, textvariable=self.capacity_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        # 在 battery_frame 中添加经验系数
        ttk.Label(battery_frame, text="经验系数:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.experience_factor_var = tk.StringVar(value="0.7")
        ttk.Entry(battery_frame, textvariable=self.experience_factor_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        # 工作模式输入区域
        mode_frame = ttk.LabelFrame(main_frame, text="工作模式设置", padding="5")
        mode_frame.pack(fill="x", pady=10)

        # 创建一个容器Frame来包含表格和水平滚动条
        table_container = ttk.Frame(mode_frame)
        table_container.pack(fill="x", pady=2)

        # 关键：禁止容器自动扩展，并设置固定高度
        table_container.pack_propagate(False)
        table_container.configure(height=120)  # 根据你的需求调整

        # 工作模式表格（现在使用容器Frame）
        self.mode_table = ttk.Treeview(table_container,
                                       columns=("mode", "current_unit", "current_value", "duration_unit",
                                                "duration_value", "times_per_day"), show="headings",
                                                height=5) # 只显示 5 行

        # 设置列宽（更紧凑）
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

        # 添加水平滚动条
        xscroll = ttk.Scrollbar(table_container, orient="horizontal", command=self.mode_table.xview)
        self.mode_table.configure(xscrollcommand=xscroll.set)

        # 放置表格和滚动条
        self.mode_table.pack(side="top", fill="x")
        xscroll.pack(side="bottom", fill="x")

        # 双击编辑功能
        self.setup_double_click_edit()

        # 添加/删除按钮
        btn_frame = ttk.Frame(mode_frame)
        btn_frame.pack(fill="x", pady=2)

        ttk.Button(btn_frame, text="添加模式", command=self.add_mode).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="删除模式", command=self.delete_mode).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="清空模式", command=self.clear_modes).pack(side="left", padx=2)

        # 计算模式选择
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

        # 计算区域
        calc_area = ttk.Frame(main_frame)
        calc_area.pack(fill="x", pady=10)

        ttk.Label(calc_area, text="输入:").grid(row=0, column=0, sticky="e", padx=5)
        self.input_var = tk.StringVar(value="5000")
        ttk.Entry(calc_area, textvariable=self.input_var, width=10).grid(row=0, column=1, padx=5)
        ttk.Label(calc_area, text="ms (续航时间) 或 mAh (容量)").grid(row=0, column=2, sticky="w", padx=5)

        ttk.Button(main_frame, text="计算", command=self.calculate).pack(pady=10)

        # 结果展示区域（现在使用更大的文本框）
        result_frame = ttk.LabelFrame(main_frame, text="计算结果", padding="10")
        result_frame.pack(fill="both", expand=True, pady=10)

        # 创建更大的文本框，带自动换行和滚动
        self.result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            width=100,  # 增加宽度（字符数）
            height=10,  # 增加高度（行数）
            bg="white",
            relief="solid",
            padx=5,
            pady=5
        )
        self.result_text.pack(fill="both", expand=True)
        self.result_text.configure(state="disabled")

        # 初始化示例数据
        self.add_example_data()

    def setup_double_click_edit(self):
        """设置双击编辑功能"""
        # 绑定双击事件
        self.mode_table.bind("<Double-1>", self.on_double_click)

        # 绑定左键点击事件用于单位列的下拉选择
        self.mode_table.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        """处理点击事件：在电流单位/时长单位列显示下拉菜单"""
        col = self.mode_table.identify_column(event.x)
        item = self.mode_table.identify_row(event.y)

        if not item or col not in ("#2", "#4"):  # 电流单位 或 时长单位 列
            return

        values = self.mode_table.item(item, "values")
        if len(values) < 6:
            return

        current_value = values[1] if col == "#2" else values[3]

        # 定义选项
        options = ["uA", "mA"] if col == "#2" else ["ms", "s", "min", "h"]

        # 创建 Combobox
        combo = ttk.Combobox(
            self.mode_table,
            values=options,
            width=5,
            state="readonly",
            font=("Segoe UI", 9),
            background="#ffffff"
        )
        combo.set(current_value)

        # 获取单元格位置
        x, y, w, h = self.mode_table.bbox(item, col)
        combo.place(x=x + 5, y=y + 5, width=w - 10, height=h - 5)

        # 绑定选择事件
        def on_select(event):
            selected = combo.get()
            if selected:
                new_values = list(values)

                if col == "#2":  # 电流单位
                    new_values[1] = selected
                else:  # 时长单位
                    # 获取原始时长值（秒）
                    original_duration = float(new_values[4])
                    old_unit = current_value

                    # 转换为秒
                    seconds = convert_to_seconds(original_duration, old_unit)

                    # 转换为新单位
                    new_duration = convert_from_seconds(seconds, selected)
                    new_values[3] = selected
                    new_values[4] = new_duration

                self.mode_table.item(item, values=new_values)
                self.update_sleep_duration()  # 更新休眠时长
                combo.destroy()

                # ✅ 关键：更新休眠时长
                self.update_sleep_duration()

        combo.bind("<<ComboboxSelected>>", on_select)
        combo.focus()

    def on_double_click(self, event):
        """处理双击事件：原地编辑数值"""
        col = self.mode_table.identify_column(event.x)
        item = self.mode_table.identify_row(event.y)

        if not item:
            return

        values = self.mode_table.item(item, "values")
        if len(values) < 6:
            return

        # 检查是否是“休眠”模式且是第一列（模式名）
        if col == "#1" and values[0] == "休眠":
            return  # 不允许修改休眠模式名称

        # 确定要编辑的列索引
        column_index = None
        if col == "#3":  # 电流值
            column_index = 2
        elif col == "#5":  # 时长值
            column_index = 4
        elif col == "#6":  # 每天次数
            column_index = 5

        if column_index is None:
            return

        # 获取当前值
        current_value = str(values[column_index])

        # 创建 Entry 编辑框
        entry = tk.Entry(
            self.mode_table,
            width=10,
            font=("Segoe UI", 9),
            justify="center"
        )
        entry.insert(0, current_value)

        # 获取单元格位置
        x, y, w, h = self.mode_table.bbox(item, col)

        # 精确贴合单元格
        entry.place(x=x + 5, y=y + 5, width=w - 10, height=h - 5)

        # 绑定事件
        def save_value(event=None):
            try:
                value = float(entry.get())
                if column_index == 5:  # 每天次数
                    value = int(value)
                new_values = list(values)
                new_values[column_index] = value
                self.mode_table.item(item, values=new_values)
                entry.destroy()

                # ✅ 关键：更新休眠时长
                self.update_sleep_duration()

            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
                entry.destroy()
        def cancel():
            entry.destroy()

        entry.bind("<Return>", save_value)
        entry.bind("<FocusOut>", save_value)
        entry.bind("<Escape>", cancel)
        entry.focus()

    def get_input(self, prompt, default_value):
        """获取用户输入"""
        try:
            value = simpledialog.askstring("输入", prompt, initialvalue=default_value)
            if value is None:  # 用户取消
                return None
            return float(value)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return None

    def add_mode(self):
        """添加新的工作模式"""
        item_id = self.mode_table.insert("", "end",
                                         values=("模式" + str(len(self.mode_table.get_children()) + 1), "mA", "0", "s",
                                                 "0", "1"))
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
        """添加示例数据"""
        # 添加一些示例模式
        self.mode_table.insert("", "end", values=("检测", "mA", "30", "s", "30.0", "48"))
        self.mode_table.insert("", "end", values=("上传", "mA", "40", "s", "20.0", "1"))
        self.mode_table.insert("", "end", values=("拍照+上传", "mA", "100", "s", "60.0", "1"))

        # 添加休眠模式（最后）
        self.mode_table.insert("", "end", values=("休眠", "uA", "30", "s", "0", "1"))

        # 更新休眠时长
        self.update_sleep_duration()

    def update_sleep_duration(self):
        """更新休眠时长（基于其他模式的总时长）"""
        total_active_time = 0
        sleep_item = None
        total_time_per_day = 24 * 3600  # 86400 秒

        for item in self.mode_table.get_children():
            values = self.mode_table.item(item, "values")
            if len(values) < 6:
                continue

            if values[0] == "休眠":
                sleep_item = item
                continue

            # 转换为秒
            try:
                duration_value = float(values[4])
                duration_unit = values[3]
                times_per_day = int(values[5])

                seconds = convert_to_seconds(duration_value, duration_unit)
                total_active_time += seconds * times_per_day
            except (ValueError, TypeError):
                continue  # 跳过无效数据

        # 防止负数：如果活动时间超过一天，休眠时间为 0
        if sleep_item:
            if total_active_time >= total_time_per_day:
                sleep_duration_seconds = 0
                messagebox.showwarning(
                    "警告",
                    f"活动总时长 ({total_active_time:.1f} 秒) 已超过 24 小时！\n"
                    "休眠时间将被设为 0。"
                )
            else:
                sleep_duration_seconds = total_time_per_day - total_active_time

            # 获取当前休眠单位
            sleep_values = self.mode_table.item(sleep_item, "values")
            sleep_unit = sleep_values[3]

            # 转换为对应单位
            sleep_duration = convert_from_seconds(sleep_duration_seconds, sleep_unit)

            # 更新表格
            new_values = list(sleep_values)
            new_values[4] = sleep_duration
            self.mode_table.item(sleep_item, values=new_values)

    def on_battery_type_change(self, event=None):
        """根据电池类型自动设置终止电压和经验系数"""
        battery_type = self.battery_type_var.get()

        settings = {
            "锂电池": {"voltage": "3.6", "end_voltage": "3.0", "factor": "0.85"},
            "一次性锂亚电池": {"voltage": "3.6", "end_voltage": "2.0", "factor": "0.9"},
            "碱性干电池": {"voltage": "1.5", "end_voltage": "1.0", "factor": "0.7"}
        }

        if battery_type in settings:
            setting = settings[battery_type]
            self.voltage_var.set(setting["voltage"])
            self.end_voltage_var.set(setting["end_voltage"])
            self.experience_factor_var.set(setting["factor"])

    def calculate(self):
        """执行计算"""
        try:
            # 获取电池信息
            voltage = float(self.voltage_var.get())
            end_voltage = float(self.end_voltage_var.get())
            capacity = float(self.capacity_var.get())

            raw_capacity = float(self.capacity_var.get())

            # 容量单位转换（如果支持uAh）
            if hasattr(self, 'capacity_unit_var'):
                capacity_unit = self.capacity_unit_var.get()
                if capacity_unit == "uAh":
                    capacity = raw_capacity / 1000
                else:
                    capacity = raw_capacity
            else:
                capacity = raw_capacity

            # 计算平均工作电压
            average_voltage = (voltage + end_voltage) / 2

            # 总能量（mWh）
            total_energy_mwh = capacity * average_voltage

            # 应用经验系数
            usable_energy_mwh = total_energy_mwh * float(self.experience_factor_var.get())

            # 获取工作模式数据
            modes = []
            for item in self.mode_table.get_children():
                values = self.mode_table.item(item, "values")
                if len(values) < 6:
                    continue

                mode_name = values[0]
                current_unit = values[1]
                current_value = float(values[2])
                duration_unit = values[3]
                duration_value = float(values[4])
                times_per_day = int(values[5])

                # 转换为 mA
                if current_unit == "uA":
                    current_ma = current_value / 1000
                else:
                    current_ma = current_value

                # 转换为秒
                seconds = convert_to_seconds(duration_value, duration_unit)

                # 计算单次功耗（mWh）
                energy_per_cycle_mwh = (current_ma * seconds * voltage) / 3600

                # 每天总功耗（mWh）
                daily_energy_mwh = energy_per_cycle_mwh * times_per_day

                modes.append((mode_name, current_ma, seconds, energy_per_cycle_mwh, daily_energy_mwh))

            if not modes:
                messagebox.showwarning("警告", "请至少添加一个工作模式")
                return

            # 获取输入值
            input_value = float(self.input_var.get())

            # 计算每日总功耗（mWh）
            daily_total_energy = sum(daily_energy_mwh for _, _, _, _, daily_energy_mwh in modes)

            # 根据计算模式进行计算
            if self.calc_mode.get() == "续航时间":
                # 计算续航时间
                if capacity <= 0:
                    messagebox.showerror("错误", "电池容量不能为0或负数")
                    return

                # 总能量（mWh）
                total_energy_mwh = capacity * voltage

                # 应用经验系数：实际可用能量减少
                usable_energy_mwh = total_energy_mwh * float(self.experience_factor_var.get())

                # 可使用天数
                days = total_energy_mwh / daily_total_energy

                # 转换为小时、年
                hours = days * 24
                years = days / 365.25

                # 格式化结果
                result = f"电池容量: {capacity:.2f} mAh\n"
                result += f"电池电压: {voltage:.2f} V\n"
                result += f"总能量: {total_energy_mwh:.2f} mWh\n"
                result += f"每日功耗: {daily_total_energy:.4f} mWh\n"
                result += f"设备可使用时间: {hours:.2f} 小时 ({days:.2f} 天, {years:.2f} 年)\n\n"
                result += "工作模式详情:\n"

                for mode_name, current_ma, seconds, energy_per_cycle_mwh, daily_energy_mwh in modes:
                    result += f"  - {mode_name}: {current_ma:.2f} mA, {seconds:.2f} s, "
                    result += f"{energy_per_cycle_mwh:.4f} mWh/次, 每天{times_per_day}次, "
                    result += f"共{daily_energy_mwh:.4f} mWh\n"

                self.display_result(result)

            elif self.calc_mode.get() == "所需容量":
                # 计算所需电池容量
                if input_value <= 0:
                    messagebox.showerror("错误", "输入值不能为0或负数")
                    return

                # 输入的是 ms，转换为秒
                input_seconds = input_value / 1000

                # 计算所需总能量（mWh）
                required_energy_mwh = daily_total_energy * (input_seconds / 86400)  # 按比例缩放

                # 考虑经验系数：需要更大的电池来补偿损耗
                required_capacity = required_energy_mwh / (voltage * float(self.experience_factor_var.get()))

                # 所需容量（mAh）
                required_capacity = required_energy_mwh / voltage

                # 格式化结果
                result = f"输入续航时间: {input_value:.2f} ms\n"
                result += f"每日功耗: {daily_total_energy:.4f} mWh\n"
                result += f"所需电池容量: {required_capacity:.2f} mAh\n\n"
                result += "工作模式详情:\n"

                for mode_name, current_ma, seconds, energy_per_cycle_mwh, daily_energy_mwh in modes:
                    result += f"  - {mode_name}: {current_ma:.2f} mA, {seconds:.2f} s, "
                    result += f"{energy_per_cycle_mwh:.4f} mWh/次, 每天{times_per_day}次, "
                    result += f"共{daily_energy_mwh:.4f} mWh\n"

                self.display_result(result)

        except ValueError as e:
            messagebox.showerror("输入错误", f"请输入有效的数字: {str(e)}")

    def display_result(self, result):
        """显示计算结果"""
        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        self.result_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = PowerConsumeCalculator(root)
    root.mainloop()
