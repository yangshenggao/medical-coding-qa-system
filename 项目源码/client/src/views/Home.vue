<template>
  <div class="home-container">
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" data-tone="Users" @click="goToStat('users')">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">用户总数</span>
              <span class="stat-value">{{ stats.user_count }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#409eff"><User /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" data-tone="Libraries">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">知识库数量</span>
              <span class="stat-value">{{ stats.kb_count }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#67c23a"><FolderOpened /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" data-tone="Documents">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">文档总数</span>
              <span class="stat-value">{{ stats.doc_count }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#e6a23c"><Document /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card clickable" data-tone="Sessions" @click="goToStat('todayChats')">
          <div class="stat-content">
            <div class="stat-info">
              <span class="stat-label">今日提问</span>
              <span class="stat-value">{{ stats.today_chat_count }}</span>
            </div>
            <el-icon class="stat-icon" :size="48" color="#f56c6c"><ChatDotRound /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">近7天提问趋势</span>
          </template>
          <div ref="trendChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">知识库文档占比</span>
          </template>
          <div ref="pieChartRef" class="chart-box"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { getOverview } from '../api/stats'

const router = useRouter()
const stats = reactive({
  user_count: 0,
  kb_count: 0,
  doc_count: 0,
  today_chat_count: 0,
  trend_data: [],
  kb_doc_data: []
})

const trendChartRef = ref(null)
const pieChartRef = ref(null)
let trendChart = null
let pieChart = null
let echartsLib = null

async function ensureEcharts() {
  if (!echartsLib) {
    echartsLib = await import('echarts')
  }
  return echartsLib
}

async function loadStats() {
  try {
    const res = await getOverview()
    Object.assign(stats, res.data)
    await renderTrendChart()
    await renderPieChart()
  } catch (err) {
    // 错误已在拦截器中处理
  }
}

async function renderTrendChart() {
  if (!trendChartRef.value) return
  const echarts = await ensureEcharts()
  trendChart?.dispose()
  trendChart = echarts.init(trendChartRef.value)

  const dates = stats.trend_data.map(item => item.date)
  const counts = stats.trend_data.map(item => item.count)

  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [{
      name: '提问次数',
      type: 'line',
      smooth: true,
      data: counts,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
          { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
        ])
      },
      lineStyle: { color: '#409eff', width: 2 },
      itemStyle: { color: '#409eff' }
    }]
  })
}

async function renderPieChart() {
  if (!pieChartRef.value) return
  const echarts = await ensureEcharts()
  pieChart?.dispose()
  pieChart = echarts.init(pieChartRef.value)

  const data = stats.kb_doc_data.length > 0
    ? stats.kb_doc_data
    : [{ name: '暂无数据', value: 1 }]

  pieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '2%',
      top: 'middle',
      width: '32%'
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['28%', '50%'],
      avoidLabelOverlap: false,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' }
      },
      data
    }]
  })
}

function handleResize() {
  trendChart?.resize()
  pieChart?.resize()
}

function goToStat(type) {
  if (type === 'users') {
    router.push('/user-manage')
    return
  }
  if (type === 'knowledge') {
    router.push('/knowledge-base')
    return
  }
  if (type === 'documents') {
    router.push('/document')
    return
  }
  if (type === 'todayChats') {
    router.push({ path: '/chat-history', query: { today: '1' } })
  }
}

onMounted(() => {
  loadStats()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  pieChart?.dispose()
})
</script>

<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stat-card {
  border-radius: 24px;
  position: relative;
  overflow: hidden;
}

.stat-card::after {
  content: attr(data-tone);
  position: absolute;
  right: 20px;
  top: 16px;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(83, 101, 95, 0.42);
}

.clickable {
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.clickable:hover {
  transform: translateY(-4px);
}

.stat-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 132px;
  padding: 4px 2px 2px;
}

.stat-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 70%;
}

.stat-label {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--med-ink-soft);
}

.stat-value {
  font-size: 40px;
  line-height: 1;
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  font-weight: 700;
  color: var(--med-ink);
}

.stat-icon {
  opacity: 0.88;
  padding: 16px;
  border-radius: 22px;
  background: rgba(255, 249, 240, 0.74);
  box-shadow: inset 0 0 0 1px rgba(64, 84, 77, 0.08);
}

.card-title {
  font-weight: 600;
  font-size: 18px;
  font-family: 'Iowan Old Style', 'Palatino Linotype', 'Noto Serif SC', serif;
  color: var(--med-ink);
}

.chart-box {
  width: 100%;
  height: 320px;
}

.stat-cards :deep(.el-card__body) {
  padding: 22px 22px 18px;
}

.chart-row :deep(.el-card__header) {
  padding: 20px 22px 12px;
  border-bottom: 1px solid rgba(64, 84, 77, 0.08);
  background: rgba(255, 248, 238, 0.5);
}

.chart-row :deep(.el-card__body) {
  padding: 10px 14px 18px;
}
</style>
