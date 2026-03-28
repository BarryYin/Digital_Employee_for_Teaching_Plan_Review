# 教案评审智能体

## 项目介绍

教案评审智能体是一个基于 Flask 开发的 Web 应用，用于提交教案标题、适用年级和教案内容，并返回智能评审结果、改进建议与历史记录。当前项目已从原始的英语作文练习助手演进为面向教学设计场景的教案评审工具。

## 效果展示

### **教案提交与评审**
---
![智能题目生成](demo/generate_writting_topic.png)
---
![智能题目生成](demo/user_input_writting.png)

### **评审结果展示**
![作文自动评审](demo/review_writting.png)

### **历史记录管理**
![历史记录管理](demo/view_writting_history.png)

## 技术架构

- Python 3.6 或更高版本
- Flask 框架
- AI 平台: 讯飞星辰 Agent 开源平台 （[https://github.com/iflytek/astron-agent](https://github.com/iflytek/astron-agent)）


## 配置方法


### 1. 工作流配置

将 `workflow/教案评审员.yml` 导入到讯飞星辰 Agent 开源平台。

建议先在讯飞星辰 Agent 平台完成工作流调试，确认发布接口能够稳定返回评审结果，再接入本项目页面。


### 2. 依赖安装

首先，确保您已安装Python。然后，安装所需的Python包：

```bash
pip install flask json5
```

### 3. API配置

通过讯飞星辰 Agent 平台发布工作流后，可以获取下列参数。推荐使用以下两种方式之一进行本地配置：

方式一：环境变量

```bash
export API_KEY="your_api_key_here"
export API_SECRET="your_api_secret_here"
export API_FLOW_ID="your_flow_id_here"
export XUN_FEI_URL="your_xun_fei_url_here"
```

方式二：创建本地 `config_local.py`

```python
API_KEY = "your_api_key_here"
API_SECRET = "your_api_secret_here"
API_FLOW_ID = "your_flow_id_here"
XUN_FEI_URL = "your_xun_fei_url_here"
```

`config_local.py` 已加入 `.gitignore`，仅用于本地运行，不会被提交到 Git。


## 启动和访问方法

### 1. 启动应用

完成所有配置后，导航到根目录，执行：

```bash
python app.py
```

### 2. 访问应用

应用启动成功后，打开Web浏览器，输入地址 `http://127.0.0.1:5000/` 

## 未来改进方向

### 1.个性化学习路径
系统可以根据不同学段、学科和历史评审结果，生成更有针对性的教案优化建议。

### 2.多维度评分
除综合评分外，可以进一步拆分为规范性、课标契合度、教学逻辑、创新性和合规性等维度。

### 3.评审结果结构化
让工作流统一输出标准 JSON，减少纯文本兼容解析带来的评分偏差和展示差异。

感谢使用教案评审智能体！如有任何问题或建议，欢迎反馈。
