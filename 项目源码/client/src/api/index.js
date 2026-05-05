import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

function handleBusinessError(payload = {}, fallbackMessage = '请求失败') {
  const code = Number(payload.code || 500)
  const message = payload.message || fallbackMessage

  if (code === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    router.push('/login')
    ElMessage.error(message || '登录已过期')
    return Promise.reject(new Error(message))
  }

  ElMessage.error(message)
  return Promise.reject(new Error(message))
}

request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res.code === 200) {
      return res
    }
    return handleBusinessError(res)
  },
  (error) => {
    if (error.response?.data) {
      return handleBusinessError(error.response.data, error.message || '请求失败')
    }
    ElMessage.error(error.message || '网络异常')
    return Promise.reject(error)
  }
)

export default request
