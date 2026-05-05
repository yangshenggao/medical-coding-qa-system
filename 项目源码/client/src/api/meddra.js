import axios from './index'

export const meddraApi = {
  search(params) {
    const normalized = { ...params }
    if (normalized.pageSize !== undefined && normalized.page_size === undefined) {
      normalized.page_size = normalized.pageSize
      delete normalized.pageSize
    }
    return axios.get('/meddra/search', { params: normalized })
  },
  semanticSearch(data) {
    return axios.post('/meddra/semantic_search', data)
  },
  hierarchy(params) {
    return axios.get('/meddra/hierarchy', { params })
  },
  browse(params) {
    return axios.get('/meddra/browse', { params })
  },
  stats() {
    return axios.get('/meddra/stats')
  }
}
