# PowerConsume 功耗计算器

一款用于计算嵌入式设备电池续航时间或所需电池容量的工具，支持多种电池类型和工作模式配置。

## 功能特性

- **多种计算模式**：计算续航时间 / 计算所需电池容量
- **多种电池类型**：锂电池、一次性锂亚电池、碱性干电池（可自定义参数）
- **多工作模式**：支持添加、删除、编辑多种工作模式（如检测、上传、拍照、休眠等）
- **自动计算休眠时长**：根据其他模式的活跃时间自动计算休眠时长
- **图表可视化**：柱状图 + 环形图展示能耗分布
- **多种时间单位**：支持 ms、s、min、h、天
- **电流单位切换**：支持 uA 和 mA
- **串并联配置**：支持多节电池串联和并联
- **经验系数**：考虑电池放电效率的经验系数
- **导出功能**：支持导出 PDF、保存/加载配置（桌面版）

## 在线演示

**GitHub Pages**：[点击访问在线计算器](https://stark1898y.github.io/Power-Consumption-Calculator/)

## 项目结构

```
power-consumption-calculator/
├── main.py                    # 桌面版主程序（Python + Tkinter GUI）
├── docs/
│   └── index.html             # 纯前端版（HTML + JS + Chart.js，可直接打开或部署 GitHub Pages）
├── requirements.txt           # Python 依赖（桌面版）
├── PowerConsumeCalculator.spec # PyInstaller 打包配置
├── dist/
│   └── PowerConsumeCalculator.exe  # 打包好的 Windows 可执行文件
├── LICENSE                    # MIT 许可证
└── README.md                  # 项目说明
```

## 版本说明

| 版本               | 文件                | 技术栈                       | 运行方式                                            |
| ------------------ | ------------------- | ---------------------------- | --------------------------------------------------- |
| **桌面版**   | `main.py`         | Python + Tkinter             | 运行 `python main.py` 或使用打包好的 exe           |
| **纯前端版** | `docs/index.html` | HTML + JavaScript + Chart.js | 直接双击打开 HTML 文件或部署到 GitHub Pages          |

## 快速开始

### 1. 桌面版

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 2. 纯前端版（推荐）

直接双击打开 `docs/index.html` 文件，无需安装任何依赖。

也可部署到 GitHub Pages：

1. Fork 本仓库
2. 在仓库 Settings → Pages → Source 选择 `main` 分支的 `/docs` 文件夹
3. 访问 `https://你的用户名.github.io/Power-Consumption-Calculator/`

### 3. EXE 可执行文件（免安装）

直接运行 `dist/PowerConsumeCalculator.exe`，无需 Python 环境。

## 计算公式

### 续航时间计算

```
总电压 = 单节电压 × 串联数
总容量 = 单节容量 × 并联数
平均电压 = (总电压 + 终止电压 × 串联数) / 2
总能量 = 总容量 × 平均电压
可用能量 = 总能量 × 经验系数
每日功耗 = Σ(电流 × 时长 × 平均电压 / 3600 × 每日次数)
续航时间 = 可用能量 / 每日功耗
```

### 所需容量计算

```
所需能量 = 每日功耗 × 目标天数 × 86400 / 86400
所需容量 = 所需能量 / (平均电压 × 经验系数)
```

## 开源地址

- **GitHub**：[https://github.com/stark1898y/Power-Consumption-Calculator](https://github.com/stark1898y/Power-Consumption-Calculator)
- **Gitee（国内）**：[https://gitee.com/stark1898/power-consumption-calculator](https://gitee.com/stark1898/power-consumption-calculator)

## 参考

- [PowerConsume功耗计算器](https://blog.csdn.net/yufm/article/details/134437810)

## 许可证

本项目采用 [MIT 许可证](LICENSE)。
