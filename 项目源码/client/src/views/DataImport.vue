<template>
  <div class="import-container">
    <el-card class="status-card">
      <template #header>
        <span>数据状态</span>
        <el-button text @click="loadStatus" style="float: right">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="4">
          <el-statistic title="WHODrug (英文)" :value="status.whodrug?.en || 0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="WHODrug (中文)" :value="status.whodrug?.cn || 0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="MedDRA (英文)" :value="status.meddra?.en || 0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="MedDRA (中文)" :value="status.meddra?.cn || 0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="SMQ (英文)" :value="status.smq?.en || 0" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="SMQ (中文)" :value="status.smq?.cn || 0" />
        </el-col>
      </el-row>
    </el-card>

    <el-card class="import-card">
      <template #header>
        <span>导入医学编码资源</span>
      </template>
      
      <el-alert
        title="导入说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #default>
          这里导入的是系统运行所需的核心医学编码词典资源，包括 WHODrug 和 MedDRA 的中英文版本。
        </template>
      </el-alert>

      <el-form label-width="120px">
        <el-divider>核心词典</el-divider>

        <el-form-item label="WHODrug (英文)">
          <el-button 
            type="primary" 
            @click="handleImport('whodrug', 'en')" 
            :loading="loading.whodrug_en"
            :disabled="status.whodrug?.en > 0"
          >
            {{ status.whodrug?.en > 0 ? '已导入' : '导入' }}
          </el-button>
          <span class="hint">从 WHODrug Global 2026 Mar 1 导入</span>
        </el-form-item>

        <el-form-item label="WHODrug (中文)">
          <el-button 
            type="primary" 
            @click="handleImport('whodrug', 'cn')" 
            :loading="loading.whodrug_cn"
            :disabled="status.whodrug?.cn > 0"
          >
            {{ status.whodrug?.cn > 0 ? '已导入' : '导入' }}
          </el-button>
          <span class="hint">从 WHODrug Global Chinese 2026 Mar 1 导入</span>
        </el-form-item>

        <el-form-item label="MedDRA (英文)">
          <el-button 
            type="primary" 
            @click="handleImport('meddra', 'en')" 
            :loading="loading.meddra_en"
            :disabled="status.meddra?.en > 0"
          >
            {{ status.meddra?.en > 0 ? '已导入' : '导入' }}
          </el-button>
          <span class="hint">从 English_29_0/MedAscii 导入</span>
        </el-form-item>

        <el-form-item label="MedDRA (中文)">
          <el-button 
            type="primary" 
            @click="handleImport('meddra', 'cn')" 
            :loading="loading.meddra_cn"
            :disabled="status.meddra?.cn > 0"
          >
            {{ status.meddra?.cn > 0 ? '已导入' : '导入' }}
          </el-button>
          <span class="hint">从 Chinese_29_0/ascii-290 导入</span>
        </el-form-item>

        <el-divider>SMQ 标准化查询</el-divider>

        <el-form-item label="SMQ (英文)">
          <el-button 
            type="primary" 
            @click="handleImport('smq', 'en')" 
            :loading="loading.smq_en"
            :disabled="status.smq?.en > 0"
          >
            {{ status.smq?.en > 0 ? '已导入' : '导入' }}
          </el-button>
          <span class="hint">从 smq_list.asc / smq_content.asc 导入</span>
        </el-form-item>

        <el-form-item label="SMQ (中文)">
          <el-button 
            type="primary" 
            @click="handleImport('smq', 'cn')" 
            :loading="loading.smq_cn"
            :disabled="status.smq?.cn > 0"
          >
            {{ status.smq?.cn > 0 ? '已导入' : '导入' }}
          </el-button>
          <span class="hint">从 smq_list.asc / smq_content.asc 导入</span>
        </el-form-item>

        <el-divider>MedDRA 规则文档（向量化）</el-divider>

        <el-form-item label="规则文档 (英文)">
          <el-button 
            type="success" 
            @click="handleImport('meddra_docs', 'en')" 
            :loading="loading.meddra_docs_en"
          >
            导入并向量化
          </el-button>
          <span class="hint">SMQ指南、入门指南、文件格式说明等 PDF 文档</span>
        </el-form-item>

        <el-form-item label="规则文档 (中文)">
          <el-button 
            type="success" 
            @click="handleImport('meddra_docs', 'cn')" 
            :loading="loading.meddra_docs_cn"
          >
            导入并向量化
          </el-button>
          <span class="hint">SMQ指南、入门指南、文件格式说明等 PDF 文档</span>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="logs-card">
      <template #header>
        <span>导入日志</span>
      </template>
      
      <el-table :data="logs" stripe>
        <el-table-column prop="dict_type" label="词典类型" width="150">
          <template #default="{ row }">
            {{ getDictTypeName(row.dict_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="file_name" label="文件名" min-width="150" />
        <el-table-column prop="record_count" label="记录数" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" min-width="150" />
        <el-table-column prop="create_time" label="导入时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { importApi } from '../api/import'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const status = ref({})
const logs = ref([])
const loading = reactive({
  whodrug_en: false,
  whodrug_cn: false,
  meddra_en: false,
  meddra_cn: false,
  smq_en: false,
  smq_cn: false,
  meddra_docs_en: false,
  meddra_docs_cn: false
})

const loadStatus = async () => {
  try {
    const res = await importApi.getStatus()
    status.value = res.data || {}
  } catch (e) {
    console.error(e)
  }
}

const loadLogs = async () => {
  try {
    const res = await importApi.getLogs({ page: 1, pageSize: 20 })
    logs.value = res.data.list || []
  } catch (e) {
    console.error(e)
  }
}

const getDictTypeName = (type) => {
  const map = {
    'whodrug_en': 'WHODrug 英文',
    'whodrug_cn': 'WHODrug 中文',
    'meddra_en': 'MedDRA 英文',
    'meddra_cn': 'MedDRA 中文',
    'smq_en': 'SMQ 英文',
    'smq_cn': 'SMQ 中文',
    'md_docs_en': 'MedDRA 说明文档英文',
    'md_docs_cn': 'MedDRA 说明文档中文'
  }
  return map[type] || type
}

const getStatusType = (status) => {
  const map = {
    'success': 'success',
    'failed': 'danger',
    'running': 'warning',
    'pending': 'info'
  }
  return map[status] || 'info'
}

const handleImport = async (dictType, language) => {
  const key = `${dictType}_${language}`
  loading[key] = true
  
  try {
    let res
    if (dictType === 'whodrug') {
      res = await importApi.importWhodrug({ language })
    } else if (dictType === 'smq') {
      res = await importApi.importSmq({ language })
    } else if (dictType === 'meddra_docs') {
      res = await importApi.importMeddraDocs({ language })
    } else {
      res = await importApi.importMeddra({ language })
    }

    ElMessage.success(res.message || '导入成功')
    await loadStatus()
    await loadLogs()
  } catch (e) {
    ElMessage.error(e.message || '导入失败')
  } finally {
    loading[key] = false
  }
}

onMounted(() => {
  loadStatus()
  loadLogs()
})
</script>

<style scoped>
.import-container {
  padding: 20px;
}

.status-card {
  margin-bottom: 20px;
}

.import-card {
  margin-bottom: 20px;
}

.hint {
  margin-left: 15px;
  color: #909399;
  font-size: 12px;
}
</style>
