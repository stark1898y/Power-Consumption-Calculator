# app.py
from flask import Flask, request, jsonify
import math

app = Flask(__name__)

# 保留核心计算函数
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

# 移植核心计算逻辑
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
                <select id="battery_type">
                    <option value="锂电池">锂电池</option>
                    <option value="一次性锂亚电池">一次性锂亚电池</option>
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
            </div>

            <div id="result"></div>
        </div>

        <script>
            function addModeRow() {
                const table = document.getElementById("modes_table").getElementsByTagName('tbody')[0];
                const newRow = table.insertRow();

                newRow.innerHTML = `
                    <td><input type="text" value="模式" class="mode_name"></td>
                    <td>
                        <select class="current_unit">
                            <option value="uA">uA</option>
                            <option value="mA" selected>mA</option>
                        </select>
                    </td>
                    <td><input type="number" value="0" class="current_value"></td>
                    <td>
                        <select class="duration_unit">
                            <option value="ms">ms</option>
                            <option value="s" selected>s</option>
                            <option value="min">min</option>
                            <option value="h">h</option>
                            <option value="天">天</option>
                        </select>
                    </td>
                    <td><input type="number" value="0" class="duration_value"></td>
                    <td><input type="number" value="1" class="times_per_day"></td>
                    <td><button onclick="deleteRow(this)">删除</button></td>
                `;
            }

            function deleteRow(button) {
                const row = button.parentNode.parentNode;
                row.parentNode.removeChild(row);
            }

            function collectData() {
                const modes = [];
                const rows = document.getElementById("modes_table").getElementsByTagName('tbody')[0].rows;

                for (let i = 0; i < rows.length; i++) {
                    const cells = rows[i].cells;
                    modes.push({
                        mode: cells[0].getElementsByTagName('input')[0].value,
                        current_unit: cells[1].getElementsByTagName('select')[0].value,
                        current_value: cells[2].getElementsByTagName('input')[0].value,
                        duration_unit: cells[3].getElementsByTagName('select')[0].value,
                        duration_value: cells[4].getElementsByTagName('input')[0].value,
                        times_per_day: cells[5].getElementsByTagName('input')[0].value
                    });
                }

                return {
                    battery_type: document.getElementById("battery_type").value,
                    experience_factor: document.getElementById("experience_factor").value,
                    series_count: document.getElementById("series_count").value,
                    parallel_count: document.getElementById("parallel_count").value,
                    cell_voltage: document.getElementById("cell_voltage").value,
                    end_voltage: document.getElementById("end_voltage").value,
                    cell_capacity: document.getElementById("cell_capacity").value,
                    modes: modes,
                    calc_mode: document.querySelector('input[name="calc_mode"]:checked').value,
                    input_value: document.getElementById("input_value").value,
                    input_unit: document.getElementById("input_unit").value
                };
            }

            function calculate() {
                const data = collectData();

                fetch('/calculate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                })
                .then(response => response.json())
                .then(result => {
                    displayResult(result);
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById("result").innerHTML = "<p style='color: red;'>计算出错: " + error + "</p>";
                });
            }

            function displayResult(result) {
                let html = "<h3>计算结果</h3>";

                if (result.type === "battery_life") {
                    html += `
                        <p>总电压: ${result.voltage.toFixed(2)} V</p>
                        <p>总容量: ${result.capacity.toFixed(2)} mAh</p>
                        <p>平均电压: ${result.average_voltage.toFixed(2)} V</p>
                        <p>总能量: ${result.total_energy_mwh.toFixed(2)} mWh</p>
                        <p>可用能量: ${result.usable_energy_mwh.toFixed(2)} mWh (×${result.experience_factor})</p>
                        <p>每日功耗: ${result.daily_total_energy.toFixed(4)} mWh</p>
                        <p>可使用时间: ${result.hours.toFixed(2)} 小时 (${result.days.toFixed(2)} 天, ${result.years.toFixed(2)} 年)</p>
                        <h4>工作模式详情:</h4>
                        <ul>
                    `;

                    result.modes.forEach(mode => {
                        html += `<li>${mode.name}: ${mode.current_ma.toFixed(2)} mA, ${mode.seconds.toFixed(2)} s, ${mode.daily_energy_mwh.toFixed(4)} mWh/天</li>`;
                    });

                    html += "</ul>";
                } else {
                    html += `
                        <p>目标续航: ${result.input_value} ${result.input_unit} (${result.input_seconds.toFixed(2)} 秒)</p>
                        <p>每日功耗: ${result.daily_total_energy.toFixed(4)} mWh</p>
                        <p>所需容量: ${result.required_capacity.toFixed(2)} mAh</p>
                        <p>(考虑了 ${result.experience_factor} 的经验系数和平均电压)</p>
                        <h4>工作模式详情:</h4>
                        <ul>
                    `;

                    result.modes.forEach(mode => {
                        html += `<li>${mode.name}: ${mode.current_ma.toFixed(2)} mA, ${mode.seconds.toFixed(2)} s, ${mode.daily_energy_mwh.toFixed(4)} mWh/天</li>`;
                    });

                    html += "</ul>";
                }

                document.getElementById("result").innerHTML = html;
            }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
