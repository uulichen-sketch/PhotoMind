<template>
  <div class="detail-page">
    <el-button @click="$router.back()" size="large" style="margin-bottom: 20px;">
      ← 返回
    </el-button>

    <el-card v-if="photo" class="detail-card">
      <el-row :gutter="20">
        <!-- 照片展示 -->
        <el-col :span="14">
          <img :src="photoUrl" class="detail-image" :alt="photo.description" />
        </el-col>

        <!-- 详细信息 -->
        <el-col :span="10">
          <h2>{{ photo.filename }}</h2>

          <el-divider />

          <!-- AI 描述 -->
          <div class="info-section">
            <h3>📝 AI 描述</h3>
            <p>{{ photo.description || '暂无描述' }}</p>
          </div>

          <!-- 标签 -->
          <div class="info-section">
            <h3>🏷️ 标签</h3>
            <div class="tags-container">
              <el-tag v-for="tag in (photo.tags || [])" :key="tag" size="large">
                {{ tag }}
              </el-tag>
              <span v-if="!photo.tags?.length">暂无标签</span>
            </div>
          </div>

          <el-divider />

          <!-- EXIF 信息 -->
          <div class="info-section">
            <h3>📷 拍摄信息</h3>
            <div class="info-item">
              <span class="info-label">拍摄时间:</span>
              <span>{{ formatDate(photo.datetime) || '未知' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">拍摄地点:</span>
              <span>{{ photo.location || '未知' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">相机:</span>
              <span>{{ photo.camera || '未知' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">镜头:</span>
              <span>{{ photo.lens || '未知' }}</span>
            </div>
          </div>

          <el-divider />

          <!-- 拍摄参数 -->
          <div class="info-section">
            <h3>⚙️ 拍摄参数</h3>
            <el-row :gutter="10">
              <el-col :span="12">
                <div class="param-item">
                  <span class="param-label">ISO</span>
                  <span class="param-value">{{ photo.iso || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="param-item">
                  <span class="param-label">光圈</span>
                  <span class="param-value">{{ photo.aperture || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="param-item">
                  <span class="param-label">快门</span>
                  <span class="param-value">{{ photo.shutter || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="param-item">
                  <span class="param-label">焦距</span>
                  <span class="param-value">{{ photo.focal_length || '-' }}</span>
                </div>
              </el-col>
            </el-row>
          </div>

          <el-divider />

          <!-- 文件信息 -->
          <div class="info-section">
            <h3>📁 文件信息</h3>
            <div class="info-item">
              <span class="info-label">文件大小:</span>
              <span>{{ formatSize(photo.file_size) }}</span>
            </div>
            <div v-if="photo.width && photo.height" class="info-item">
              <span class="info-label">分辨率:</span>
              <span>{{ photo.width }} × {{ photo.height }}</span>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-empty v-else description="照片不存在" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const route = useRoute()
const API_BASE = 'http://localhost:8000'

const photo = ref(null)
const loading = ref(true)

const photoId = computed(() => route.params.id)
const photoUrl = computed(() => `${API_BASE}/api/photo/${photoId.value}/file`)

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
    const res = await axios.get(`${API_BASE}/api/photo/${photoId.value}`)
    photo.value = res.data
  } catch (e) {
    ElMessage.error('加载照片失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadPhoto()
})
</script>

<style scoped>
.detail-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.detail-card {
  background: white;
}

.detail-image {
  width: 100%;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.info-section {
  margin-bottom: 16px;
}

.info-section h3 {
  font-size: 18px;
  color: #303133;
  margin-bottom: 12px;
}

.info-item {
  margin-bottom: 8px;
  font-size: 16px;
}

.info-label {
  color: #909399;
  margin-right: 8px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.param-item {
  text-align: center;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 8px;
}

.param-label {
  display: block;
  font-size: 14px;
  color: #909399;
}

.param-value {
  display: block;
  font-size: 20px;
  font-weight: bold;
  color: #303133;
  margin-top: 4px;
}
</style>
