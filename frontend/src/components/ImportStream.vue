<template>
  <div class="import-stream">
    <!-- 头部信息 -->
    <div class="stream-header">
      <div class="progress-ring">
        <svg viewBox="0 0 100 100">
          <circle class="ring-bg" cx="50" cy="50" r="45" />
          <circle 
            class="ring-progress" 
            cx="50" 
            cy="50" 
            r="45"
            :style="{ strokeDashoffset: ringOffset }"
          />
        </svg>
        <div class="progress-text">
          <span class="percentage">{{ progressPercent }}</span>
          <span class="percent-sign">%</span>
        </div>
      </div>
      <div class="header-info">
        <h3>{{ statusText }}</h3>
        <p class="stats">
          已处理 {{ processed }} / {{ total }} 张
          <span v-if="failed > 0" class="failed-count">失败 {{ failed }} 张</span>
        </p>
      </div>
    </div>

    <!-- 当前处理的照片 -->
    <div v-if="currentPhoto" class="current-photo">
      <div class="photo-card-large">
        <div class="photo-preview">
          <img v-if="currentPhoto.preview" :src="currentPhoto.preview" alt="预览" />
          <div v-else class="photo-placeholder">
            <span>📷</span>
          </div>
          <div class="photo-index">#{{ currentPhoto.index }}</div>
        </div>
        
        <div class="photo-processing">
          <h4 class="filename">{{ currentPhoto.filename }}</h4>
          
          <!-- 处理步骤 -->
          <div class="processing-steps">
            <div 
              v-for="step in processingSteps" 
              :key="step.id"
              :class="['step', { 
                'active': currentStep === step.id, 
                'completed': isStepCompleted(step.id) 
              }]"
            >
              <div class="step-icon">
                <span v-if="isStepCompleted(step.id)">✓</span>
                <span v-else-if="currentStep === step.id" class="spinner"></span>
                <span v-else>{{ step.icon }}</span>
              </div>
              <div class="step-info">
                <span class="step-name">{{ step.name }}</span>
                <span class="step-status">{{ getStepStatus(step.id) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI 分析结果 -->
    <div v-if="currentResult" class="ai-result">
      <div class="result-header">
        <span class="ai-icon">🤖</span>
        <span>AI 分析结果</span>
      </div>
      
      <!-- 评分 -->
      <div v-if="currentResult.scores" class="score-section">
        <div class="overall-score" :style="getScoreStyle(currentResult.scores.overall)">
          <span class="score-value">{{ currentResult.scores.overall.toFixed(1) }}</span>
          <span class="score-label">综合评分</span>
        </div>
        <div class="score-details">
          <div class="score-item">
            <span class="score-bar-label">构图</span>
            <div class="mini-bar"><div :style="{ width: (currentResult.scores.composition / 5 * 100) + '%' }"></div></div>
            <span>{{ currentResult.scores.composition.toFixed(1) }}</span>
          </div>
          <div class="score-item">
            <span class="score-bar-label">色彩</span>
            <div class="mini-bar"><div :style="{ width: (currentResult.scores.color / 5 * 100) + '%' }"></div></div>
            <span>{{ currentResult.scores.color.toFixed(1) }}</span>
          </div>
          <div class="score-item">
            <span class="score-bar-label">光线</span>
            <div class="mini-bar"><div :style="{ width: (currentResult.scores.lighting / 5 * 100) + '%' }"></div></div>
            <span>{{ currentResult.scores.lighting.toFixed(1) }}</span>
          </div>
        </div>
      </div>

      <!-- 描述 -->
      <div v-if="currentResult.description" class="description-section">
        <p class="description-text">{{ currentResult.description }}</p>
      </div>

      <!-- 标签 -->
      <div v-if="currentResult.tags?.length" class="tags-section">
        <el-tag v-for="tag in currentResult.tags.slice(0, 8)" :key="tag" size="small" effect="dark">
          {{ tag }}
        </el-tag>
      </div>

      <!-- 评分理由 -->
      <div v-if="currentResult.scores?.reason" class="reason-section">
        <p class="reason-text">💡 {{ currentResult.scores.reason }}</p>
      </div>
    </div>

    <!-- 已完成的照片缩略图 -->
    <div v-if="completedPhotos.length > 0" class="completed-photos">
      <h4>已处理 ({{ completedPhotos.length }})</h4>
      <div class="photo-thumbnails">
        <div 
          v-for="photo in completedPhotos.slice(-10).reverse()" 
          :key="photo.id"
          class="thumb-item"
          :class="{ 'has-score': photo.scores }"
        >
          <img v-if="photo.preview" :src="photo.preview" />
          <div v-else class="thumb-placeholder">📷</div>
          <div v-if="photo.scores" class="thumb-score" :style="getScoreStyle(photo.scores.overall)">
            {{ photo.scores.overall.toFixed(1) }}
          </div>
        </div>
      </div>
    </div>

    <!-- 控制按钮 -->
    <div class="stream-actions">
      <el-button 
        v-if="isComplete" 
        type="primary" 
        size="large"
        @click="$emit('complete')"
      >
        完成，查看照片
      </el-button>
      <el-button 
        v-else-if="error" 
        type="danger" 
        size="large"
        @click="$emit('retry')"
      >
        重试
      </el-button>
      <el-button 
        v-else
        size="large"
        @click="$emit('cancel')"
      >
        取消导入
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  taskId: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['complete', 'retry', 'cancel'])

const API_BASE = 'http://localhost:8000'

// 状态
const total = ref(0)
const processed = ref(0)
const failed = ref(0)
const isComplete = ref(false)
const error = ref(null)
const currentStep = ref('')

// 当前处理的照片
const currentPhoto = ref(null)
const currentResult = ref(null)
const completedPhotos = ref([])

// 处理步骤定义
const processingSteps = [
  { id: 'exif', name: '提取 EXIF', icon: '📋' },
  { id: 'location', name: '解析位置', icon: '📍' },
  { id: 'ai', name: 'AI 分析', icon: '🤖' },
  { id: 'save', name: '保存数据', icon: '💾' }
]

// 计算属性
const progressPercent = computed(() => {
  if (total.value === 0) return 0
  return Math.round((processed.value / total.value) * 100)
})

const ringOffset = computed(() => {
  const circumference = 2 * Math.PI * 45
  return circumference - (progressPercent.value / 100) * circumference
})

const statusText = computed(() => {
  if (isComplete.value) return '导入完成'
  if (error.value) return '导入出错'
  if (currentStep.value === 'ai') return 'AI 分析中...'
  return '正在处理...'
})

// 方法
const isStepCompleted = (stepId) => {
  const stepOrder = ['exif', 'location', 'ai', 'save']
  const currentIndex = stepOrder.indexOf(currentStep.value)
  const stepIndex = stepOrder.indexOf(stepId)
  return stepIndex < currentIndex
}

const getStepStatus = (stepId) => {
  if (currentStep.value === stepId) return '进行中...'
  if (isStepCompleted(stepId)) return '完成'
  return '等待'
}

const getScoreStyle = (score) => {
  let color = '#ef4444'
  if (score >= 4.5) color = '#10b981'
  else if (score >= 4.0) color = '#6366f1'
  else if (score >= 3.0) color = '#f59e0b'
  return { background: color }
}

// 连接 SSE
let eventSource = null

const connectStream = () => {
  eventSource = new EventSource(`${API_BASE}/api/import-stream/events/${props.taskId}`)
  
  eventSource.onmessage = (event) => {
    try {
      const { type, data } = JSON.parse(event.data)
      handleEvent(type, data)
    } catch (e) {
      console.error('Parse event error:', e)
    }
  }
  
  eventSource.onerror = (e) => {
    console.error('SSE error:', e)
    error.value = '连接出错'
    eventSource.close()
  }
}

const handleEvent = (type, data) => {
  switch (type) {
    case 'import_start':
      total.value = data.total
      break
      
    case 'photo_start':
      currentPhoto.value = {
        id: data.photo_id,
        filename: data.filename,
        index: data.progress.current,
        preview: null
      }
      currentStep.value = 'exif'
      currentResult.value = null
      break
      
    case 'exif_extracted':
      currentStep.value = data.exif.gps_latitude ? 'location' : 'ai'
      break
      
    case 'location_found':
      currentStep.value = 'ai'
      break
      
    case 'ai_analyzing':
      currentStep.value = 'ai'
      break
      
    case 'ai_complete':
      currentResult.value = {
        description: data.description,
        tags: data.tags,
        mood: data.mood,
        subjects: data.subjects,
        scores: data.scores
      }
      currentStep.value = 'save'
      break
      
    case 'photo_complete':
      processed.value++
      completedPhotos.value.push({
        id: currentPhoto.value.id,
        filename: currentPhoto.value.filename,
        preview: currentPhoto.value.preview,
        scores: data.metadata?.scores
      })
      currentStep.value = ''
      break
      
    case 'photo_error':
      failed.value++
      break
      
    case 'import_complete':
      isComplete.value = true
      eventSource.close()
      break
      
    case 'error':
      error.value = data.message
      eventSource.close()
      break
      
    case 'complete':
      isComplete.value = true
      eventSource.close()
      break
  }
}

onMounted(() => {
  connectStream()
})

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
  }
})
</script>

<style scoped>
.import-stream {
  max-width: 800px;
  margin: 0 auto;
}

/* 头部进度 */
.stream-header {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
  padding: 24px;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
}

.progress-ring {
  position: relative;
  width: 100px;
  height: 100px;
  flex-shrink: 0;
}

.progress-ring svg {
  transform: rotate(-90deg);
  width: 100%;
  height: 100%;
}

.ring-bg {
  fill: none;
  stroke: var(--border-color);
  stroke-width: 8;
}

.ring-progress {
  fill: none;
  stroke: var(--primary-color);
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 0.5s ease;
}

.progress-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.percentage {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.percent-sign {
  font-size: 14px;
  color: var(--text-muted);
}

.header-info h3 {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: var(--text-primary);
}

.stats {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0;
}

.failed-count {
  color: var(--accent-color);
  margin-left: 12px;
}

/* 当前照片 */
.current-photo {
  margin-bottom: 24px;
}

.photo-card-large {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow);
  display: flex;
  gap: 24px;
}

.photo-preview {
  position: relative;
  width: 200px;
  height: 200px;
  border-radius: var(--radius);
  overflow: hidden;
  flex-shrink: 0;
  background: var(--bg-color);
}

.photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 64px;
}

.photo-index {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.photo-processing {
  flex: 1;
}

.filename {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 20px 0;
  word-break: break-all;
}

.processing-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--bg-color);
  opacity: 0.6;
  transition: all 0.3s ease;
}

.step.active {
  opacity: 1;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  border: 1px solid var(--primary-light);
}

.step.completed {
  opacity: 1;
  background: rgba(16, 185, 129, 0.1);
}

.step-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--card-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.step.active .step-icon {
  background: var(--primary-color);
  color: white;
}

.step.completed .step-icon {
  background: #10b981;
  color: white;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid white;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.step-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.step-status {
  font-size: 12px;
  color: var(--text-muted);
}

/* AI 结果 */
.ai-result {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05), rgba(139, 92, 246, 0.05));
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 24px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.ai-icon {
  font-size: 20px;
}

/* 评分区域 */
.score-section {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px dashed var(--border-color);
}

.overall-score {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.score-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

.score-label {
  font-size: 11px;
  opacity: 0.9;
}

.score-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}

.score-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.score-bar-label {
  width: 40px;
  color: var(--text-secondary);
}

.mini-bar {
  flex: 1;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}

.mini-bar div {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-light));
  border-radius: 3px;
  transition: width 0.5s ease;
}

/* 描述 */
.description-section {
  margin-bottom: 16px;
  padding: 12px;
  background: var(--card-bg);
  border-radius: 8px;
}

.description-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
}

/* 标签 */
.tags-section {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

/* 理由 */
.reason-section {
  padding: 12px;
  background: rgba(245, 158, 11, 0.1);
  border-radius: 8px;
  border-left: 3px solid #f59e0b;
}

.reason-text {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* 已完成照片 */
.completed-photos {
  margin-bottom: 24px;
}

.completed-photos h4 {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.photo-thumbnails {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.thumb-item {
  position: relative;
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-color);
}

.thumb-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.thumb-score {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  color: white;
}

/* 操作按钮 */
.stream-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
}

/* 响应式 */
@media (max-width: 768px) {
  .photo-card-large {
    flex-direction: column;
  }
  
  .photo-preview {
    width: 100%;
    height: 200px;
  }
  
  .score-section {
    flex-direction: column;
    align-items: center;
  }
}
</style>
