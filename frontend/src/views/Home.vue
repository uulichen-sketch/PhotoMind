<template>
  <div class="home">
    <!-- 后台处理进度条 -->
    <div v-if="processingStats.pending_total > 0" class="processing-banner">
      <div class="processing-content">
        <div class="processing-icon">🤖</div>
        <div class="processing-info">
          <h4>AI 正在分析照片</h4>
          <p>{{ processingStats.completed_total }} / {{ processingStats.total }} 张照片已完成</p>
        </div>
        <div class="processing-progress">
          <el-progress 
            :percentage="processingPercent" 
            :stroke-width="8"
            :show-text="false"
          />
        </div>
      </div>
    </div>

    <div class="page-header">
      <div>
        <h1 class="page-title">我的照片</h1>
        <p class="page-subtitle">
          共 {{ photos.length }} 张照片
          <span v-if="processingStats.pending_total > 0" class="processing-hint">
            ({{ processingStats.pending_total }} 张正在分析)
          </span>
        </p>
      </div>
      <el-button type="primary" size="large" @click="$router.push('/import')">
        <span class="btn-icon">+</span>
        导入照片
      </el-button>
    </div>

    <el-empty v-if="photos.length === 0" class="empty-state" :image-size="200">
      <template #description>
        <div class="empty-content">
          <p class="empty-title">还没有照片</p>
          <p class="empty-desc">导入您的第一张照片开始管理</p>
        </div>
      </template>
      <el-button type="primary" size="large" @click="$router.push('/import')">
        📥 导入照片
      </el-button>
    </el-empty>

    <div v-else class="photo-grid">
      <div 
        v-for="(photo, index) in photos" 
        :key="photo.id" 
        class="photo-card"
      >
        <div class="photo-image-wrapper" @click="openViewer(index)">
          <img :src="getPhotoUrl(photo)" :alt="photo.description" loading="lazy" />
          <!-- 评分徽章 -->
          <div v-if="photo.scores?.overall" class="score-badge" :style="getScoreStyle(photo.scores.overall)">
            {{ photo.scores.overall.toFixed(1) }}
          </div>
          <!-- 处理中标记 -->
          <div v-else-if="!photo.ai_processed && !photo.ai_error" class="processing-badge">
            <span class="spinner"></span>
          </div>
        </div>
        
        <div class="photo-info">
          <p class="photo-desc" @click="openViewer(index)">{{ photo.description || photo.filename }}</p>
          <div class="photo-meta">
            <div class="photo-tags" @click="openViewer(index)">
              <el-tag v-for="tag in (photo.tags || []).slice(0, 2)" :key="tag" size="small">
                {{ tag }}
              </el-tag>
              <el-tag v-if="!photo.tags?.length" size="small" type="info">处理中...</el-tag>
            </div>
            <el-button 
              type="danger" 
              text 
              size="small"
              class="delete-btn"
              @click.stop="deletePhoto(photo)"
            >
              🗑️
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片浏览器 -->
    <ImageViewer
      v-model:visible="viewerVisible"
      :images="viewerImages"
      :initial-index="viewerIndex"
      @change="(idx) => viewerIndex = idx"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import ImageViewer from '../components/ImageViewer.vue'

const router = useRouter()
const photos = ref([])
const viewerVisible = ref(false)
const viewerIndex = ref(0)

// 后台处理统计
const processingStats = ref({
  pending_total: 0,
  completed_total: 0,
  total: 0
})
let statsInterval = null

const API_BASE = 'http://localhost:8000'

const processingPercent = computed(() => {
  if (processingStats.value.total === 0) return 0
  return Math.round((processingStats.value.completed_total / processingStats.value.total) * 100)
})

const getPhotoUrl = (photo) => {
  return `${API_BASE}/api/photos/${photo.id}/thumbnail`
}

const getPhotoFileUrl = (photo) => {
  return `${API_BASE}/api/photos/${photo.id}/file`
}

const goToDetail = (id) => {
  router.push(`/photo/${id}`)
}

// 图片浏览器数据
const viewerImages = computed(() => {
  return photos.value.map(photo => ({
    src: getPhotoFileUrl(photo),
    thumbnail: getPhotoUrl(photo),
    filename: photo.filename,
    description: photo.description,
    datetime: photo.datetime,
    location: photo.location,
    camera: photo.camera,
    scores: photo.scores
  }))
})

const openViewer = (index) => {
  viewerIndex.value = index
  viewerVisible.value = true
}

const getScoreStyle = (score) => {
  let color = '#ef4444'
  if (score >= 4.5) color = '#10b981'
  else if (score >= 4.0) color = '#6366f1'
  else if (score >= 3.0) color = '#f59e0b'
  
  return {
    background: color
  }
}

const loadPhotos = async () => {
  try {
    // 获取所有照片（包括待处理的）
    const res = await axios.get(`${API_BASE}/api/photos?status=all`)
    photos.value = res.data || []
  } catch (e) {
    console.error('加载照片失败', e)
  }
}

// 删除照片
const deletePhoto = async (photo) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 "${photo.filename}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    await axios.delete(`${API_BASE}/api/photos/${photo.id}`)
    ElMessage.success('删除成功')
    
    // 从列表中移除
    photos.value = photos.value.filter(p => p.id !== photo.id)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
    }
  }
}

// 获取后台处理统计
const loadProcessingStats = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/photos/processing-stats`)
    processingStats.value = res.data
    
    // 如果还有未完成的，刷新照片列表
    if (res.data.pending_total > 0) {
      loadPhotos()
    }
  } catch (e) {
    console.error('加载处理统计失败', e)
  }
}

onMounted(() => {
  loadPhotos()
  loadProcessingStats()
  
  // 每 5 秒刷新一次处理状态
  statsInterval = setInterval(() => {
    loadProcessingStats()
  }, 5000)
})

onUnmounted(() => {
  if (statsInterval) {
    clearInterval(statsInterval)
  }
})
</script>

<style scoped>
/* 后台处理进度条 */
.processing-banner {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  margin-bottom: 24px;
}

.processing-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.processing-icon {
  font-size: 32px;
}

.processing-info {
  flex: 1;
}

.processing-info h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.processing-info p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.processing-progress {
  width: 200px;
}

.processing-hint {
  color: var(--primary-color);
  font-size: 14px;
  margin-left: 8px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.btn-icon {
  margin-right: 4px;
  font-size: 20px;
}

.empty-content {
  text-align: center;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-muted);
}

.empty-state :deep(.el-empty__image) {
  filter: grayscale(100%);
  opacity: 0.5;
}

/* 评分徽章 */
.score-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 2;
}

/* 处理中标记 */
.processing-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  z-index: 2;
}

.processing-badge .spinner {
  width: 20px;
  height: 20px;
  border: 2px solid white;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 照片卡片优化 */
.photo-image-wrapper {
  position: relative;
  cursor: pointer;
}

.photo-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.photo-tags {
  flex: 1;
  cursor: pointer;
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;
  padding: 4px 8px !important;
}

.photo-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.1) !important;
}
</style>
