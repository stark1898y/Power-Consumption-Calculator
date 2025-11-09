# app.py
from flask import Flask, request, jsonify
import math
import base64
import io
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

app = Flask(__name__, static_folder='static')

# 检查系统并设置合适的字体
def setup_chinese_font():
    """设置中文字体支持"""
    # 尝试加载常见中文字体
    font_names = [
        'WenQuanYi Zen Hei',
        'WenQuanYi Micro Hei',
        'Noto Sans CJK SC',
        'SimHei',
        'Microsoft YaHei'
    ]

    # 检查系统中是否存在这些字体
    available_fonts = []
    for name in font_names:
        try:
            # 查找字体文件
            font_prop = fm.FontProperties(family=name)
            available_fonts.append(name)
        except:
            continue

    if available_fonts:
        plt.rcParams['font.sans-serif'] = available_fonts
    else:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS']

    plt.rcParams['axes.unicode_minus'] = False

# 在应用启动时设置字体
setup_chinese_font()

@app.route('/chart', methods=['POST'])
def generate_chart():
    data = request.json
    modes = data.get('modes', [])

    # 使用 'name' 键而不是 'mode' 键
    names = [mode['name'] for mode in modes]
    energies = [mode['daily_energy_mwh'] for mode in modes]

    # 创建图表
    fig, ax = plt.subplots(figsize=(10, 6))

    # 设置颜色
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    bars = ax.bar(names, energies, color=colors[:len(names)])

    # 添加数值标签
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

    # 设置坐标轴标签和标题
    ax.set_xlabel('工作模式', fontsize=12)
    ax.set_ylabel('每日能耗 (mWh)', fontsize=12)
    ax.set_title('功耗分布图', fontsize=14)
    ax.grid(axis='y', alpha=0.3)

    # 调整布局避免裁剪
    plt.tight_layout()

    # 保存为内存中的字节流
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    plt.close(fig)

    return jsonify({'image': img_base64})

# 修改后的计算函数
@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json

    # 从请求中获取参数
    series = int(data.get('series_count', 1))
    parallel = int(data.get('parallel_count', 1))
    cell_voltage = float(data.get('cell_voltage', 3.6))
    end_voltage = float(data.get('end_voltage', 3.0))
    cell_capacity = float(data.get('cell_capacity', 19000))
    experience_factor = float(data.get('experience_factor', 0.7))

    total_voltage = cell_voltage * series
    total_capacity = cell_capacity * parallel
    average_voltage = (total_voltage + end_voltage * series) / 2

    # 处理工作模式
    modes = data.get('modes', [])
    daily_total_energy = 0

    mode_details = []
    for mode in modes:
        current_unit = mode['current_unit']
        current_value = float(mode['current_value'])
        duration_unit = mode['duration_unit']
        duration_value = float(mode['duration_value'])
        times_per_day = int(mode['times_per_day'])

        current_ma = current_value / 1000 if current_unit == "uA" else current_value
        seconds = convert_to_seconds(duration_value, duration_unit)

        energy_per_cycle_mwh = (current_ma * seconds * average_voltage) / 3600
        daily_energy_mwh = energy_per_cycle_mwh * times_per_day
        daily_total_energy += daily_energy_mwh

        mode_details.append({
            'name': mode['mode'],
            'current_ma': current_ma,
            'seconds': seconds,
            'times_per_day': times_per_day,
            'energy_per_cycle_mwh': energy_per_cycle_mwh,
            'daily_energy_mwh': daily_energy_mwh
        })

    # 执行计算
    calc_mode = data.get('calc_mode', '续航时间')
    input_value = float(data.get('input_value', 5000))
    unit = data.get('input_unit', '天')

    if calc_mode == "续航时间":
        input_seconds = convert_to_seconds(input_value, unit)
        total_energy_mwh = total_capacity * average_voltage
        usable_energy_mwh = total_energy_mwh * experience_factor
        days = usable_energy_mwh / daily_total_energy
        hours = days * 24
        years = days / 365.25

        result = {
            "type": "battery_life",
            "voltage": total_voltage,
            "capacity": total_capacity,
            "average_voltage": average_voltage,
            "total_energy_mwh": total_energy_mwh,
            "usable_energy_mwh": usable_energy_mwh,
            "experience_factor": experience_factor,
            "daily_total_energy": daily_total_energy,
            "days": days,
            "hours": hours,
            "years": years,
            "modes": mode_details
        }
    else:  # 所需容量
        input_seconds = convert_to_seconds(input_value, "s")
        required_energy_mwh = daily_total_energy * (input_seconds / 86400)
        average_voltage = (total_voltage + end_voltage) / 2
        required_capacity = required_energy_mwh / (average_voltage * experience_factor)

        result = {
            "type": "required_capacity",
            "input_value": input_value,
            "input_unit": unit,
            "input_seconds": input_seconds,
            "voltage": total_voltage,
            "average_voltage": average_voltage,
            "experience_factor": experience_factor,
            "daily_total_energy": daily_total_energy,
            "required_energy_mwh": required_energy_mwh,
            "required_capacity": required_capacity,
            "modes": mode_details
        }

    return jsonify(result)

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

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>PowerConsume 功耗计算器</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .form-group { margin-bottom: 15px; }
            label { display: inline-block; width: 150px; }
            input, select { padding: 5px; margin: 5px; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
            th { background-color: #f2f2f2; }
            button { padding: 10px 20px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
            button:hover { background-color: #45a049; }
            #result { margin-top: 20px; padding: 15px; background-color: #f9f9f9; border-left: 5px solid #4CAF50; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PowerConsume 功耗计算器</h1>

            <h2>电池信息</h2>
            <div class="form-group">
                <label>电池类型:</label>
                <select id="battery_type" onchange="updateBatteryDefaults(this.value)">
                    <option value="锂电池">锂电池</option>
                    <option value="一次性锂亚电池" selected>一次性锂亚电池</option>
                    <option value="碱性干电池">碱性干电池</option>
                </select>

                <label>经验系数:</label>
                <input type="number" id="experience_factor" value="0.7" step="0.1" min="0" max="1">
            </div>

            <div class="form-group">
                <label>串联个数:</label>
                <input type="number" id="series_count" value="1" min="1">

                <label>并联个数:</label>
                <input type="number" id="parallel_count" value="1" min="1">
            </div>

            <div class="form-group">
                <label>单节电压 (V):</label>
                <input type="number" id="cell_voltage" value="3.6" step="0.1">

                <label>终止电压 (V):</label>
                <input type="number" id="end_voltage" value="3.0" step="0.1">

                <label>单节容量 (mAh):</label>
                <input type="number" id="cell_capacity" value="19000">
            </div>

            <div class="form-group">
                <label>总电压 (V):</label>
                <input type="number" id="total_voltage" value="3.6" readonly>

                <label>总终止电压 (V):</label>
                <input type="number" id="total_end_voltage" value="3.0" readonly>

                <label>总容量 (mAh):</label>
                <input type="number" id="total_capacity" value="19000" readonly>
            </div>

            <h2>工作模式设置</h2>
            <table id="modes_table">
                <thead>
                    <tr>
                        <th>模式</th>
                        <th>电流单位</th>
                        <th>平均电流</th>
                        <th>时长单位</th>
                        <th>时长值</th>
                        <th>每天次数</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><input type="text" value="检测" class="mode_name"></td>
                        <td>
                            <select class="current_unit">
                                <option value="uA">uA</option>
                                <option value="mA" selected>mA</option>
                            </select>
                        </td>
                        <td><input type="number" value="30" class="current_value"></td>
                        <td>
                            <select class="duration_unit">
                                <option value="ms">ms</option>
                                <option value="s" selected>s</option>
                                <option value="min">min</option>
                                <option value="h">h</option>
                                <option value="天">天</option>
                            </select>
                        </td>
                        <td><input type="number" value="30" class="duration_value"></td>
                        <td><input type="number" value="48" class="times_per_day"></td>
                        <td><button onclick="deleteRow(this)">删除</button></td>
                    </tr>
                    <tr>
                        <td><input type="text" value="上传" class="mode_name"></td>
                        <td>
                            <select class="current_unit">
                                <option value="uA">uA</option>
                                <option value="mA" selected>mA</option>
                            </select>
                        </td>
                        <td><input type="number" value="40" class="current_value"></td>
                        <td>
                            <select class="duration_unit">
                                <option value="ms">ms</option>
                                <option value="s" selected>s</option>
                                <option value="min">min</option>
                                <option value="h">h</option>
                                <option value="天">天</option>
                            </select>
                        </td>
                        <td><input type="number" value="20" class="duration_value"></td>
                        <td><input type="number" value="1" class="times_per_day"></td>
                        <td><button onclick="deleteRow(this)">删除</button></td>
                    </tr>
                    <tr>
                        <td><input type="text" value="拍照+上传" class="mode_name"></td>
                        <td>
                            <select class="current_unit">
                                <option value="uA">uA</option>
                                <option value="mA" selected>mA</option>
                            </select>
                        </td>
                        <td><input type="number" value="100" class="current_value"></td>
                        <td>
                            <select class="duration_unit">
                                <option value="ms">ms</option>
                                <option value="s" selected>s</option>
                                <option value="min">min</option>
                                <option value="h">h</option>
                                <option value="天">天</option>
                            </select>
                        </td>
                        <td><input type="number" value="60" class="duration_value"></td>
                        <td><input type="number" value="1" class="times_per_day"></td>
                        <td><button onclick="deleteRow(this)">删除</button></td>
                    </tr>
                    <tr>
                        <td><input type="text" value="休眠" class="mode_name"></td>
                        <td>
                            <select class="current_unit">
                                <option value="uA" selected>uA</option>
                                <option value="mA">mA</option>
                            </select>
                        </td>
                        <td><input type="number" value="30" class="current_value"></td>
                        <td>
                            <select class="duration_unit">
                                <option value="ms">ms</option>
                                <option value="s" selected>s</option>
                                <option value="min">min</option>
                                <option value="h">h</option>
                                <option value="天">天</option>
                            </select>
                        </td>
                        <td><input type="number" value="84880" class="duration_value"></td>
                        <td><input type="number" value="1" class="times_per_day"></td>
                        <td><button onclick="deleteRow(this)">删除</button></td>
                    </tr>
                </tbody>
            </table>
            <button onclick="addModeRow()">添加模式</button>

            <h2>计算模式</h2>
            <div class="form-group">
                <label>
                    <input type="radio" name="calc_mode" value="续航时间" checked>
                    计算续航时间
                </label>
                <label>
                    <input type="radio" name="calc_mode" value="所需容量">
                    计算所需容量
                </label>
            </div>

            <div class="form-group">
                <label>输入值:</label>
                <input type="number" id="input_value" value="5000">

                <label>单位:</label>
                <select id="input_unit">
                    <option value="天">天</option>
                    <option value="h">h</option>
                    <option value="min">min</option>
                </select>

                <button onclick="calculate()">计算</button>
                <button onclick="showChart()">显示图表</button>
                <div id="chart-container" style="margin-top: 20px;"></div>
            </div>
            <div id="result"></div>
        </div>

        <!-- 引入外部 JS -->
        <script src="/static/script.js"></script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
