# 蚂蚁经营助手 MVP 原型交付说明

## 1. 交付内容

本次交付为一个可运行、可部署、可分享的 Streamlit AI 产品 MVP 原型。

产品名称：蚂蚁经营助手

目标用户：中小微商家

核心价值：帮助商家通过经营数据发现异常、理解原因、确认经营方案，并查看执行复盘。

交付目录：

```text
streamlit-ai-business-assistant/
├─ app.py
├─ requirements.txt
├─ README.md
├─ assets/
└─ previews/
```

其中：

- `app.py`：MVP 原型主代码。
- `requirements.txt`：运行依赖。
- `README.md`：快速运行与部署说明。
- `assets/`：首页视觉资源。
- `previews/`：首页设计预览图。

## 2. MVP 功能说明

应用包含一条完整的产品验证闭环：

```text
选择样例/接入数据 -> 经营日报 -> 异常诊断 -> 继续追问 -> 方案确认 -> 执行复盘
```

主要能力：

- 经营数据接入：支持内置样例、CSV 上传、公开 CSV 链接。
- 经营日报：展示今日最建议处理的问题与关键指标变化。
- 异常诊断：根据订单、实收、新客、券领取、履约、评价、天气和竞争指数生成原因权重。
- 继续追问：提供 AI 工具选择入口，预留真实 AI 接入能力。
- 方案确认：商家可调整券门槛、优惠金额、预算、人群和触达文案。
- 执行复盘：模拟展示执行状态、结果指标、事实数据、模型推断和下一步建议。

当前内置 3 组样例场景：

- 午市新客下滑
- 晚市履约延迟
- 早餐券领取下降

## 3. 本地运行说明

### 3.1 环境要求

建议使用：

- Python 3.10 或以上
- pip
- 浏览器或微信内置浏览器

### 3.2 安装依赖

在终端进入项目目录：

```bash
cd streamlit-ai-business-assistant
```

安装依赖：

```bash
pip install -r requirements.txt
```

### 3.3 启动应用

本机访问：

```bash
streamlit run app.py
```

启动后打开：

```text
http://127.0.0.1:8501
```

### 3.4 手机访问

如果希望在手机或微信中打开本地版本，需要电脑和手机连接同一个 Wi-Fi，然后运行：

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

再用手机访问电脑的局域网地址，例如：

```text
http://192.168.x.x:8501
```

注意：手机顶部显示的 IP 是浏览器地址栏，不是 App 内容。正式部署后会显示 Streamlit 公网链接。

## 4. CSV 数据格式

如需接入自己的经营数据，CSV 至少包含以下字段：

```text
date, period, orders, revenue, new_customers, coupon_claims,
rating_reply_delay, delivery_delay, weather_heat, competitor_index
```

字段含义：

| 字段 | 含义 |
| --- | --- |
| `date` | 日期，例如 `2026-07-01` |
| `period` | 经营时段，例如 `早餐`、`午市`、`晚市`、`夜宵` |
| `orders` | 订单数 |
| `revenue` | 实收金额 |
| `new_customers` | 新客数 |
| `coupon_claims` | 优惠券领取数 |
| `rating_reply_delay` | 评价回复延迟 |
| `delivery_delay` | 履约/配送延迟 |
| `weather_heat` | 天气热度 |
| `competitor_index` | 周边竞争指数 |

## 5. Streamlit Cloud 部署说明

1. 将 `streamlit-ai-business-assistant` 提交到 GitHub 仓库。
2. 打开 Streamlit Community Cloud。
3. 点击新建 App。
4. Repository 选择对应 GitHub 仓库。
5. Branch 选择主分支。
6. Main file path 填写：

```text
streamlit-ai-business-assistant/app.py
```

7. 点击 Deploy。
8. 部署完成后复制公网链接，即可通过微信发送给他人体验。

## 6. 可选 AI 工具接入

当前版本默认不依赖真实 AI 密钥，确保可以直接运行和部署。

如后续需要接入真实模型，可使用以下环境变量：

| 接入方式 | 环境变量 |
| --- | --- |
| Ollama 本地大模型 | `OLLAMA_BASE_URL`、可选 `OLLAMA_MODEL` |
| OpenAI-compatible API | `AI_API_BASE_URL`、`AI_API_KEY`、`AI_MODEL` |

未配置外部 AI 时，应用不会报错，继续追问区域会保留为工具选择演示。

## 7. 验收方式

建议按以下流程验收：

1. 打开首页，确认可看到“蚂蚁经营助手”和样例体验入口。
2. 选择任一经营场景，点击“查看经营日报”。
3. 从经营日报进入异常诊断。
4. 在诊断页查看原因权重和证据链。
5. 进入方案确认页，调整预算、优惠和文案。
6. 点击确认执行。
7. 查看执行复盘结果。

基础技术检查：

```bash
python -m py_compile app.py
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

健康检查地址：

```text
http://127.0.0.1:8501/_stcore/health
```

返回 `ok` 即表示服务正常。

## 8. 说明与边界

- 本版本为首版 AI 产品 MVP 原型，不接真实支付宝/蚂蚁接口。
- 样例数据为虚构数据，仅用于演示核心流程。
- 方案结果为模拟执行复盘，不承诺真实收益提升。
- 涉及权益、触达、预算的动作均需要商家确认后才进入执行复盘。
