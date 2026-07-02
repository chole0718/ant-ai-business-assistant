# 蚂蚁经营助手

一个基于 Streamlit 的可运行 AI 产品 MVP 原型，面向中小微商家，帮助商家从经营数据中发现异常、理解原因、确认经营方案并查看执行复盘。

核心链路：

`选择样例/接入数据 -> 经营日报 -> 异常诊断 -> 继续追问 -> 方案确认 -> 执行复盘`

## 项目结构

```text
streamlit-ai-business-assistant/
├─ app.py                         # Streamlit 主应用
├─ requirements.txt               # 运行依赖
├─ assets/
│  ├─ hero-business-data.png       # 原始首页视觉图
│  └─ hero-business-data-clean.png # 当前应用使用的首页视觉图
├─ previews/                      # 首页视觉预览图
└─ README.md                      # 运行与部署说明
```

## 本地运行

进入项目目录：

```bash
cd streamlit-ai-business-assistant
```

安装依赖：

```bash
pip install -r requirements.txt
```

启动应用：

```bash
streamlit run app.py
```

浏览器打开：

```text
http://127.0.0.1:8501
```

同一 Wi-Fi 下手机访问：

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

然后在手机浏览器或微信内置浏览器中打开电脑的局域网地址。手机顶部显示的 IP 或域名属于浏览器地址栏，不是应用内容；部署到 Streamlit Community Cloud 后会显示公网链接。

## 体验方式

应用内置 3 组样例经营场景：

- 午市新客下滑
- 晚市履约延迟
- 早餐券领取下降

也支持接入自己的测试数据：

- 上传 CSV 文件
- 粘贴公开可访问的 CSV 链接

CSV 至少包含这些字段：

```text
date, period, orders, revenue, new_customers, coupon_claims,
rating_reply_delay, delivery_delay, weather_heat, competitor_index
```

## 部署到 Streamlit Community Cloud

1. 将 `streamlit-ai-business-assistant` 目录提交到 GitHub。
2. 打开 Streamlit Community Cloud。
3. 新建 App，选择对应 GitHub 仓库。
4. Main file path 填写：

```text
streamlit-ai-business-assistant/app.py
```

5. 部署完成后复制公网链接，即可发给微信好友体验。

## 可选 AI 接入

默认不需要密钥即可完整体验。继续追问区域会保留 AI 工具选择入口。

如需接入真实 AI 回答，可配置环境变量：

- Ollama：`OLLAMA_BASE_URL`，可选 `OLLAMA_MODEL`
- OpenAI-compatible API：`AI_API_BASE_URL`、`AI_API_KEY`、`AI_MODEL`

未配置外部 AI 时，应用不会报错，会保留演示模式。
