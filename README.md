# 🎙️ Natural AI Podcast

> **AI 驱动的自然质感对谈播客系统。** 结合 4 阶段 LLM 脚本优化管线与 MiniMax 高级 TTS 技术，打造像真人一样闲聊的播客体验。

[![Frontend - Astro](https://img.shields.io/badge/Frontend-Astro-ff5d01?style=flat-square&logo=astro)](https://astro.build/)
[![UI - React](https://img.shields.io/badge/UI-React-61dafb?style=flat-square&logo=react)](https://react.dev/)
[![Backend - FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![License - MIT](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

---

## ✨ 核心特性

- **🌊 极致视觉设计**：复刻 `Hacker Podcast` 的线性极简布局，融合 **OpenAI** 官网的高对比度纯净感与 **蓝绿渐变** 科技美学。
- **🧠 4 阶段脚本管线**：任意素材 → 基础改写 → 节奏调整 → 聊天质感注入 → 最终审核，支持 **Kimi 2.6, DeepSeek V4, MiniMax M2.7, Qwen** 等多种顶尖 LLM。
- **🎧 真人质感播客**：基于 MiniMax TTS 引擎，支持林深、若水等多角色自然对谈，自动注入停顿 `<#0.2#>` 与情绪标签 `(chuckle)`。
- **📱 响应式三栏布局**：侧边栏持久化、全局播放器、深色模式完美适配，支持全站无刷新页面跳转（Client Router）。
- **🔗 多平台支持**：预留小宇宙、网易云音乐、RSS 订阅接口。

---

## 🛠️ 技术架构

### 前端 (Frontend)
- **Framework**: Astro 6.0 (SSG/SPA Hybrid)
- **UI Library**: React 19
- **Icons**: Lucide Icons
- **Transitions**: Astro Client Router (View Transitions)
- **Styling**: Mesh Gradient + Glassmorphism (CSS)

### 后端 (Backend)
- **Framework**: FastAPI (Python 3.10+)
- **TTS Engine**: MiniMax Voice 2.8
- **Audio Process**: FFmpeg (音频剪辑、合成与归一化)

---

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/wang-h/natural-ai-podcast.git
cd natural-ai-podcast
```

### 2. 配置环境
在根目录创建 `.env` 文件，填入必要的 API Key：
```env
# MiniMax API
MINIMAX_API_KEY="your_minimax_key"
MINIMAX_GROUP_ID="your_group_id"

# LLM APIs (Optional, base_url support)
OPENAI_API_KEY="your_openai_key"
OPENAI_BASE_URL="https://api.minimaxi.com/v1"
```

### 3. 安装依赖
#### 后端 (Python)
```bash
pip install -r requirements.txt
```
#### 前端 (Node.js)
```bash
cd frontend
npm install
npm run build  # 编译静态文件到 dist 目录
```

### 4. 启动服务
```bash
# 回到项目根目录
python main.py
```
访问 `http://localhost:8700` 即可开始使用。

---

## 📸 界面预览

- **首页**：线性剧集列表，支持点击即听。
- **文本 → 脚本**：强大的 4 阶段 LLM 协同优化界面。
- **脚本 → 音频**：可视化 TTS 渲染流程，支持 Deepling 品牌 Intro/Outro 自动合成。

---

## 📝 开源协议

本项目基于 **MIT License** 协议开源。

---

Developed with ❤️ by [wang-h](https://github.com/wang-h)
