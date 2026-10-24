/**
 * API 响应类型定义
 * 与后端 backend/schemas.py 中的 Pydantic 模型一一对应
 */

// ============ 通用 ============

/** 通用分页响应 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** 通用消息响应 */
export interface MessageResponse {
  message: string
  [key: string]: unknown
}

// ============ Atlas ============

/** 图集基础 */
export interface AtlasBase {
  name: string
  description?: string
}

/** 图集响应 */
export interface AtlasResponse extends AtlasBase {
  id: number
  created_at: string
  updated_at: string
}

// ============ Image ============

/** 图片响应 */
export interface ImageResponse {
  id: number
  atlas_id: number
  file_path: string
  directory: string | null  // 根目录为 null
  width?: number
  height?: number
  annotated: boolean
  created_at: string
}

/** 图片列表项（精简） */
export interface ImageListItem {
  id: number
  atlas_id: number
}

// ============ Category ============

/** 类别响应 */
export interface CategoryResponse {
  id: number
  name: string
  color: string
  is_directory: boolean
  parent_id: number | null
}

/** 类别导出节点（递归树结构） */
export interface CategoryExportNode {
  name: string
  color: string
  is_directory: boolean
  children: CategoryExportNode[]
}

/** 类别导入请求 */
export interface CategoryImportPayload {
  version: number
  categories: CategoryExportNode[]
}

/** 类别导入结果 */
export interface CategoryImportResult {
  created: number
  skipped: number
  errors: string[]
}

// ============ Annotation ============

/** 标注响应 */
export interface AnnotationResponse {
  id: number
  image_id: number
  category_id: number
  bbox: number[]
  created_at: string
  updated_at: string
}

// ============ Model ============

/** 模型文件响应 */
export interface ModelFileResponse {
  id: number
  model_id: number
  format: string
  file_path: string
  file_size?: number
  precision: string
  is_default: boolean
  created_at: string
}

/** 模型类别元数据 */
export interface ModelCategory {
  id?: number
  name: string
  color?: string
}

/** 模型指标 - 已知字段类型化, 未知字段保留 unknown */
export interface ModelMetrics {
  mAP50?: number
  mAP50_95?: number
  precision?: number
  recall?: number
  num_classes?: number
  categories?: ModelCategory[]
  [key: string]: unknown
}

/** 模型响应 */
export interface ModelResponse {
  id: number
  name: string
  version?: string
  pretrained_model?: string
  file_path?: string
  format?: string
  device_preference?: string
  precision?: string
  atlas_id?: number
  metrics?: ModelMetrics
  is_best: boolean
  created_at: string
  files: ModelFileResponse[]
  input_shape?: string
}

/** 模型导出响应 */
export interface ModelExportResponse {
  success: boolean
  output_path: string
  file_size: number
  available_formats: string[]
  target_format: string
  half: boolean
}

// ============ Training ============

/** 训练任务响应 */
export interface TrainingJobResponse {
  id: number
  model_id: number
  atlas_id: number
  status: string
  config?: Record<string, unknown>
  current_step: number
  total_steps?: number
  metrics?: Record<string, unknown>
  started_at?: string
  finished_at?: string
  _displayStatus?: string
  message?: string
}

// ============ Launch ============

/** 推理加载状态 */
export interface InferenceLoadStatus {
  loaded: boolean
  model_id?: number
  model_name?: string
  device?: string
  precision?: string
  format?: string
}

// ============ Inference ============

/** 推理检测结果项 - 单个目标 */
export interface DetectionItem {
  bbox: [number, number, number, number]  // [x1, y1, x2, y2]
  class_id: number
  class_name: string
  confidence: number
}

/** 类别配置项 (来自后端) */
export interface CategoryConfig {
  id?: number
  name: string
  color?: string
}

/** 图片检测响应 - 与 backend/routers/inference.py:detect_image 返回一致 */
export interface DetectImageResponse {
  success: boolean
  original_image?: string
  result_image?: string
  result_image_base64: string
  detections: DetectionItem[]
  num_detections: number
  categories?: CategoryConfig[]
  used_format?: string | null
}

/** 推理任务记录 */
export interface InferenceJob {
  id: number
  job_id: string
  model_id: number
  model_name: string
  file_name: string
  file_path: string
  file_type: 'image' | 'video'
  conf_threshold: number
  device: string
  precision: string
  used_format: string
  status: string
  total_frames: number | null
  total_detections: number
  thumbnail: string | null
  created_at: string
  finished_at: string | null
}

// ============ RuleEngine ============

/** 节点输入/输出端口定义 */
export interface NodePort {
  name: string
  type: string
  label?: string
}

/** 节点定义 */
export interface NodeDefinition {
  type: string
  category: string
  label: string
  description?: string
  icon?: string
  inputs: NodePort[]
  outputs: NodePort[]
  config_schema: Record<string, ConfigSchemaProperty>
}

/** 变量类型 */
export type VariableType = 'STRING' | 'NUMBER' | 'BOOLEAN' | 'IMAGE' | 'BBOX'

/** 变量默认值类型 */
export type VariableDefaultValue = string | number | boolean | (string | number)[] | null

/** 节点配置 Schema 属性 */
export interface ConfigSchemaProperty {
  type: string
  title?: string
  description?: string
  default?: VariableDefaultValue
  minimum?: number
  maximum?: number
  step?: number
  enum?: string[]
  widget?: string
  visible?: string
  /** multiselect 控件是否允许用户输入自定义选项（不限于 enum） */
  allow_create?: boolean
  /** 是否隐藏该字段（true = 在 UI 中不渲染） */
  hidden?: boolean
}

/** 规则图节点数据 */
export interface RuleNodeData {
  /** 节点类型标识 */
  type: string
  /** 节点显示名称 */
  label?: string
  /** 节点分类 */
  category: string
  /** 输入端口定义 */
  inputs?: NodePort[]
  /** 输出端口定义 */
  outputs?: NodePort[]
  /**
   * 端口连线关系 - 目标端口名 -> 上游节点与上游输出端口。
   *
   * 与 `inputs`/`outputs`(端口元数据数组, 用于渲染手柄)职责分离。
   * 后端 `_resolve_inputs` 读取此字段解析上游数据。
   */
  connections?: Record<string, { node_id: string; output: string }>
  /** 配置 Schema */
  configSchema?: Record<string, ConfigSchemaProperty>
  /** 节点配置值 */
  config?: Record<string, VariableDefaultValue>
  /** 执行状态 */
  status?: 'idle' | 'running' | 'success' | 'failed'
  /** 是否选中 */
  selected?: boolean
  /** 是否拖拽中 */
  dragging?: boolean
  /** 节点配置区展开状态（用于内联配置折叠/展开） */
  configExpanded?: boolean
}

/** 规则图节点 - 用于存储和传输 */
export interface GraphNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: RuleNodeData
}

/** 规则图连接边 - 用于存储和传输 */
export interface GraphEdge {
  id: string
  source: string
  target: string
  source_handle?: string
  target_handle?: string
}

/**
 * 端口类型兼容矩阵响应。
 *
 * 后端 `backend/services/rule_engine/port_types.py` 是矩阵的唯一事实源。
 */
export interface PortCompatibilityResponse {
  /** 源类型 -> 兼容的目标类型列表 */
  matrix: Record<string, string[]>
  /** 全部端口类型 */
  types: string[]
}

/**
 * 规则图校验结果。
 *
 * 后端返回 `{valid, errors[], error}`; `error` 是单条错误的向后兼容字段。
 */
export interface RuleGraphValidateResult {
  valid: boolean
  /** 逐条错误信息 */
  errors: string[]
  /** 单条错误(向后兼容) */
  error?: string | null
}

/** 规则图基础 */
export interface RuleGraphBase {
  name: string
  description?: string
  nodes_json: string
  edges_json: string
  variables_json?: string
  version: string
  is_active: boolean
  thumbnail?: string
}

/** 规则图响应 */
export interface RuleGraphResponse extends RuleGraphBase {
  id: number
  created_at: string
  updated_at: string
}

/** 规则图详情（含解析后的节点/边） */
export interface RuleGraphDetail extends RuleGraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  variables?: Record<string, unknown>
}

/** 执行触发请求 */
export interface ExecutionTrigger {
  graph_id: number
  trigger_type?: string
  trigger_data?: Record<string, unknown>
}

/** 执行结果响应 */
export interface ExecutionResponse {
  execution_id: number
  status: string
  result?: Record<string, unknown>
}

/** 执行历史响应 */
export interface ExecutionHistoryResponse {
  id: number
  graph_id: number
  status: string
  start_time: string
  end_time?: string
  trigger_type?: string
  result_json?: string
  logs_json?: string
}
