/*
 * @Author       : stark1898y 1658608470@qq.com
 * @Date         : 2025-11-09 23:02:54
 * @LastEditors: stark1898y 1658608470@qq.com
 * @LastEditTime: 2026-06-22 13:35:05
 * @FilePath     : \Power Consumption Calculator\static\script.js
 * @Description  :
 *
 * Copyright (c) 2025 by yzy, All Rights Reserved.
 */
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

// 更新总容量
function updateTotalCapacity() {
    const parallel = parseFloat(document.getElementById("parallel_count").value) || 1;
    const capacity = parseFloat(document.getElementById("cell_capacity").value) || 0;
    const total = parallel * capacity;
    document.getElementById("total_capacity").value = total.toFixed(0);
}

// 更新总电压
function updateTotalVoltage() {
    const series = parseFloat(document.getElementById("series_count").value) || 1;
    const voltage = parseFloat(document.getElementById("cell_voltage").value) || 0;
    const total = series * voltage;
    document.getElementById("total_voltage").value = total.toFixed(2);
}

// 更新总终止电压
function updateTotalEndVoltage() {
    const series = parseFloat(document.getElementById("series_count").value) || 1;
    const endVoltage = parseFloat(document.getElementById("end_voltage").value) || 0;
    const total = series * endVoltage;
    document.getElementById("total_end_voltage").value = total.toFixed(2);
}

// 绑定事件
document.getElementById("parallel_count").addEventListener("input", updateTotalCapacity);
document.getElementById("cell_capacity").addEventListener("input", updateTotalCapacity);
document.getElementById("series_count").addEventListener("input", updateTotalVoltage);
document.getElementById("series_count").addEventListener("input", updateTotalEndVoltage);
document.getElementById("cell_voltage").addEventListener("input", updateTotalVoltage);
document.getElementById("end_voltage").addEventListener("input", updateTotalEndVoltage);

// 页面加载时初始化
updateTotalCapacity();
updateTotalVoltage();
updateTotalEndVoltage();

// 在 JavaScript 中添加电池类型切换逻辑
function updateBatteryDefaults(type) {
    const defaults = {
        "锂电池": { voltage: 4.2, endVoltage: 3.6, capacity: 3500, series: 1, parallel: 1 },
        "一次性锂亚电池": { voltage: 3.6, endVoltage: 2.0, capacity: 19000, series: 1, parallel: 2 },
        "碱性干电池": { voltage: 1.5, endVoltage: 1.0, capacity: 2700, series: 2, parallel: 1 }
    };

    const def = defaults[type];
    document.getElementById("cell_voltage").value = def.voltage;
    document.getElementById("end_voltage").value = def.endVoltage;
    document.getElementById("cell_capacity").value = def.capacity;
    document.getElementById("series_count").value = def.series;
    document.getElementById("parallel_count").value = def.parallel;

    // 自动更新总容量、总电压、总终止电压
    updateTotalCapacity();
    updateTotalVoltage();
    updateTotalEndVoltage();
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
        // 计算完成后自动显示图表
        showChart(); // ← 添加这行
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById("result").innerHTML = "<p style='color: red;'>计算出错: " + error + "</p>";
    });
}

// 自动计算休眠时长
function calculateSleepDuration() {
    const rows = document.getElementById("modes_table").getElementsByTagName('tbody')[0].rows;
    let totalActiveTimeSeconds = 0;

    // 遍历所有行，计算非休眠模式的总活跃时间
    for (let i = 0; i < rows.length; i++) {
        const cells = rows[i].cells;
        const modeName = cells[0].getElementsByTagName('input')[0].value;
        if (modeName === "休眠") continue;

        const currentUnit = cells[1].getElementsByTagName('select')[0].value;
        const currentValue = parseFloat(cells[2].getElementsByTagName('input')[0].value);
        const durationUnit = cells[3].getElementsByTagName('select')[0].value;
        const durationValue = parseFloat(cells[4].getElementsByTagName('input')[0].value);
        const timesPerDay = parseInt(cells[5].getElementsByTagName('input')[0].value);

        // 转换为秒
        let seconds = durationValue;
        if (durationUnit === "ms") seconds /= 1000;
        else if (durationUnit === "min") seconds *= 60;
        else if (durationUnit === "h") seconds *= 3600;
        else if (durationUnit === "天") seconds *= 24 * 3600;

        totalActiveTimeSeconds += seconds * timesPerDay;
    }

    // 找到休眠行
    let sleepRow = null;
    for (let i = 0; i < rows.length; i++) {
        const modeName = rows[i].cells[0].getElementsByTagName('input')[0].value;
        if (modeName === "休眠") {
            sleepRow = rows[i];
            break;
        }
    }

    if (!sleepRow) return;

    // 计算休眠时间（秒）
    const sleepDurationSeconds = Math.max(0, 24 * 3600 - totalActiveTimeSeconds);

    // 获取休眠的时长单位
    const sleepDurationUnit = sleepRow.cells[3].getElementsByTagName('select')[0].value;

    // 转换为对应单位
    let sleepDurationValue = sleepDurationSeconds;
    if (sleepDurationUnit === "ms") sleepDurationValue *= 1000;
    else if (sleepDurationUnit === "min") sleepDurationValue /= 60;
    else if (sleepDurationUnit === "h") sleepDurationValue /= 3600;
    else if (sleepDurationUnit === "天") sleepDurationValue /= (24 * 3600);

    // 更新输入框
    sleepRow.cells[4].getElementsByTagName('input')[0].value = sleepDurationValue.toFixed(2);
}

// 绑定事件：当任何模式修改后，重新计算休眠时间
document.addEventListener('input', function(e) {
    if (e.target.classList.contains('current_value') ||
        e.target.classList.contains('duration_value') ||
        e.target.classList.contains('times_per_day')) {
        calculateSleepDuration();
    }
});

// 页面加载完成后初始化一次
window.onload = function() {
    calculateSleepDuration();
};

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

function showChart() {
    const container = document.getElementById("chart-container");
    const button = document.querySelector('button[onclick="showChart()"]');

    // 如果已有图表，则隐藏并修改按钮文字
    if (container.innerHTML.includes('data:image')) {
        container.innerHTML = '';
        button.textContent = '显示图表';
        return;
    }

    // 否则调用接口生成图表
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
        return fetch('/chart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ modes: result.modes })
        });
    })
    .then(response => response.json())
    .then(result => {
        const imgData = result.image;
        container.innerHTML = `<img src="data:image/png;base64,${imgData}" style="max-width:100%; height:auto;" />`;
        button.textContent = '隐藏图表';
    })
    .catch(error => {
        console.error('Error:', error);
        alert("图表生成失败");
    });
}
