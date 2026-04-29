import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export default api

// Atlas API
export const atlasApi = {
  list: () => api.get('/atlas'),
  get: (id: number) => api.get(`/atlas/${id}`),
  create: (data: { name: string; description?: string }) => api.post('/atlas', data),
  update: (id: number, data: { name?: string; description?: string }) => api.put(`/atlas/${id}`, data),
  delete: (id: number) => api.delete(`/atlas/${id}`),
  getImages: (id: number, directory?: string, page: number = 1, pageSize: number = 50) =>
    api.get(`/atlas/${id}/images`, { params: { directory, page, page_size: pageSize } }),
  getDirectories: (id: number) => api.get(`/atlas/${id}/directories`),
  createDirectory: (id: number, directory: string) => api.post(`/atlas/${id}/directories`, null, { params: { directory } }),
  uploadImages: (id: number, files: FormData, directory?: string) => {
    return api.post(`/atlas/${id}/images`, files, {
      params: directory ? { directory } : {},
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

// Image API
export const imageApi = {
  list: () => api.get('/images'),
  get: (id: number) => api.get(`/images/${id}`),
  getFile: (id: number) => `/api/images/${id}/file`,
  delete: (id: number) => api.delete(`/images/${id}`),
  updateDirectory: (id: number, directory: string) => api.put(`/images/${id}/directory`, null, { params: { directory } }),
  // 批量操作
  batchUpdateDirectory: (imageIds: number[], directory: string) =>
    api.post('/images/batch-update-directory', { image_ids: imageIds, directory }),
  batchDelete: (imageIds: number[]) =>
    api.post('/images/batch-delete', { image_ids: imageIds }),
}

// Category API
export const categoryApi = {
  list: () => api.get('/categories'),
  getTree: () => api.get('/categories/tree'),
  create: (data: { name: string; color?: string; is_directory?: boolean; parent_id?: number | null }) =>
    api.post('/categories', data),
  update: (id: number, data: { name?: string; color?: string; is_directory?: boolean; parent_id?: number | null }) =>
    api.put(`/categories/${id}`, data),
  delete: (id: number) => api.delete(`/categories/${id}`),
}

// Annotation API
export const annotationApi = {
  getByImage: (imageId: number) => api.get(`/annotations/image/${imageId}`),
  create: (data: { image_id: number; category_id: number; bbox: number[] }) => api.post('/annotations', data),
  update: (id: number, data: { category_id?: number; bbox?: number[] }) => api.put(`/annotations/${id}`, data),
  delete: (id: number) => api.delete(`/annotations/${id}`),
}

// Model API
export const modelApi = {
  list: () => api.get('/models'),
  get: (id: number) => api.get(`/models/${id}`),
  create: (data: { name: string; version?: string; file_path?: string; atlas_id?: number }) => api.post('/models', data),
  update: (id: number, data: { name?: string; version?: string; metrics?: object }) => api.put(`/models/${id}`, data),
  delete: (id: number) => api.delete(`/models/${id}`),
  setBest: (id: number) => api.post(`/models/${id}/set-best`),
  upload: (id: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/models/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getTrainingHistory: (id: number) => api.get(`/models/${id}/training-history`),
}

// Training API
export const trainingApi = {
  listJobs: () => api.get('/training/jobs'),
  getJob: (id: number) => api.get(`/training/jobs/${id}`),
  start: (data: { model_id: number; atlas_id: number; config?: object }) => api.post('/training/start', data),
  stop: (jobId: number) => api.post(`/training/stop?job_id=${jobId}`),
  deleteJob: (jobId: number) => api.delete(`/training/jobs/${jobId}`),
  clearCompleted: () => api.delete('/training/jobs'),
  getMetricsHistory: (jobId: number) => api.get(`/training/jobs/${jobId}/metrics-history`),
  getDeviceInfo: () => api.get('/training/device-info'),
  getProgress: () => api.get('/training/progress'),
}

// Launch API
export const launchApi = {
  load: (modelId: number) => api.post(`/launch/load?model_id=${modelId}`),
  start: () => api.post('/launch/start'),
  stop: () => api.post('/launch/stop'),
  status: () => api.get('/launch/status'),
}

// Inference API
export const inferenceApi = {
  detectImage: (file: File, modelId: number, confThreshold: number = 0.25) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/inference/detect/image?model_id=${modelId}&conf_threshold=${confThreshold}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
  },
  detectVideo: (file: File, modelId: number, confThreshold: number = 0.25) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/inference/detect/video?model_id=${modelId}&conf_threshold=${confThreshold}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000, // 上传超时 30s，检测在后台进行
    })
  },
  getVideoJobStatus: (jobId: string) => api.get(`/inference/video/status/${jobId}`),
  getVideoResultUrl: (jobId: string) => `/api/inference/video/result/${jobId}`,
  listTrainedModels: () => api.get('/inference/models'),
}

// RuleEngine API
export const ruleEngineApi = {
  // 节点定义
  getNodeDefinitions: () => api.get('/rule-engine/nodes/definitions'),

  // 规则图 CRUD
  listGraphs: () => api.get('/rule-engine/graphs'),
  getGraph: (id: number) => api.get(`/rule-engine/graphs/${id}`),
  getGraphDetail: (id: number) => api.get(`/rule-engine/graphs/${id}/detail`),
  createGraph: (data: {
    name: string
    description?: string
    nodes_json?: string
    edges_json?: string
    variables_json?: string
    version?: string
    is_active?: boolean
  }) => api.post('/rule-engine/graphs', data),
  updateGraph: (id: number, data: {
    name?: string
    description?: string
    nodes_json?: string
    edges_json?: string
    variables_json?: string
    is_active?: boolean
    thumbnail?: string
  }) => api.put(`/rule-engine/graphs/${id}`, data),
  updateThumbnail: (id: number, thumbnail: string) =>
    api.patch(`/rule-engine/graphs/${id}/thumbnail`, null, { params: { thumbnail } }),
  deleteGraph: (id: number) => api.delete(`/rule-engine/graphs/${id}`),
  validateGraph: (id: number) => api.post(`/rule-engine/graphs/${id}/validate`),
  activateGraph: (id: number) => api.post(`/rule-engine/graphs/${id}/activate`),
  deactivateGraph: (id: number) => api.post(`/rule-engine/graphs/${id}/deactivate`),

  // 执行
  execute: (data: {
    graph_id: number
    trigger_type?: string
    trigger_data?: object
  }) => api.post('/rule-engine/execute', data),

  // 执行历史
  listExecutions: (graphId?: number, limit?: number) =>
    api.get('/rule-engine/executions', { params: { graph_id: graphId, limit } }),
  getExecution: (id: number) => api.get(`/rule-engine/executions/${id}`),
  getExecutionLogs: (id: number) => api.get(`/rule-engine/executions/${id}/logs`),
}
