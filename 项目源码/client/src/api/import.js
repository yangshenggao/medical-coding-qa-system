import axios from './index'

export const importApi = {
  importWhodrug(data) {
    return axios.post('/import/whodrug', data, {
      timeout: 3600000
    })
  },
  importMeddra(data) {
    return axios.post('/import/meddra', data, {
      timeout: 3600000
    })
  },
  importSmq(data) {
    return axios.post('/import/meddra_smq', data, {
      timeout: 3600000
    })
  },
  importMeddraDocs(data) {
    return axios.post('/import/meddra_docs', data, {
      timeout: 3600000
    })
  },
  getLogs(params) {
    return axios.get('/import/logs', { params })
  },
  getStatus() {
    return axios.get('/import/status')
  }
}
