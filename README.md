# 沙海拆城者 · Sand City Breaker

一款直接在浏览器运行的第一人称 3D 城市拆除游戏。建筑模型由 Blender 制作，游戏使用 Three.js 渲染。

## 在线游玩

GitHub Pages：<https://flycarl.github.io/sand-city-breaker/>

建议使用最新版 Chrome 或 Edge，并允许页面锁定鼠标。

## 玩法特色

- 8 个逐步扩大的关卡：从单栋训练建筑到完整城市。
- 建筑被拆分成局部结构块，需要逐块破坏；失去支撑的结构会坍塌。
- 关卡计时、个人排名、通关进度与装备方案保存在浏览器 `localStorage`。
- 冷兵器开局，随后依次解锁激光枪、粒子炮、等离子炮、轨道陨石和奇点坍缩器。
- 战术仓库支持携带最多 10 件武器，并在游戏中用数字键切换。

## 操作

- `W A S D`：移动
- `Shift`：冲刺
- 鼠标移动：第一人称视角
- 鼠标左键：攻击
- `1–0` 或滚轮：切换武器
- `Esc`：释放鼠标并暂停

## 本地运行

项目是纯静态站点。由于浏览器不允许从 `file://` 安全加载 GLB 模型，请通过本地 HTTP 服务器运行：

```bash
python3 -m http.server 4173
```

然后访问 <http://127.0.0.1:4173/>。

## 项目结构

- `index.html`：完整游戏、UI、Three.js 场景和玩法逻辑。
- `blender_city/waterfront_city.glb`：浏览器中使用的城市模型。
- `blender_city/waterfront_city.blend`：Blender 可编辑源文件。
- `blender_city/create_city.py`：城市模型生成脚本。

Three.js 通过 jsDelivr CDN 加载，游戏不需要后端服务。

## 技术与素材

- 渲染与控制：[Three.js](https://threejs.org/)（MIT License）
- 城市模型与游戏代码：本项目原创内容
