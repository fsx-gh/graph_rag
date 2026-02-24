# 人物关联知识图谱系统 - Vue 3 版本

这是一个基于 Vue 3 + Vite + D3.js 构建的人物关联知识图谱可视化系统。

## 项目结构

```
frontend-vue/
├── src/
│   ├── components/         # Vue 组件
│   │   ├── AlertMessage.vue      # 提示消息组件
│   │   ├── BaseModal.vue         # 基础模态框组件
│   │   ├── GraphCanvas.vue       # 图谱画布组件（D3.js）
│   │   ├── LeftPanel.vue         # 左侧详情面板
│   │   ├── MenuBar.vue           # 顶部菜单栏
│   │   ├── PathModal.vue         # 路径查询模态框
│   │   ├── PersonModal.vue       # 添加人物模态框
│   │   ├── RelationModal.vue     # 添加关系模态框
│   │   ├── SearchModal.vue       # 搜索模态框
│   │   ├── StatsModal.vue        # 统计信息模态框
│   │   └── SubgraphModal.vue     # 子图查询模态框
│   ├── services/          # API 服务
│   │   └── api.js              # API 调用封装
│   ├── styles/            # 样式文件（模块化结构）
│   │   ├── main.css           # 主样式入口（导入所有模块）
│   │   ├── variables.css      # CSS变量和全局样式
│   │   ├── menu.css           # 菜单栏样式
│   │   ├── sidebar.css        # 侧边栏样式
│   │   ├── graph.css          # 图谱样式
│   │   ├── forms.css          # 表单样式
│   │   ├── modals.css         # 模态框样式
│   │   ├── utils.css          # 全局工具和响应式
│   │   └── README.md          # 样式模块说明
│   ├── App.vue            # 根组件
│   └── main.js            # 应用入口
├── public/                # 静态资源
├── index.html            # HTML 模板
├── package.json          # 项目配置
└── vite.config.js        # Vite 配置
```

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vite** - 下一代前端构建工具
- **D3.js** - 数据可视化库
- **Composition API** - Vue 3 组合式 API

## 主要功能

### 1. 图谱可视化
- 力导向图布局（Force-Directed Graph）
- 节点拖拽、缩放、平移
- 节点和关系的高亮显示
- 动态参数调节（节点大小、连接距离、排斥力）

### 2. 数据管理
- 添加/删除人物节点
- 建立/删除人物关系
- 导入/导出图谱数据（JSON格式）
- 加载预设数据集（清朝历史、西游记、红楼梦、四代家谱）

### 3. 分析功能
- 人物搜索（按姓名、职业、描述）
- 最短路径查询
- 人物圈子分析（子图提取）
- 统计信息面板
  - 基本统计（节点数、关系数、关系类型）
  - 网络指标（平均度数、网络密度）
  - 关系类型分布
  - 最高连接度人物
  - 连通分量分组

## 安装和运行

### 前置要求
- Node.js >= 16.0.0
- npm 或 yarn

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

应用将运行在 `http://localhost:3000`

### 构建生产版本

```bash
npm run build
```

构建产物将输出到 `dist/` 目录

### 预览生产构建

```bash
npm run preview
```

## 后端配置

确保后端 Flask 服务运行在 `http://localhost:5000`

如需修改后端地址，编辑 `src/services/api.js` 中的 `API_URL` 常量。

## 组件说明

### MenuBar 菜单栏
提供文件、编辑、分析等菜单选项，以及图谱参数调节控件。

### LeftPanel 左侧面板
显示选中节点的详细信息和关联关系。

### GraphCanvas 图谱画布
核心组件，使用 D3.js 渲染力导向图，支持交互操作。

### 各种 Modal 组件
封装不同功能的对话框，包括添加人物、添加关系、搜索、路径查询、统计信息等。

## API 服务

所有后端 API 调用都封装在 `src/services/api.js` 中，分为以下模块：

- **graphService**: 图谱数据的获取、导入、导出、初始化和统计
- **personService**: 人物的添加、删除和搜索
- **relationshipService**: 关系的添加和删除
- **networkService**: 路径查询和子图提取

## 样式系统

使用 CSS 变量定义主题颜色和样式，便于统一管理和修改：

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f7;
  --text-primary: #000000;
  --accent-color: #007aff;
  --danger-color: #ff3b30;
  --success-color: #34c759;
}
```

## 相比原版的改进

### 架构优化
- ✅ 组件化：将单文件 HTML 拆分为多个可维护的 Vue 组件
- ✅ 代码分离：HTML、CSS、JavaScript 完全分离
- ✅ 模块化：API 调用、工具函数独立封装
- ✅ 类型化：使用 props 和 emits 明确组件接口

### 开发体验
- ✅ 热更新：Vite 提供极速的 HMR（热模块替换）
- ✅ 构建优化：生产构建自动压缩和优化
- ✅ 开发工具：Vue DevTools 支持
- ✅ 代码组织：清晰的目录结构

### 性能优化
- ✅ 按需加载：组件懒加载
- ✅ 响应式：Vue 3 的 Proxy 响应式系统
- ✅ 计算属性：自动缓存和依赖追踪
- ✅ 异步处理：使用 async/await 简化异步逻辑

## 注意事项

1. 确保后端服务正常运行
2. D3.js 操作直接操作 DOM，避免与 Vue 的响应式系统冲突
3. 图谱数据较大时可能影响性能，建议分批加载
4. 导出的 JSON 文件需符合项目定义的格式

## 许可证

本项目仅供学习和研究使用。
