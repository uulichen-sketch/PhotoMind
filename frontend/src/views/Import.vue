<template>
  <div class="import-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">导入照片</h1>
        <p class="page-subtitle">选择文件夹导入您的照片</p>
      </div>
    </div>

    <el-card>
      <!-- 步骤指示器 -->
      <div class="steps">
        <div :class="['step', { active: step >= 1, completed: step > 1 }]">
          <div class="step-number">1</div>
          <div class="step-label">选择目录</div>
        </div>
        <div class="step-line"></div>
        <div :class="['step', { active: step >= 2, completed: step > 2 }]">
          <div class="step-number">2</div>
          <div class="step-label">确认导入</div>
        </div>
        <div class="step-line"></div>
        <div :class="['step', { active: step >= 3 }]">
          <div class="step-number">3</div>
          <div class="step-label">导入完成</div>
        </div>
      </div>

      <!-- 步骤 1: 选择目录 -->
      <div v-if="step === 1" class="step-content">
        <div 
          class="import-zone"
          :class="{ dragover: isDragover }"
          @click="selectDirectory"
          @dragover.prevent="isDragover = true"
          @dragleave="isDragover = false"
          @drop.prevent="handleDrop"
        >
          <div class="import-zone-icon">📁</div>
          <div class="import-zone-text">点击选择文件夹</div>
          <div class="import-zone-hint">或将文件夹拖拽到此处</div>
        </div>

        <!-- 隐藏的文件输入 -->
        <input 
          ref="fileInput"
          type="file" 
          webkitdirectory 
          directory
          multiple
          style="display: none"
          @change="handleFileSelect"
        />

        <!-- 已选择的文件列表 -->
        <div v-if="selectedFiles.length > 0" class="selected-files">
          <div class="files-header">
            <span class="files-title">📋 已选择 {{ selectedFiles.length }} 个文件</span>
            <el-button type="primary" text @click="clearFiles">清空</el-button>
          </div>
          <div class="file-list">
            <div 
              v-for="(file, index) in selectedFiles.slice(0, 10)" 
              :key="index"
              class="file-list-item"
            >
              <span class="file-list-icon">🖼️</span>
              <span class="file-list-name">{{ file.name }}</span>
              <span class="file-list-size">{{ formatSize(file.size) }}</span>
            </div>
            <div v-if="selectedFiles.length > 10" class="file-list-more">
              还有 {{ selectedFiles.length - 10 }} 个文件...
            </div>
          </div>
          <div class="files-actions">
            <el-button size="large" @click="clearFiles">重新选择</el-button>
            <el-button type="primary" size="large" @click="step = 2">
              下一步
              <span class="btn-arrow">→</span>
            </el-button>
          </div>
        </div>
      </div>

      <!-- 步骤 2: 确认导入 -->
      <div v-if="step === 2" class="step-content">
        <div class="confirm-panel">
          <div class="confirm-icon">📦</div>
          <h3>准备导入 {{ selectedFiles.length }} 张照片</h3>
          <p class="confirm-desc">
            系统将分析每张照片的 EXIF 信息、生成缩略图并使用 AI 进行场景识别。
            <br>此过程可能需要一些时间，请耐心等待。
          </p>
          <div class="confirm-actions">
            <el-button size="large" @click="step = 1">上一步</el-button>
            <el-button type="primary" size="large" :loading="uploading" @click="startUpload">
              开始导入
            </el-button>
          </div>
        </div>
      </div>

      <!-- 步骤 3: 导入进度 -->
      <div v-if="step === 3" class="step-content">
        <div class="progress-container">
          <div class="progress-header">
            <div class="progress-icon" :class="{ completed: isCompleted, failed: isFailed }">
              {{ progressIcon }}
            </div>
            <div class="progress-info">
              <h3>{{ progressTitle }}</h3>
              <p class="progress-desc">{{ progressDesc }}</p>
            </div>
          </div>
          
          <el-progress 
            :percentage="progressPercent" 
            :status="progressStatus"
            :stroke-width="12"
            :show-text="true"
          />
          
          <div v-if="currentFile" class="current-file">
            <span class="file-label">正在处理:</span>
            <span class="file-name">{{ currentFile }}</span>
          </div>

          <div v-if="isCompleted || isFailed" class="progress-actions">
            <el-button type="primary" size="large" @click="resetImport">
              导入更多照片
            </el-button>
            <el-button size="large" @click="$router.push('/')">查看照片</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 导入历史 -->
    <el-card v-if="importHistory.length > 0" class="history-card">
      <template #header>
        <div class="history-header">
          <span class="history-title">📚 导入历史</span>
        </div>
      </template>
      <el-table :data="importHistory" style="width: 100%">
        <el-table-column prop="task_id" label="任务ID" width="100">
          <template #default="{ row }">
            <code>{{ row.task_id.slice(0, 8) }}...</code>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="150">
          <template #default="{ row }">
            {{ row.processed }} / {{ row.total }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE = 'http://localhost:8000'

const fileInput = ref(null)
const step = ref(1)
const isDragover = ref(false)
const selectedFiles = ref([])
const uploading = ref(false)
const taskId = ref('')
const status = ref('')
const total = ref(0)
const processed = ref(0)
const failed = ref(0)
const currentFile = ref('')
const importHistory = ref([])

let pollTimer = null

const progressPercent = computed(() => {
  if (total.value === 0) return 0
  return Math.round((processed.value / total.value) * 100)
})

const progressStatus = computed(() => {
  if (status.value === 'completed') return 'success'
  if (status.value === 'failed') return 'exception'
  return null
})

const isCompleted = computed(() => status.value === 'completed')
const isFailed = computed(() => status.value === 'failed')

const progressIcon = computed(() => {
  if (isCompleted.value) return '✅'
  if (isFailed.value) return '❌'
  return '📤'
})

const progressTitle = computed(() => {
  if (isCompleted.value) return '导入完成！'
  if (isFailed.value) return '导入失败'
  return '正在导入...'
})

const progressDesc = computed(() => {
  if (isCompleted.value) return `成功导入 ${processed.value - failed.value} 张照片`
  if (isFailed.value) return '请检查网络连接后重试'
  return `已处理 ${processed.value} / ${total.value} 张`
})

// 选择目录
const selectDirectory = () => {
  fileInput.value?.click()
}

// 处理文件选择
const handleFileSelect = (e) => {
  const files = Array.from(e.target.files)
  filterImageFiles(files)
}

// 处理拖拽
const handleDrop = (e) => {
  isDragover.value = false
  const files = Array.from(e.dataTransfer.files)
  filterImageFiles(files)
}

// 过滤图片文件
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

// 清空选择
const clearFiles = () => {
  selectedFiles.value = []
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 格式化文件大小
const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// 开始上传
const startUpload = async () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  step.value = 3

  try {
    // 创建 FormData
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('files', file)
    })

    // 上传文件
    const res = await axios.post(`${API_BASE}/api/import/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    taskId.value = res.data.task_id
    status.value = res.data.status
    total.value = selectedFiles.value.length
    
    // 开始轮询状态
    pollTimer = setInterval(pollStatus, 1000)
    
    ElMessage.success('导入任务已启动')
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
    status.value = 'failed'
    uploading.value = false
  }
}

// 轮询状态
const pollStatus = async () => {
  if (!taskId.value) return
  
  try {
    const res = await axios.get(`${API_BASE}/api/import/status/${taskId.value}`)
    const data = res.data
    
    status.value = data.status
    total.value = data.total
    processed.value = data.processed
    failed.value = data.failed
    currentFile.value = data.current_file || ''
    
    if (data.status === 'completed' || data.status === 'failed') {
      clearInterval(pollTimer)
      pollTimer = null
      uploading.value = false
      
      importHistory.value.unshift({
        ...data,
        created_at: new Date().toISOString()
      })
    }
  } catch (e) {
    console.error('获取状态失败', e)
  }
}

// 重置导入
const resetImport = () => {
  step.value = 1
  selectedFiles.value = []
  taskId.value = ''
  status.value = ''
  total.value = 0
  processed.value = 0
  failed.value = 0
  currentFile.value = ''
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 状态标签
const getStatusType = (status) => {
  const map = {
    'pending': 'info',
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    'pending': '等待中',
    'processing': '处理中',
    'completed': '完成',
    'failed': '失败'
  }
  return map[status] || status
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
  }
})
</script>

<style scoped>
.import-page {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

/* 步骤指示器 */
.steps {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  padding: 20px 0;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-color);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  transition: var(--transition);
}

.step.active .step-number {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  color: white;
  box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39);
}

.step.completed .step-number {
  background: #10b981;
  color: white;
}

.step-label {
  font-size: 14px;
  color: var(--text-muted);
  font-weight: 500;
}

.step.active .step-label {
  color: var(--primary-color);
}

.step-line {
  width: 60px;
  height: 2px;
  background: var(--border-color);
  margin: 0 16px;
  margin-bottom: 24px;
}

/* 导入区域 */
.step-content {
  padding: 0 20px 20px;
}

.import-zone {
  margin-bottom: 24px;
}

.selected-files {
  background: var(--bg-color);
  border-radius: var(--radius);
  padding: 20px;
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.files-title {
  font-weight: 600;
  color: var(--text-primary);
}

.file-list {
  max-height: 250px;
  overflow-y: auto;
  background: var(--card-bg);
  border-radius: 10px;
  padding: 8px;
  margin-bottom: 20px;
}

.file-list-more {
  text-align: center;
  padding: 12px;
  color: var(--text-muted);
  font-size: 14px;
}

.files-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.btn-arrow {
  margin-left: 4px;
}

/* 确认面板 */
.confirm-panel {
  text-align: center;
  padding: 40px 20px;
}

.confirm-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.confirm-panel h3 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.confirm-desc {
  color: var(--text-secondary);
  line-height: 1.8;
  margin-bottom: 32px;
}

.confirm-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

/* 进度 */
.progress-container {
  padding: 20px;
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.progress-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--bg-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.progress-icon.completed {
  background: #d1fae5;
}

.progress-icon.failed {
  background: #fee2e2;
}

.progress-info h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.progress-desc {
  color: var(--text-secondary);
  font-size: 14px;
}

.current-file {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--card-bg);
  border-radius: 8px;
  font-size: 14px;
}

.file-label {
  color: var(--text-muted);
  margin-right: 8px;
}

.file-name {
  color: var(--text-primary);
  font-weight: 500;
}

.progress-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
}

/* 历史卡片 */
.history-card {
  margin-top: 24px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.history-title {
  font-weight: 600;
  font-size: 16px;
}

/* 响应式 */
@media (max-width: 768px) {
  .steps {
    padding: 10px 0;
  }
  
  .step-line {
    width: 30px;
    margin: 0 8px;
    margin-bottom: 24px;
  }
  
  .step-label {
    font-size: 12px;
  }
  
  .confirm-actions,
  .progress-actions {
    flex-direction: column;
  }
  
  .files-actions {
    flex-direction: column-reverse;
  }
  
  .files-actions .el-button {
    width: 100%;
  }
}
</style>
