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
  getImages: (id: number, directory?: string) => api.get(`/atlas/${id}/images`, { params: directory ? { directory } : {} }),
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
  get: (id: number) => api.get(`/images/${id}`),
  delete: (id: number) => api.delete(`/images/${id}`),
}

// Category API
export const categoryApi = {
  list: () => api.get('/categories'),
  create: (data: { name: string; color: string }) => api.post('/categories', data),
  update: (id: number, data: { name?: string; color?: string }) => api.put(`/categories/${id}`, data),
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
}

// Launch API
export const launchApi = {
  load: (modelId: number) => api.post(`/launch/load?model_id=${modelId}`),
  start: () => api.post('/launch/start'),
  stop: () => api.post('/launch/stop'),
  status: () => api.get('/launch/status'),
}
