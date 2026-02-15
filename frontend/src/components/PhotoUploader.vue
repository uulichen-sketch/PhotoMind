<template>
  <div class="photo-uploader">
    <!-- 上传区域 -->
    <div 
      v-if="!uploading"
      class="upload-zone"
      :class="{ dragover: isDragover }"
      @click="selectFiles"
      @dragover.prevent="isDragover = true"
      @dragleave="isDragover = false"
      @drop.prevent="handleDrop"
    >
      <div class="upload-icon">📁</div>
      <div class="upload-text">点击选择照片或拖拽到此处</div>
      <div class="upload-hint">支持 JPG、PNG、GIF 等格式</div>
    </div>
    
    <!-- 隐藏的文件输入 -->
    <input 
      ref="fileInput"
      type="file" 
      multiple
      accept="image/*"
      style="display: none"
      @change="handleFileSelect"
    />
    
    <!-- 上传进度 -->
    <div v-if="uploading" class="upload-progress">
      <div class="progress-header">
        <h3>正在上传 {{ selectedFiles.length }} 张照片</h3>
        <p class="progress-stats">
          已完成 {{ uploadedCount }} / {{ selectedFiles.length }}
        </p>
      </div>
      
      <el-progress 
        :percentage="uploadProgress" 
        :stroke-width="12"
        :status="uploadProgress === 100 ? 'success' : null"
      />
      
      <div class="progress-details">
        <div v-if="currentFile" class="current-file">
          正在上传: {{ currentFile }}
        </div>
        <div v-if="uploadProgress === 100" class="upload-complete">
          <span class="success-icon">✅</span>
          上传完成！照片正在后台进行 AI 分析...
        </div>
      </div>
      
      <!-- 上传完成后的操作 -->
      <div v-if="uploadProgress === 100" class="upload-actions">
        <el-button type="primary" @click="goToHome">
          去首页查看
        </el-button>
        <el-button @click="resetUpload">
          继续上传
        </el-button>
      </div>
    </div>
    
    <!-- 已选文件列表（上传前显示） -->
    <div v-if="selectedFiles.length > 0 && !uploading" class="selected-files">
      <div class="files-header">
        <span>已选择 {{ selectedFiles.length }} 个文件</span>
        <el-button type="primary" text @click="clearFiles">清空</el-button>
      </div>
      
      <div class="file-list">
        <div 
          v-for="(file, index) in selectedFiles.slice(0, 10)" 
          :key="index"
          class="file-item"
        >
          <span class="file-icon">🖼️</span>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatSize(file.size) }}</span>
        </div>
        <div v-if="selectedFiles.length > 10" class="file-more">
          还有 {{ selectedFiles.length - 10 }} 个文件...
        </div>
      </div>
      
      <div class="file-actions">
        <el-button size="large" @click="clearFiles">重新选择</el-button>
        <el-button type="primary" size="large" @click="startUpload">
          开始上传
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const API_BASE = 'http://localhost:8000'

const fileInput = ref(null)
const isDragover = ref(false)
const selectedFiles = ref([])
const uploading = ref(false)
const uploadedCount = ref(0)
const currentFile = ref('')

const uploadProgress = computed(() => {
  if (selectedFiles.value.length === 0) return 0
  return Math.round((uploadedCount.value / selectedFiles.value.length) * 100)
})

const selectFiles = () => {
  fileInput.value?.click()
}

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files)
  filterImageFiles(files)
}

const handleDrop = (e) => {
  isDragover.value = false
  const files = Array.from(e.dataTransfer.files)
  filterImageFiles(files)
}

const filterImageFiles = (files) => {
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff']
  selectedFiles.value = files.filter(file => {
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    return imageExtensions.includes(ext)
  })
  
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('未找到图片文件')
  } else {
    ElMessage.success(`已选择 ${selectedFiles.value.length} 张图片`)
  }
}

const clearFiles = () => {
  selectedFiles.value = []
  uploadedCount.value = 0
  currentFile.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const resetUpload = () => {
  uploading.value = false
  clearFiles()
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const startUpload = async () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  uploadedCount.value = 0

  try {
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('files', file)
      currentFile.value = file.name
    })

    // 一次性上传所有文件
    const res = await axios.post(`${API_BASE}/api/photos/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        // 计算整体上传进度
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100)
          uploadedCount.value = Math.round((percent / 100) * selectedFiles.value.length)
        }
      }
    })
    
    uploadedCount.value = selectedFiles.value.length
    currentFile.value = ''
    
    const data = res.data
    ElMessage.success(`成功上传 ${data.uploaded} 张照片，AI 分析将在后台进行`)
    
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
    uploading.value = false
  }
}

const goToHome = () => {
  router.push('/')
}
</script>

<style scoped>
.photo-uploader {
  max-width: 600px;
  margin: 0 auto;
}

.upload-zone {
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-lg);
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: var(--transition);
  background: var(--bg-color);
}

.upload-zone:hover,
.upload-zone.dragover {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.02);
}

.upload-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.upload-text {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 14px;
  color: var(--text-muted);
}

/* 上传进度 */
.upload-progress {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 32px;
  box-shadow: var(--shadow);
}

.progress-header {
  text-align: center;
  margin-bottom: 24px;
}

.progress-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.progress-stats {
  color: var(--text-secondary);
  font-size: 14px;
}

.progress-details {
  margin-top: 20px;
  text-align: center;
}

.current-file {
  font-size: 14px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.upload-complete {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 8px;
  color: #10b981;
  font-weight: 500;
}

.success-icon {
  font-size: 20px;
}

.upload-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}

/* 已选文件 */
.selected-files {
  margin-top: 24px;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow);
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.file-list {
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 20px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--bg-color);
  margin-bottom: 8px;
}

.file-icon {
  font-size: 20px;
}

.file-name {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: var(--text-muted);
}

.file-more {
  text-align: center;
  padding: 8px;
  color: var(--text-muted);
  font-size: 14px;
}

.file-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
