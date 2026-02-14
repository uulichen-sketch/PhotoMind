<template>
  <div class="home">
    <div class="page-header">
      <div>
        <h1 class="page-title">我的照片</h1>
        <p class="page-subtitle">共 {{ photos.length }} 张照片</p>
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
        @click="openViewer(index)"
      >
        <img :src="getPhotoUrl(photo)" :alt="photo.description" loading="lazy" />
        <!-- 评分徽章 -->
        <div v-if="photo.scores?.overall" class="score-badge" :style="getScoreStyle(photo.scores.overall)">
          {{ photo.scores.overall.toFixed(1) }}
        </div>
        <div class="photo-info">
          <p class="photo-desc">{{ photo.description || photo.filename }}</p>
          <div class="photo-tags">
            <el-tag v-for="tag in (photo.tags || []).slice(0, 3)" :key="tag" size="small">
              {{ tag }}
            </el-tag>
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
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import ImageViewer from '../components/ImageViewer.vue'

const router = useRouter()
const photos = ref([])
const viewerVisible = ref(false)
const viewerIndex = ref(0)

const API_BASE = 'http://localhost:8000'

const getPhotoUrl = (photo) => {
  return `${API_BASE}/api/photo/${photo.id}/thumbnail`
}

const getPhotoFileUrl = (photo) => {
  return `${API_BASE}/api/photo/${photo.id}/file`
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
    const res = await axios.get(`${API_BASE}/api/photos`)
    photos.value = res.data.photos || []
  } catch (e) {
    console.error('加载照片失败', e)
  }
}

onMounted(() => {
  // loadPhotos() // 暂时注释，等后端接口完善
})
</script>

<style scoped>
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
</style>
