<template>
  <div class="detail-page">
    <el-button class="back-btn" text @click="$router.back()">
      <span class="back-icon">←</span>
      返回
    </el-button>

    <div v-if="photo" class="detail-content">
      <!-- 照片展示区 -->
      <div class="photo-section">
        <div class="photo-container" @click="viewerVisible = true">
          <img :src="photoUrl" class="main-photo" :alt="photo.description" />
          <div class="photo-overlay">
            <span class="zoom-icon">🔍</span>
            <span>点击查看大图</span>
          </div>
        </div>
        
        <!-- 照片操作 -->
        <div class="photo-actions">
          <el-button size="large" @click="downloadPhoto">
            <span class="action-icon">⬇️</span>
            下载原图
          </el-button>
          <el-button size="large" type="danger" plain @click="deletePhoto">
            <span class="action-icon">🗑️</span>
            删除
          </el-button>
        </div>
      </div>

      <!-- 信息侧边栏 -->
      <div class="info-section">
        <el-card class="info-card">
          <!-- AI 评分 -->
          <div v-if="photo.scores" class="info-block">
            <PhotoScore :scores="photo.scores" />
          </div>

          <el-divider v-if="photo.scores" />

          <!-- AI 描述 -->
          <div class="info-block">
            <div class="block-header">
              <div class="block-icon ai-icon">🤖</div>
              <h3>AI 描述</h3>
            </div>
            <p class="ai-description">{{ photo.description || '暂无描述' }}</p>
          </div>

          <el-divider />

          <!-- 标签 -->
          <div class="info-block">
            <div class="block-header">
              <div class="block-icon tag-icon">🏷️</div>
              <h3>标签</h3>
            </div>
            <div class="tags-list">
              <el-tag 
                v-for="tag in (photo.tags || [])" 
                :key="tag"
                class="photo-tag"
                effect="dark"
                round
              >
                {{ tag }}
              </el-tag>
              <span v-if="!photo.tags?.length" class="no-data">暂无标签</span>
            </div>
          </div>

          <el-divider />

          <!-- 拍摄参数 -->
          <div class="info-block">
            <div class="block-header">
              <div class="block-icon camera-icon">📷</div>
              <h3>拍摄参数</h3>
            </div>
            <div class="params-grid">
              <div class="param-item">
                <span class="param-icon">📐</span>
                <span class="param-label">ISO</span>
                <span class="param-value">{{ photo.iso || '-' }}</span>
              </div>
              <div class="param-item">
                <span class="param-icon">🔍</span>
                <span class="param-label">光圈</span>
                <span class="param-value">{{ photo.aperture || '-' }}</span>
              </div>
              <div class="param-item">
                <span class="param-icon">⏱️</span>
                <span class="param-label">快门</span>
                <span class="param-value">{{ photo.shutter || '-' }}</span>
              </div>
              <div class="param-item">
                <span class="param-icon">📏</span>
                <span class="param-label">焦距</span>
                <span class="param-value">{{ photo.focal_length || '-' }}</span>
              </div>
            </div>
          </div>

          <el-divider />

          <!-- 元数据信息 -->
          <div class="info-block">
            <div class="block-header">
              <div class="block-icon meta-icon">📋</div>
              <h3>详细信息</h3>
            </div>
            <div class="meta-list">
              <div class="meta-item">
                <span class="meta-label">文件名</span>
                <span class="meta-value" :title="photo.filename">{{ photo.filename }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">拍摄时间</span>
                <span class="meta-value">{{ formatDate(photo.datetime) || '未知' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">拍摄地点</span>
                <span class="meta-value">{{ photo.location || '未知' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">相机</span>
                <span class="meta-value">{{ photo.camera || '未知' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">镜头</span>
                <span class="meta-value">{{ photo.lens || '未知' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">文件大小</span>
                <span class="meta-value">{{ formatSize(photo.file_size) }}</span>
              </div>
              <div v-if="photo.width && photo.height" class="meta-item">
                <span class="meta-label">分辨率</span>
                <span class="meta-value">{{ photo.width }} × {{ photo.height }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <el-empty v-else description="照片不存在" :image-size="200" />

    <!-- 图片浏览器 -->
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
const loading = ref(true)
const viewerVisible = ref(false)

const photoId = computed(() => route.params.id)
const photoUrl = computed(() => `${API_BASE}/api/photos/${photoId.value}/file`)

// 图片浏览器数据
const viewerImages = computed(() => {
  if (!photo.value) return []
  return [{
    src: photoUrl.value,
    thumbnail: photoUrl.value,
    filename: photo.value.filename,
    description: photo.value.description,
    datetime: photo.value.datetime,
    location: photo.value.location,
    camera: photo.value.camera
  }]
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
  if (!bytes) return '未知'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const loadPhoto = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/photos/${photoId.value}`)
    photo.value = res.data
  } catch (e) {
    ElMessage.error('加载照片失败')
  } finally {
    loading.value = false
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
  max-width: 1400px;
  margin: 0 auto;
}

.back-btn {
  margin-bottom: 24px;
  font-size: 16px;
  padding: 8px 16px;
}

.back-icon {
  margin-right: 4px;
}

.detail-content {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 32px;
}

/* 照片区域 */
.photo-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.photo-container {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  position: relative;
  cursor: zoom-in;
  overflow: hidden;
}

.photo-container:hover .photo-overlay {
  opacity: 1;
}

.photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: white;
  font-size: 16px;
  opacity: 0;
  transition: opacity 0.3s ease;
  border-radius: var(--radius-lg);
}

.zoom-icon {
  font-size: 48px;
}

.main-photo {
  max-width: 100%;
  max-height: 70vh;
  border-radius: var(--radius);
  object-fit: contain;
}

.photo-actions {
  display: flex;
  gap: 12px;
}

.action-icon {
  margin-right: 6px;
}

/* 信息区域 */
.info-section {
  position: sticky;
  top: 20px;
  align-self: flex-start;
}

.info-card {
  border-radius: var(--radius-lg) !important;
}

.info-block {
  padding: 4px 0;
}

.block-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.block-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.ai-icon {
  background: linear-gradient(135deg, #8b5cf6, #a78bfa);
}

.tag-icon {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
}

.camera-icon {
  background: linear-gradient(135deg, #06b6d4, #22d3ee);
}

.meta-icon {
  background: linear-gradient(135deg, #10b981, #34d399);
}

.block-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

/* AI 描述 */
.ai-description {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-secondary);
  padding: 16px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.05), rgba(167, 139, 250, 0.05));
  border-radius: 10px;
  border-left: 3px solid #8b5cf6;
}

/* 标签 */
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.photo-tag {
  font-size: 13px !important;
  padding: 6px 14px !important;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark)) !important;
  border: none !important;
}

.no-data {
  color: var(--text-muted);
  font-size: 14px;
}

/* 参数网格 */
.params-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.param-item {
  background: var(--bg-color);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  transition: var(--transition);
}

.param-item:hover {
  background: linear-gradient(135deg, rgba(6, 182, 212, 0.1), rgba(34, 211, 238, 0.1));
  transform: translateY(-2px);
}

.param-icon {
  font-size: 20px;
  display: block;
  margin-bottom: 4px;
}

.param-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
}

.param-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--primary-color);
  display: block;
  margin-top: 2px;
}

/* 元数据列表 */
.meta-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.meta-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px dashed var(--border-color);
}

.meta-item:last-child {
  border-bottom: none;
}

.meta-label {
  font-size: 14px;
  color: var(--text-muted);
}

.meta-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
  max-width: 60%;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 响应式 */
@media (max-width: 1024px) {
  .detail-content {
    grid-template-columns: 1fr;
  }
  
  .info-section {
    position: static;
  }
  
  .photo-container {
    min-height: auto;
  }
}

@media (max-width: 768px) {
  .photo-actions {
    flex-direction: column;
  }
  
  .photo-actions .el-button {
    width: 100%;
  }
  
  .params-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
