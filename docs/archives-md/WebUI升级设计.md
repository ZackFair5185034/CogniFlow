# CogniFlow WebUI 升级设计方案
FastAPI + Vue3 全栈界面，训练图集管理、模型管理、数据标注、模型启动

---

## 一、需求概述
对 CogniFlow 项目进行 WebUI 升级，实现以下功能：

 
- **WebUI**：FastAPI + Vue3 全栈界面 
- **训练图集管理**：按目录管理图片分组 
- **模型管理**：完整管理（版本、元数据、指标） 
- **数据标注交互**：通过 WebUI 进行实时标注 
- **模型启动**：加载模型后手动控制开始 
*部署架构：FastAPI 同时托管 Vue3 构建产物（前后端合一）*

## 二、技术选型
           
| 层级 | 技术 | 说明 |
| --- | --- | --- |
| 后端框架 | FastAPI + Uvicorn | 高性能异步 API |
| 数据库 | SQLite + SQLAlchemy | 单用户场景足够 |
| 实时通信 | WebSocket | 训练状态实时推送 |
| 前端框架 | Vue3 + Vite + TypeScript | 现代前端栈 |
| UI 组件库 | Element Plus | Vue3 组件库 |
| 状态管理 | Pinia | Vue3 官方推荐 |
| 图片存储 | 本地文件系统 | 按配置路径存储 |

## 三、数据库模型

### 3.1 Atlas（训练图集）
         
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | Integer | 主键 |
| name | String | 图集名称 |
| description | String | 描述 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3.2 Image（图片）
            
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | Integer | 主键 |
| atlas_id | Integer | 外键关联 Atlas |
| file_path | String | 图片路径 |
| directory | String | 所属目录分组 |
| width | Integer | 图片宽度 |
| height | Integer | 图片高度 |
| annotated | Boolean | 是否已标注 |
| created_at | DateTime | 创建时间 |

### 3.3 Category（标注类别）
       
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | Integer | 主键 |
| name | String | 类别名称 |
| color | String | 颜色（hex） |

### 3.4 Annotation（标注）
          
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | Integer | 主键 |
| image_id | Integer | 外键关联 Image |
| category_id | Integer | 外键关联 Category |
| bbox | JSON | COCO 格式 [x, y, w, h] |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3.5 Model（模型）
            
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | Integer | 主键 |
| name | String | 模型名称 |
| version | String | 版本号 (v1, v2...) |
| file_path | String | 模型文件路径 |
| atlas_id | Integer | 训练用图集 ID |
| metrics | JSON | 训练指标 |
| is_best | Boolean | 是否最佳模型 |
| created_at | DateTime | 创建时间 |

### 3.6 TrainingJob（训练任务）
              
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | Integer | 主键 |
| model_id | Integer | 外键关联 Model |
| atlas_id | Integer | 外键关联 Atlas |
| status | String | pending/running/completed/failed |
| config | JSON | 训练超参 |
| current_step | Integer | 当前步数 |
| total_steps | Integer | 总步数 |
| metrics | JSON | 实时指标 |
| started_at | DateTime | 开始时间 |
| finished_at | DateTime | 结束时间 |

## 四、API 设计

### 4.1 图集管理
            
| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | /api/atlas | 获取图集列表 |
| POST | /api/atlas | 创建图集 |
| GET | /api/atlas/{id} | 获取图集详情 |
| PUT | /api/atlas/{id} | 更新图集 |
| DELETE | /api/atlas/{id} | 删除图集 |
| POST | /api/atlas/{id}/images | 上传图片到图集 |
| GET | /api/atlas/{id}/images | 获取图集图片列表 |
| DELETE | /api/atlas/{id}/images/{image_id} | 删除图片 |

### 4.2 图片管理
          
| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | /api/images | 获取所有图片（分页） |
| GET | /api/images/{id} | 获取图片详情 |
| GET | /api/images/{id}/annotations | 获取图片标注 |
| POST | /api/images/{id}/annotations | 添加标注 |
| PUT | /api/annotations/{id} | 更新标注 |
| DELETE | /api/annotations/{id} | 删除标注 |

### 4.3 类别管理
        
| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | /api/categories | 获取类别列表 |
| POST | /api/categories | 创建类别 |
| PUT | /api/categories/{id} | 更新类别 |
| DELETE | /api/categories/{id} | 删除类别 |

### 4.4 模型管理
          
| 方法 | 路径 | 功能 |
| --- | --- | --- |
| GET | /api/models | 获取模型列表 |
| POST | /api/models | 创建模型记录 |
| GET | /api/models/{id} | 获取模型详情 |
| PUT | /api/models/{id} | 更新模型 |
| DELETE | /api/models/{id} | 删除模型 |
| POST | /api/models/{id}/set-best | 设为最佳模型 |

### 4.5 训练管理
        
| 方法 | 路径 | 功能 |
| --- | --- | --- |
| POST | /api/training/start | 启动训练 |
| POST | /api/training/stop | 停止训练 |
| GET | /api/training/jobs | 获取训练任务列表 |
| GET | /api/training/jobs/{id} | 获取任务详情 |

### 4.6 模型启动
       
| 方法 | 路径 | 功能 |
| --- | --- | --- |
| POST | /api/launch/load | 加载模型 |
| POST | /api/launch/start | 开始执行（手动） |
| POST | /api/launch/stop | 停止执行 |

### 4.7 WebSocket 实时通信
      
| 路径 | 功能 |
| --- | --- |
| /api/ws/training/{job_id} | 训练状态实时推送 |
| /api/ws/launch | 模型执行状态推送 |

```json
{
  "type": "training_update",
  "data": {
    "step": 1000,
    "total_steps": 100000,
    "loss": 0.234,
    "fps": 30.5
  }
}
```

## 五、前端页面结构
            
| 路由 | 页面 | 功能 |
| --- | --- | --- |
| / | 首页仪表盘 | 概览统计入口 |
| /atlas | 图集列表 | 查看/创建/删除图集 |
| /atlas/:id | 图集详情 | 图片网格、目录分组 |
| /annotate/:image_id | 标注页面 | Bounding Box 标注 |
| /models | 模型列表 | 模型管理 |
| /models/:id | 模型详情 | 模型详情和训练历史 |
| /training | 训练监控 | 实时训练状态 |
| /launch | 模型启动 | 加载模型 + 手动控制 |

## 六、核心功能流程

### 6.1 图集管理流程

 
1. 创建图集（名称 + 描述） 
1. 上传图片到图集（支持拖拽批量） 
1. 图片按目录自动分组 
1. 查看图集图片网格 
1. 删除图片或整个图集 

### 6.2 标注流程

 
1. 进入标注页面 
1. 选择图片（从图集选择或上一张/下一张） 
1. 绘制 Bounding Box（鼠标拖拽） 
1. 按数字键 1-9 选择类别 
1. 按 S 保存标注 
1. 按 Z 撤销上一个框 
1. 自动切换下一张图 

### 6.3 训练流程

 
1. 选择模型（已有模型或新建） 
1. 选择训练图集 
1. 配置超参（学习率、batch_size 等） 
1. 启动训练 
1. WebSocket 实时接收训练状态 
1. 查看 loss 曲线 
1. 可暂停/停止训练 

### 6.4 模型启动流程

 
1. 选择已训练模型 
1. 加载模型（初始化推理 pipeline） 
1. 初始化游戏环境 
1. 等待用户手动开始 
1. 用户触发开始后执行推理循环 
1. 实时显示推理结果 

## 七、实现优先级
          
| Phase | 内容 |
| --- | --- |
| Phase 1 | 基础框架 — FastAPI 项目结构、SQLite 连接、基础 API 路由骨架 |
| Phase 2 | 图集管理 — Atlas CRUD、图片上传和管理、目录分组功能 |
| Phase 3 | 标注功能 — 类别管理、Bounding Box 标注、标注保存和加载 |
| Phase 4 | 模型管理 — 模型元数据管理、模型文件管理、训练任务关联 |
| Phase 5 | 训练集成 — 训练启动和停止、WebSocket 实时状态、训练曲线展示 |
| Phase 6 | 模型启动 — 模型加载、执行控制、状态可视化 |

## 八、备注

 
- 图片实际存储在本地文件系统，数据库只存储路径 
- 标注格式使用 COCO Bounding Box [x, y, w, h] 
- WebSocket 心跳间隔 30 秒 
- 训练检查点保存间隔可配置
