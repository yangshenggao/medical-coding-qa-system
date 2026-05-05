<template>
  <div class="page-container whodrug-page">
    <section class="page-hero">
      <div>
        <div class="hero-kicker">Structured Drug Retrieval</div>
        <h1>WHODrug 查询</h1>
        <p>
          用药名称、活性成分、MPID 与 Drug Code 在同一检索面板内交叉核对，适合做候选药物记录初筛与人工复核前准备。
        </p>
      </div>
      <div class="hero-chip">WHODrug Global</div>
    </section>

    <el-card class="search-card">
      <template #header>
        <div class="card-header">
          <div>
            <div class="section-title">检索条件</div>
            <div class="section-subtitle">按语言版本选择候选药物记录</div>
          </div>
          <el-radio-group v-model="language" size="small">
            <el-radio-button value="cn">中文</el-radio-button>
            <el-radio-button value="en">英文</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="输入药品名称、活性成分、MPID等"
            clearable
            style="width: 340px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch" :loading="loading">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="result-card" v-if="resultList.length > 0">
      <template #header>
        <div>
          <div class="section-title">候选记录</div>
          <div class="section-subtitle">共 {{ total }} 条候选药物记录</div>
        </div>
      </template>

      <el-alert
        title="WHODrug 查询结果为候选药物记录"
        type="info"
        :closable="false"
        show-icon
        class="result-tip"
      >
        <template #default>
          建议结合原始用药名称、活性成分、国家和剂型一起复核 Drug Code / MPID。
        </template>
      </el-alert>

      <el-table :data="resultList" stripe style="width: 100%">
        <el-table-column prop="mpid" label="MPID" width="120" />
        <el-table-column prop="drug_code" label="Drug Code" width="120" />
        <el-table-column prop="drug_name" label="药品名称" min-width="220" />
        <el-table-column prop="atc_code" label="ATC" width="100" />
        <el-table-column prop="pt" label="PT" min-width="180" />
        <el-table-column prop="substance_name" label="活性成分" min-width="180" />
        <el-table-column prop="pharmaceutical_form" label="剂型" width="130" />
        <el-table-column prop="country" label="国家" width="100" />
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="searchForm.page"
          v-model:page-size="searchForm.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSearch"
          @current-change="handleSearch"
        />
      </div>
    </el-card>

    <el-empty v-if="searched && resultList.length === 0" description="未找到匹配的药品" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { whodrugApi } from '../api/whodrug'

const language = ref('cn')
const loading = ref(false)
const searched = ref(false)
const resultList = ref([])
const total = ref(0)

const searchForm = reactive({
  keyword: '',
  page: 1,
  pageSize: 20
})

const handleSearch = async () => {
  if (!searchForm.keyword.trim()) {
    ElMessage.warning('请输入药物名称、活性成分或编码后再搜索')
    searched.value = false
    resultList.value = []
    total.value = 0
    return
  }

  loading.value = true
  searched.value = true
  try {
    const res = await whodrugApi.search({
      keyword: searchForm.keyword,
      language: language.value,
      page: searchForm.page,
      pageSize: searchForm.pageSize
    })
    resultList.value = res.data.list || []
    total.value = res.data.total || 0
  } catch (e) {
    ElMessage.error(e.message || '查询失败')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.keyword = ''
  searchForm.page = 1
  resultList.value = []
  total.value = 0
  searched.value = false
}

onMounted(() => {
  // 页面初始不自动查询
})
</script>

<style scoped>
.whodrug-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 10px 4px 4px;
}

.hero-kicker {
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--med-accent);
  margin-bottom: 10px;
}

.page-hero h1 {
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-size: 34px;
  line-height: 1.05;
  color: var(--med-ink);
}

.page-hero p {
  max-width: 720px;
  margin-top: 12px;
  color: var(--med-ink-soft);
  line-height: 1.8;
}

.hero-chip {
  padding: 12px 16px;
  border-radius: 999px;
  border: 1px solid rgba(139, 61, 47, 0.16);
  background: rgba(255, 251, 245, 0.72);
  color: var(--med-accent);
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-size: 18px;
  color: var(--med-ink);
}

.section-subtitle {
  margin-top: 4px;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(83, 101, 95, 0.72);
}

.search-form {
  padding-top: 6px;
}

.result-tip {
  margin-bottom: 16px;
  border-radius: 14px;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.whodrug-page :deep(.el-card__header) {
  padding: 20px 22px 14px;
  border-bottom: 1px solid rgba(64, 84, 77, 0.08);
  background: rgba(255, 248, 238, 0.46);
}

.whodrug-page :deep(.el-card__body) {
  padding: 18px 22px 22px;
}

.whodrug-page :deep(.el-form-item__label) {
  color: var(--med-ink-soft);
  font-weight: 600;
}

@media (max-width: 760px) {
  .page-hero {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
