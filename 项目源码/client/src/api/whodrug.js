import axios from './index'

export const whodrugApi = {
  search(params) {
    return axios.get('/whodrug/search', { params })
  },
  detail(mpid, params) {
    return axios.get(`/whodrug/detail/${mpid}`, { params })
  },
  stats() {
    return axios.get('/whodrug/stats')
  }
}