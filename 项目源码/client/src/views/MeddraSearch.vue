<template>
  <div class="page-container meddra-page">
    <section class="page-hero">
      <div>
        <div class="hero-kicker">Term Discovery Console</div>
        <h1>MedDRA 搜索</h1>
        <p>
          将标准术语检索与语义候选推荐放在同一工作台里，适合先筛选候选，再结合层级与规则做医学编码判断。
        </p>
      </div>
      <div class="hero-chip">CN / EN</div>
    </section>

    <el-card class="search-card">
      <template #header>
        <div class="card-header">
          <div>
            <div class="section-title">检索模式</div>
            <div class="section-subtitle">关键词定位或语义候选推荐</div>
          </div>
          <el-radio-group v-model="searchType" size="small" @change="handleTypeChange">
            <el-radio-button value="semantic">语义搜索</el-radio-button>
            <el-radio-button value="keyword">关键词搜索</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="语言">
          <el-select v-model="language" style="width: 110px">
            <el-option value="cn" label="中文" />
            <el-option value="en" label="英文" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索词">
          <el-input
            v-model="searchForm.term"
            :placeholder="searchType === 'semantic' ? '输入症状描述，如：肺泡散在条索影' : '输入术语名称或代码'"
            clearable
            style="width: 360px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="层级" v-if="searchType === 'keyword'">
          <el-select v-model="searchForm.level" clearable style="width: 110px">
            <el-option value="SOC" label="SOC" />
            <el-option value="HLGT" label="HLGT" />
            <el-option value="HLT" label="HLT" />
            <el-option value="PT" label="PT" />
            <el-option value="LLT" label="LLT" />
          </el-select>
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
          <div class="section-title">检索结果</div>
          <div class="section-subtitle">共 {{ total }} 条结果</div>
        </div>
      </template>

      <template v-if="searchType === 'semantic'">
        <el-alert
          title="语义搜索结果用于术语候选推荐"
          type="warning"
          :closable="false"
          show-icon
          class="semantic-alert"
        >
          <template #default>
            系统会根据描述相似度推荐候选 MedDRA 术语。像“肺泡散在条索影”这类影像或口语描述，仍需结合病例上下文做人工复核。
          </template>
        </el-alert>

        <div v-if="topRecommendation" class="top-recommendation">
          <div class="recommendation-label">首选候选</div>
          <div class="recommendation-main">
            <div>
              <div class="recommendation-name">{{ topRecommendation.name }}</div>
              <div class="recommendation-meta">
                <span>编码 {{ topRecommendation.code }}</span>
                <span>层级 {{ topRecommendation.level || topRecommendation.term_level }}</span>
                <span v-if="topRecommendation.llt_code">LLT {{ topRecommendation.llt_code }}</span>
                <span v-if="topRecommendation.pt_code">PT {{ topRecommendation.pt_code }}</span>
                <span v-if="topRecommendation.hlt_code">HLT {{ topRecommendation.hlt_code }}</span>
              </div>
            </div>
            <div class="recommendation-score">
              <el-progress
                type="dashboard"
                :percentage="Math.round((topRecommendation.score || 0) * 100)"
                :stroke-width="12"
              />
            </div>
          </div>
          <div class="recommendation-note">{{ getSemanticHint(topRecommendation) }}</div>
        </div>

        <div class="candidate-grid">
          <div
            v-for="(item, index) in resultList"
            :key="`${item.code}-${index}`"
            class="candidate-card"
            :class="{ primary: index === 0 }"
          >
            <div class="candidate-header">
              <div class="candidate-name">{{ item.name }}</div>
              <el-tag :type="getLevelTagType(item.level || item.term_level)" size="small">
                {{ item.level || item.term_level }}
              </el-tag>
            </div>
            <div class="candidate-info">代码：{{ item.code }}</div>
            <div class="candidate-info">LLT：{{ formatHierarchy(item.llt_code, item.llt_name) }}</div>
            <div class="candidate-info">PT：{{ formatHierarchy(item.pt_code, item.pt_name) }}</div>
            <div class="candidate-info">HLT：{{ formatHierarchy(item.hlt_code, item.hlt_name) }}</div>
            <div class="candidate-info">推荐说明：{{ getSemanticHint(item) }}</div>
            <el-progress
              :percentage="Math.round((item.score || 0) * 100)"
              :stroke-width="8"
              :show-text="true"
            />
          </div>
        </div>
      </template>

      <el-table v-else :data="resultList" stripe style="width: 100%">
        <el-table-column prop="code" label="代码" width="120" />
        <el-table-column prop="name" label="术语名称" min-width="260" />
        <el-table-column prop="term_level" label="层级" width="90">
          <template #default="{ row }">
            <el-tag :type="getLevelTagType(row.level || row.term_level)" size="small">
              {{ row.level || row.term_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="LLT" min-width="220">
          <template #default="{ row }">
            {{ formatHierarchy(row.llt_code, row.llt_name) }}
          </template>
        </el-table-column>
        <el-table-column label="PT" min-width="220">
          <template #default="{ row }">
            {{ formatHierarchy(row.pt_code, row.pt_name) }}
          </template>
        </el-table-column>
        <el-table-column label="HLT" min-width="220">
          <template #default="{ row }">
            {{ formatHierarchy(row.hlt_code, row.hlt_name) }}
          </template>
        </el-table-column>
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

    <el-empty v-if="searched && resultList.length === 0" description="未找到匹配的术语" />
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { meddraApi } from '../api/meddra'

const searchType = ref('semantic')
const language = ref('cn')
const loading = ref(false)
const searched = ref(false)
const resultList = ref([])
const total = ref(0)

const searchForm = reactive({
  term: '',
  level: '',
  page: 1,
  pageSize: 20
})

const topRecommendation = computed(() => resultList.value[0] || null)

const getLevelTagType = (level) => {
  const typeMap = {
    SOC: 'danger',
    HLGT: 'warning',
    HLT: 'success',
    PT: 'primary',
    LLT: 'info'
  }
  return typeMap[level] || ''
}

const handleTypeChange = () => {
  handleReset()
}

const getSemanticHint = (item) => {
  const score = item?.score || 0
  if (score >= 0.85) return '与输入描述高度接近，可优先作为候选编码复核'
  if (score >= 0.7) return '与输入描述较为接近，建议结合病历上下文人工确认'
  return '相关性一般，建议作为补充候选术语参考'
}

const formatHierarchy = (code, name) => {
  if (code && name) return `${code} / ${name}`
  if (code) return code
  if (name) return name
  return '-'
}

const handleSearch = async () => {
  if (!searchForm.term) {
    ElMessage.warning('请输入搜索词')
    return
  }

  loading.value = true
  searched.value = true

  try {
    if (searchType.value === 'semantic') {
      const res = await meddraApi.semanticSearch({
        term: searchForm.term,
        language: language.value,
        top_k: searchForm.pageSize
      })
      resultList.value = res.data || []
      total.value = resultList.value.length
    } else {
      const res = await meddraApi.search({
        keyword: searchForm.term,
        language: language.value,
        level: searchForm.level,
        page: searchForm.page,
        pageSize: searchForm.pageSize
      })
      resultList.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (e) {
    ElMessage.error(e.message || '搜索失败')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.term = ''
  searchForm.level = ''
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
.meddra-page {
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

.semantic-alert {
  margin-bottom: 18px;
  border-radius: 14px;
}

.top-recommendation {
  margin-bottom: 20px;
  padding: 24px;
  border-radius: 22px;
  background:
    linear-gradient(145deg, rgba(255, 250, 242, 0.96), rgba(239, 230, 217, 0.92));
  border: 1px solid rgba(139, 61, 47, 0.14);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.52);
}

.recommendation-label {
  display: inline-block;
  margin-bottom: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--med-accent);
  color: #fffaf2;
  font-size: 12px;
  letter-spacing: 0.08em;
}

.recommendation-main {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
}

.recommendation-name {
  font-size: 28px;
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-weight: 700;
  color: var(--med-ink);
  margin-bottom: 10px;
}

.recommendation-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: var(--med-ink-soft);
  font-size: 14px;
}

.recommendation-score {
  width: 140px;
  flex-shrink: 0;
}

.recommendation-note {
  margin-top: 12px;
  color: var(--med-ink-soft);
  line-height: 1.6;
}

.candidate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 14px;
}

.candidate-card {
  padding: 18px;
  border: 1px solid rgba(64, 84, 77, 0.12);
  border-radius: 18px;
  background: rgba(255, 251, 245, 0.78);
  box-shadow: var(--med-shadow-soft);
}

.candidate-card.primary {
  border-color: rgba(139, 61, 47, 0.22);
  box-shadow: 0 18px 28px rgba(97, 66, 49, 0.08);
}

.candidate-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.candidate-name {
  font-size: 18px;
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  color: var(--med-ink);
}

.candidate-info {
  margin-bottom: 8px;
  color: var(--med-ink-soft);
  line-height: 1.6;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.meddra-page :deep(.el-card__header) {
  padding: 20px 22px 14px;
  border-bottom: 1px solid rgba(64, 84, 77, 0.08);
  background: rgba(255, 248, 238, 0.46);
}

.meddra-page :deep(.el-card__body) {
  padding: 18px 22px 22px;
}

.meddra-page :deep(.el-form-item__label) {
  color: var(--med-ink-soft);
  font-weight: 600;
}

@media (max-width: 760px) {
  .page-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .recommendation-main {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
