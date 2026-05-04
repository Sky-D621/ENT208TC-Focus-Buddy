# Focus Buddy · Frontend

两个独立 HTML 页面，双击用浏览器打开即可，无需任何框架或构建工具。

## 文件说明

| 文件 | 用途 |
|---|---|
| `elderly.html`      | 老人端：大字体温湿度 + 自动语音播报 AI 提醒 + 今日提醒列表 |
| `family.html`       | 子女端：实时监控 / 前端对接说明 / 老人信息 / 用药管理 / 闹钟设置 |
| `api.py`            | 后端 API（放入 Focus-Buddy/ 目录） |
| `ai_coach.py`       | 更新版 AI 评估（同时返回标签和中文文案） |
| `sensor_monitor.py` | 更新版传感器监听（把文案写入心跳文件） |

---

## 使用前修改后端地址

两个 HTML 文件里各有一行，把 `localhost:8000` 换成实际后端地址：

```js
const API = 'http://localhost:8000';  // ← 改这里
```

演示时换成 cloudflared 地址：
```js
const API = 'https://superb-recommended-earth-stability.trycloudflare.com';
```

子女端的"前端对接"页面里也有一个输入框可以动态修改，改完后把地址告知前端同学。

---

## 前端同学接入说明（最简版）

只需在你们的代码里加这几行：

```js
// 每隔 15 秒拉一次
const res     = await fetch('后端地址/api/status');
const data    = await res.json();
const message = data.message;  // AI 生成的中文提醒文案

if (message) {
  // 方式一：你们自己的语音模块
  yourSpeechModule.play(message);

  // 方式二：浏览器内置（无需任何依赖）
  const u = new SpeechSynthesisUtterance(message);
  u.lang  = 'zh-CN';
  window.speechSynthesis.speak(u);
}
```

---

## 后端接口一览

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/status`   | GET  | 返回实时温湿度、状态、AI 提醒文案 |
| `/api/logs`     | GET  | 返回历史记录，支持 `?n=20` 参数 |
| `/api/settings` | GET  | 读取子女端设置 |
| `/api/settings` | POST | 保存子女端设置（JSON body） |

---

## 更新的后端文件

把以下三个文件**替换**到 `Focus-Buddy/` 目录：

- `api.py` → 新增 `/api/settings` 接口，`/api/status` 新增 `message` 字段
- `ai_coach.py` → 改为同时返回标签和自然语言文案 `(label, message)`
- `sensor_monitor.py` → 把 AI 文案写入心跳文件第4列，前端通过接口读取

> ⚠️ `sensor_monitor.py` 调用 `evaluate_environment_state` 时现在返回的是 `(label, message)` 元组，注意用 `label, message = evaluate_environment_state(temp, humi)` 解包。
