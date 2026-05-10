import axios, { type AxiosInstance } from 'axios'
import type {
  AtlasResponse,
  ImageResponse,
  ImageListItem,
  PaginatedResponse,
  CategoryResponse,
  CategoryImportPayload,
  CategoryImportResult,
  AnnotationResponse,
  ModelResponse,
  ModelFileResponse,
  ModelExportResponse,
  TrainingJobResponse,
  InferenceLoadStatus,
  InferenceJob,
  DetectImageResponse,
  NodeDefinition,
  RuleGraphResponse,
  RuleGraphDetail,
  ExecutionResponse,
  ExecutionHistoryResponse,
} from '@/types/api'

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

export default api

// Atlas API
export const atlasApi = {
  list: () => api.get<AtlasResponse[]>('/atlas'),
  get: (id: number) => api.get<AtlasResponse>(`/atlas/${id}`),
  create: (data: { name: string; description?: string }) => api.post<AtlasResponse>('/atlas', data),
  update: (id: number, data: { name?: string; description?: string }) => api.put<AtlasResponse>(`/atlas/${id}`, data),
  delete: (id: number) => api.delete(`/atlas/${id}`),
  getImages: (
    id: number,
    directory?: string,
    page: number = 1,
    pageSize: number = 50,
    sortBy?: string,
    sortOrder?: string,
  ) =>
    api.get<PaginatedResponse<ImageResponse>>(`/atlas/${id}/images`, {
      params: { directory, page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder },
    }),
  getDirectories: (id: number) => api.get<string[]>(`/atlas/${id}/directories`),
  createDirectory: (id: number, directory: string) =>
    api.post(`/atlas/${id}/directories`, null, { params: { directory } }),
  deleteDirectory: (id: number, directory: string) =>
    api.delete(`/atlas/${id}/directories`, { params: { directory } }),
  uploadImages: (id: number, files: FormData, directory?: string) =>
    api.post(`/atlas/${id}/images`, files, {
      params: directory ? { directory } : {},
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  uploadVideo: (id: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/atlas/${id}/video/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
  extractVideoFrames: (id: number, videoPath: string, extractCount: number, directory?: string) =>
    api.post(`/atlas/${id}/video/extract-frames`, null, {
      params: { video_path: videoPath, extract_count: extractCount, directory },
    }),
  extractVideoFramesAsync: (id: number, videoPath: string, extractCount: number) =>
    api.post(`/atlas/${id}/video/extract-frames/async`, null, {
      params: { video_path: videoPath, extract_count: extractCount },
    }),
  getExtractJobStatus: (id: number, jobId: string) =>
    api.get(`/atlas/${id}/video/extract-frames/${jobId}/status`),
  cancelExtractJob: (id: number, jobId: string) =>
    api.delete(`/atlas/${id}/video/extract-frames/${jobId}`),
  batchDownloadImages: (id: number, imageIds: number[]) =>
    api.get(`/atlas/${id}/images/download`, {
      params: { image_ids: imageIds.join(',') },
      responseType: 'blob',
    }),
}

// Image API
export const imageApi = {
  list: () => api.get<ImageListItem[]>('/images/'),
  get: (id: number) => api.get<ImageResponse>(`/images/${id}`),
  getFile: (id: number) => `/api/images/${id}/file`,
  delete: (id: number) => api.delete(`/images/${id}`),
  updateDirectory: (id: number, directory: string) =>
    api.put(`/images/${id}/directory`, null, { params: { directory } }),
  batchUpdateDirectory: (imageIds: number[], directory: string) =>
    api.post('/images/batch-update-directory', { image_ids: imageIds, directory }),
  batchDelete: (imageIds: number[]) =>
    api.post('/images/batch-delete', { image_ids: imageIds }),
}

// Category API
export const categoryApi = {
  list: () => api.get<CategoryResponse[]>('/categories'),
  getTree: () => api.get<Record<string, unknown>[]>('/categories/tree'),
  create: (data: { name: string; color?: string; is_directory?: boolean; parent_id?: number | null }) =>
    api.post<CategoryResponse>('/categories', data),
  update: (id: number, data: { name?: string; color?: string; is_directory?: boolean; parent_id?: number | null }) =>
    api.put<CategoryResponse>(`/categories/${id}`, data),
  delete: (id: number) => api.delete(`/categories/${id}`),
  export: () => api.get<CategoryImportPayload>('/categories/export'),
  import: (data: CategoryImportPayload) =>
    api.post<CategoryImportResult>('/categories/import', data),
}

// Annotation API
export const annotationApi = {
  getByImage: (imageId: number) => api.get<AnnotationResponse[]>(`/annotations/image/${imageId}`),
  create: (data: { image_id: number; category_id: number; bbox: number[] }) =>
    api.post<AnnotationResponse>('/annotations', data),
  update: (id: number, data: { category_id?: number; bbox?: number[] }) =>
    api.put<AnnotationResponse>(`/annotations/${id}`, data),
  delete: (id: number) => api.delete(`/annotations/${id}`),
}

// Model API
export const modelApi = {
  list: () => api.get<ModelResponse[]>('/models'),
  get: (id: number) => api.get<ModelResponse>(`/models/${id}`),
  create: (data: { name: string; version?: string; file_path?: string; atlas_id?: number }) =>
    api.post<ModelResponse>('/models', data),
  update: (
    id: number,
    data: {
      name?: string
      version?: string
      metrics?: Record<string, unknown>
      device_preference?: string
      precision?: string
    },
  ) => api.put<ModelResponse>(`/models/${id}`, data),
  delete: (id: number) => api.delete(`/models/${id}`),
  setBest: (id: number) => api.post<ModelResponse>(`/models/${id}/set-best`),
  getDownloadUrl: (id: number) => `/api/models/${id}/download`,
  upload: (id: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<ModelResponse>(`/models/${id}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getTrainingHistory: (id: number) => api.get(`/models/${id}/training-history`),
  exportAsync: (id: number, data: { target_format: string; half?: boolean; device?: string }) =>
    api.post(`/models/${id}/export`, data),
  export: (id: number, data: { target_format: string; half?: boolean; device?: string }) =>
    api.post<ModelExportResponse>(`/models/${id}/export/sync`, data),
  listFiles: (id: number) => api.get<ModelFileResponse[]>(`/models/${id}/files`),
  deleteFile: (id: number, fileId: number) => api.delete(`/models/${id}/files/${fileId}`),
  setDefaultFormat: (id: number, fileId: number) =>
    api.post<ModelResponse>(`/models/${id}/files/${fileId}/set-default`),
}

// Training API
export const trainingApi = {
  listJobs: () => api.get<TrainingJobResponse[]>('/training/jobs'),
  getJob: (id: number) => api.get<TrainingJobResponse>(`/training/jobs/${id}`),
  start: (data: { model_id: number; atlas_id: number; config?: Record<string, unknown> }) =>
    api.post<TrainingJobResponse>('/training/start', data),
  stop: (jobId: number) => api.post(`/training/stop?job_id=${jobId}`),
  deleteJob: (jobId: number) => api.delete(`/training/jobs/${jobId}`),
  clearCompleted: () => api.delete('/training/jobs'),
  getMetricsHistory: (jobId: number) => api.get(`/training/jobs/${jobId}/metrics-history`),
  getDeviceInfo: () => api.get('/training/device-info'),
  getProgress: () => api.get('/training/progress'),
}

// Launch API
export const launchApi = {
  load: (modelId: number) => api.post<InferenceLoadStatus>(`/launch/load?model_id=${modelId}`),
  start: () => api.post('/launch/start'),
  stop: () => api.post('/launch/stop'),
  status: () => api.get<InferenceLoadStatus>('/launch/status'),
}

// Inference API
export const inferenceApi = {
  detectImage: (
    file: File,
    modelId: number,
    confThreshold: number = 0.25,
    device: string = 'auto',
    precision: string = 'fp32',
    format: string = 'auto',
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<DetectImageResponse>(
      `/inference/detect/image?model_id=${modelId}&conf_threshold=${confThreshold}&device=${device}&precision=${precision}&format=${format}`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
      },
    )
  },
  detectVideoStream: (
    file: File,
    modelId: number,
    confThreshold: number = 0.25,
    device: string = 'auto',
    precision: string = 'fp32',
    format: string = 'auto',
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(
      `/inference/detect/video/stream?model_id=${modelId}&conf_threshold=${confThreshold}&device=${device}&precision=${precision}&format=${format}`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
      },
    )
  },
  stopVideoStream: (jobId: string) => api.post(`/inference/detect/stop/${jobId}`),
  listTrainedModels: () => api.get('/inference/models'),
  listInferenceJobs: () => api.get<InferenceJob[]>('/inference/jobs'),
  rerunInferenceJob: (
    jobId: string,
    modelId: number,
    confThreshold: number = 0.25,
    device: string = 'auto',
    format: string = 'auto',
  ) =>
    api.post(`/inference/jobs/${jobId}/rerun?model_id=${modelId}&conf_threshold=${confThreshold}&device=${device}&format=${format}`),
  clearInferenceJobs: () => api.delete('/inference/jobs'),
}

// RuleEngine API
export const ruleEngineApi = {
  getNodeDefinitions: () => api.get<NodeDefinition[]>('/rule-engine/nodes/definitions'),
  listGraphs: () => api.get<RuleGraphResponse[]>('/rule-engine/graphs'),
  getGraph: (id: number) => api.get<RuleGraphResponse>(`/rule-engine/graphs/${id}`),
  getGraphDetail: (id: number) => api.get<RuleGraphDetail>(`/rule-engine/graphs/${id}/detail`),
  createGraph: (data: {
    name: string
    description?: string
    nodes_json?: string
    edges_json?: string
    variables_json?: string
    version?: string
    is_active?: boolean
  }) => api.post<RuleGraphResponse>('/rule-engine/graphs', data),
  updateGraph: (
    id: number,
    data: {
      name?: string
      description?: string
      nodes_json?: string
      edges_json?: string
      variables_json?: string
      is_active?: boolean
      thumbnail?: string
    },
  ) => api.put<RuleGraphResponse>(`/rule-engine/graphs/${id}`, data),
  updateThumbnail: (id: number, thumbnail: string) =>
    api.patch<RuleGraphResponse>(`/rule-engine/graphs/${id}/thumbnail`, null, { params: { thumbnail } }),
  deleteGraph: (id: number) => api.delete(`/rule-engine/graphs/${id}`),
  validateGraph: (id: number) => api.post(`/rule-engine/graphs/${id}/validate`),
  activateGraph: (id: number) => api.post<RuleGraphResponse>(`/rule-engine/graphs/${id}/activate`),
  deactivateGraph: (id: number) => api.post<RuleGraphResponse>(`/rule-engine/graphs/${id}/deactivate`),
  execute: (data: {
    graph_id: number
    trigger_type?: string
    trigger_data?: Record<string, unknown>
  }) => api.post<ExecutionResponse>('/rule-engine/execute', data),
  listExecutions: (graphId?: number, limit?: number) =>
    api.get<ExecutionHistoryResponse[]>('/rule-engine/executions', {
      params: { graph_id: graphId, limit },
    }),
  getExecution: (id: number) => api.get<ExecutionHistoryResponse>(`/rule-engine/executions/${id}`),
  getExecutionLogs: (id: number) => api.get(`/rule-engine/executions/${id}/logs`),
}
