<template>
  <div class="detail-page">
    <div class="detail-header">
      <el-button class="back-btn" text @click="$router.back()">
        <span class="back-icon">&lt;</span>
        返回
      </el-button>
      <div class="header-actions" v-if="photo">
        <el-button @click="downloadPhoto">下载原图</el-button>
        <el-button type="danger" plain @click="deletePhoto">删除照片</el-button>
      </div>
    </div>

    <div v-if="photo" class="detail-content">
      <section class="photo-stage" @click="viewerVisible = true">
        <img :src="photoUrl" class="main-photo" :alt="photo.description || photo.filename" />
        <div class="stage-tip">点击查看大图</div>
      </section>

      <aside class="info-panel">
        <div v-if="photo.scores" class="panel-section">
          <h3>AI 评分</h3>
          <PhotoScore :scores="photo.scores" />
        </div>

        <div class="panel-section">
          <h3>照片描述</h3>
          <p class="description">{{ photo.description || '-' }}</p>
        </div>

        <div class="panel-section">
          <h3>标签</h3>
          <div class="tags">
            <el-tag v-for="tag in (photo.tags || [])" :key="tag" size="small">{{ tag }}</el-tag>
            <span v-if="!photo.tags?.length" class="empty">-</span>
          </div>
        </div>

        <div class="panel-section">
          <h3>EXIF 与位置信息</h3>
          <div class="exif-list">
            <div v-for="item in exifItems" :key="item.label" class="exif-item">
              <span class="exif-label">{{ item.label }}</span>
              <span class="exif-value" :title="item.value">{{ item.value }}</span>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <el-empty v-else description="照片不存在" :image-size="200" />

    <ImageViewer
      v-model:visible="viewerVisible"
      :images="viewerImages"
      :initial-index="0"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import ImageViewer from '../components/ImageViewer.vue'
import PhotoScore from '../components/PhotoScore.vue'

const route = useRoute()
const router = useRouter()
const API_BASE = 'http://localhost:8000'

const photo = ref(null)
const viewerVisible = ref(false)

const photoId = computed(() => route.params.id)
const photoUrl = computed(() => `${API_BASE}/api/photos/${photoId.value}/file`)

const viewerImages = computed(() => {
  if (!photo.value) return []
  return [{
    ...photo.value,
    src: photoUrl.value,
    thumbnail: photoUrl.value,
  }]
})

const exifItems = computed(() => {
  const p = photo.value || {}
  return [
    { label: '文件名', value: p.filename || '-' },
    { label: '拍摄时间', value: formatDate(p.datetime) || '-' },
    { label: '拍摄地点', value: p.location || '-' },
    { label: 'GPS', value: p.gps_latitude && p.gps_longitude ? `${p.gps_latitude}, ${p.gps_longitude}` : '-' },
    { label: '相机', value: p.camera || '-' },
    { label: '镜头', value: p.lens || '-' },
    { label: 'ISO', value: stringify(p.iso) },
    { label: '光圈', value: p.aperture || '-' },
    { label: '快门', value: p.shutter || '-' },
    { label: '焦距', value: p.focal_length || '-' },
    { label: '文件大小', value: formatSize(p.file_size) },
    { label: '分辨率', value: p.width && p.height ? `${p.width} x ${p.height}` : '-' },
    { label: '照片 ID', value: p.id || '-' },
  ]
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const stringify = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}

const loadPhoto = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/photos/${photoId.value}`)
    photo.value = res.data
  } catch (e) {
    ElMessage.error('加载照片失败')
  }
}

const downloadPhoto = () => {
  window.open(photoUrl.value, '_blank')
}

const deletePhoto = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这张照片吗？此操作不可恢复。',
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await axios.delete(`${API_BASE}/api/photos/${photoId.value}`)
    ElMessage.success('删除成功')
    router.push('/')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadPhoto()
})
</script>

<style scoped>
.detail-page {
  max-width: 1440px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}

.back-btn {
  font-size: 16px;
}

.back-icon {
  margin-right: 4px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.detail-content {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 18px;
  min-height: calc(100vh - 180px);
}

.photo-stage {
  position: relative;
  border-radius: 14px;
  background: #0f172a;
  border: 1px solid rgba(15, 23, 42, 0.16);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-in;
  min-height: 520px;
}

.main-photo {
  max-width: 100%;
  max-height: 80vh;
  object-fit: contain;
}

.stage-tip {
  position: absolute;
  right: 12px;
  bottom: 12px;
  padding: 6px 10px;
  font-size: 12px;
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.9);
  background: rgba(2, 6, 23, 0.66);
}

.info-panel {
  position: sticky;
  top: 18px;
  align-self: flex-start;
  max-height: calc(100vh - 140px);
  overflow: auto;
  border-radius: 14px;
  background: rgba(17, 24, 39, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 14px;
}

.panel-section {
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-section:last-child {
  padding-bottom: 0;
  margin-bottom: 0;
  border-bottom: none;
}

.panel-section h3 {
  margin: 0 0 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.95);
}

.description {
  margin: 0;
  line-height: 1.6;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.86);
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty {
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
}

.exif-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.exif-item {
  display: grid;
  grid-template-columns: 90px 1fr;
  gap: 8px;
  align-items: start;
}

.exif-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.58);
}

.exif-value {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.92);
  word-break: break-word;
}

@media (max-width: 1024px) {
  .detail-content {
    grid-template-columns: 1fr;
  }

  .photo-stage {
    min-height: 360px;
  }

  .info-panel {
    position: static;
    max-height: none;
  }
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions .el-button {
    flex: 1;
  }
}
</style>
