## PDF Highlighter-AI Translator 使用指南

**作者：Teng**

---

### 1. 项目概述

PDF Highlighter-AI Translator 是一款集 PDF 高亮、注释和 AI 翻译于一体的文档阅读工具，专为外语学习者和专业读者设计。它将大语言模型的强大能力与直观的 PDF 操作体验相结合，帮助您高效浏览、理解并整理文档内容。

---

### 2. 安装与部署

#### 2.1 Windows 可执行版

1. 从 Release 页面下载 **PDF\_Highlighter-AI\_Translator.zip**
2. 解压后，确保以下文件位于同一目录：

   * `PDF_Highlighter-AI_Translator.exe`
   * `ai.cfg`
   * `ui.cfg`

#### 2.2 源码部署（跨平台）

```bash
# 克隆仓库并进入项目目录
git clone https://github.com/twy2020/PDF_Highlighter-AI_Translator.git
cd PDF_Highlighter-AI_Translator

# 推荐使用 Conda 创建虚拟环境
conda create -n pdf_tran python=3.12 -y
conda activate pdf_tran

# 安装依赖
pip install -r requirements.txt
```

---

### 3. 配置指南

#### 3.1 AI 翻译接口 (`ai.cfg`)

```jsonc
{
  "API_URL":       "https://api.siliconflow.cn/v1/chat/completions",
  "API_KEY":       "您的 API 密钥",
  "MODEL_NAME":    "deepseek-ai/DeepSeek-V3",
  "REQUEST_TIMEOUT": 60,
  "WORD_PROMPT":   "初中及以上水平的、专业的、难的、冷门的、重点的"
}
```

> **提示**：使用作者邀请链接注册 siliconflow，可获得免费余额 https://cloud.siliconflow.cn/i/jLLp0NCk

#### 3.2 界面偏好设置 (`ui.cfg`)

```jsonc
{
  "DARK_MODE":     true,      // 是否默认启用暗黑模式
  "INVERT_PDF":    false,     // 是否翻转 PDF 背景色
  "CONTRAST_LEVEL": 0.85      // 对比度（范围 0.2–1.0）
}
```

---

### 4. 快速上手

#### 4.1 启动应用

* **命令行启动**

  ```bash
  python main.py              # 打开主界面
  python main.py path/to/doc.pdf  # 直接加载指定 PDF
  ```
* **Windows 双击**
  直接运行 `PDF_Highlighter-AI_Translator.exe`。

#### 4.2 打开与导航

* **打开 PDF**：点击工具栏上的 “打开 PDF”
* **页面跳转**：

  * 左侧缩略图面板
  * 底部页码输入框
* **缩放视图**：Ctrl + 鼠标滚轮

---

### 5. 核心功能演示

#### 5.1 智能文本选择

* 鼠标拖拽即可选中任意文本区域
* 自动处理换行、上下标、连字符

#### 5.2 翻译与生词提取

1. 选中文本后，在左侧操作面板选择：

   * **整段翻译**
   * **提取并翻译生词**
2. 查看右侧 “翻译结果” 或 “生词列表”

#### 5.3 高亮与注释

* **单词/句子高亮**：点击表格首列图标
* **自定义颜色**：输入十六进制色码或使用颜色选择器
* **显示翻译**：悬停已高亮区域，即可查看工具提示

#### 5.4 批量操作

* **本页全高亮／全清除**
* **全文全高亮／全清除**

---

### 6. 导出功能

#### 6.1 单词与句子导出

* **当前页导出**：对应标签页点击 “导出本页”
* **全文导出**：对应标签页点击 “导出全部”

#### 6.2 带注释 PDF 导出

* 工具栏点击 “导出 PDF”，生成包含所有高亮与注释的文件

---

### 7. 界面自定义

* **暗黑／明亮模式**：工具栏切换按钮
* **PDF 颜色翻转**：工具栏 “翻转” 按钮
* **对比度调整**：工具栏滑块
* **缩略图面板**：

  * 点击跳转
  * 带状态指示的高亮预览

---

### 8. 高级技巧

#### 8.1 微调生词提取

在 `ai.cfg` 中调整 `WORD_PROMPT`，例如：

```jsonc
"WORD_PROMPT": "专业术语、技术词汇、高级词汇"
```

#### 8.2 界面设置

修改 `ui.cfg` 中的主题、对比度和翻转设置，保存后重启应用生效。

---

### 9. 常见问题与解决

| 问题     | 解决方案                                                  |
| ------ | ----------------------------------------------------- |
| 翻译失败   | 1. 检查 `ai.cfg` 中 API 配置是否正确<br>2. 确保网络正常<br>3. 缩短选区长度 |
| 高亮不显示  | 1. 确认当前页<br>2. 尝试缩放视图（Ctrl+滚轮）<br>3. 更换高亮颜色           |
| 缩略图不同步 | 1. 页面切换时自动更新<br>2. 重启应用             |

---

### 10. 技术支持与贡献

* **问题反馈 & 功能建议**：
  GitHub Issues → [https://github.com/twy2020/PDF\_Highlighter-AI\_Translator/issues](https://github.com/twy2020/PDF_Highlighter-AI_Translator/issues)
* **联系邮箱**：[tenwonyun@gmail.com](mailto:tenwonyun@gmail.com)
* **欢迎贡献**：Fork & Pull Request，详见项目 README

---

**PDF Highlighter-AI Translator** 致力于为外语文献阅读提供高效、便捷的解决方案。感谢您的使用与支持！
