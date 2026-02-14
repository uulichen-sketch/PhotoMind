<template>
  <div class="search-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">搜索照片</h1>
        <p class="page-subtitle">用文字或语音找到您想要的照片</p>
      </div>
    </div>

    <el-card class="search-card">
      <!-- 搜索模式切换 -->
      <div class="search-tabs">
        <div 
          :class="['search-tab', { active: searchMode === 'text' }]"
          @click="searchMode = 'text'"
        >
          <span class="tab-icon">⌨️</span>
          <span>文字搜索</span>
        </div>
        <div 
          :class="['search-tab', { active: searchMode === 'voice' }]"
          @click="searchMode = 'voice'"
        >
          <span class="tab-icon">🎤</span>
          <span>语音搜索</span>
        </div>
      </div>

      <!-- 文字搜索 -->
      <div v-if="searchMode === 'text'" class="search-section">
        <div class="search-box">
          <el-input
            v-model="searchQuery"
            placeholder="输入关键词搜索，如：海边、日落、2024年夏天..."
            size="large"
            clearable
            @keyup.enter="searchByText"
          >
            <template #prefix>
              <span class="search-prefix">🔍</span>
            </template>
          </el-input>
          <el-button 
            type="primary" 
            size="large" 
            :loading="searching"
            @click="searchByText"
          >
            搜索
          </el-button>
        </div>
        
        <!-- 热门搜索 -->
        <div class="hot-searches">
          <span class="hot-label">热门搜索:</span>
          <div class="hot-tags">
            <span 
              v-for="tag in hotSearches" 
              :key="tag"
              class="hot-tag"
              @click="searchQuery = tag; searchByText()"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </div>

      <!-- 语音搜索 -->
      <div v-else class="search-section voice-section">
        <div class="voice-container">
          <button
            :class="['voice-btn', { recording: recording }]"
            @click="toggleRecording"
          >
            <span class="voice-icon">{{ recording ? '⏹️' : '🎤' }}</span>
          </button>
          <p class="voice-hint">
            {{ recording ? '正在录音，点击停止' : '点击开始录音' }}
          </p>
        </div>
        
        <div v-if="voiceText" class="voice-result">
          <div class="voice-text-box">
            <span class="voice-label">识别结果:</span>
            <span class="voice-text">{{ voiceText }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 搜索结果 -->
    <div v-if="results.length > 0" class="results-section">
      <div class="results-header">
        <h3>找到 {{ results.length }} 张相关照片</h3>
        <el-button type="primary" text @click="clearResults">清除结果</el-button>
      </div>
      
      <div class="photo-grid">
        <div 
          v-for="(photo, index) in results" 
          :key="photo.id"
          class="photo-card"
          @click="openViewer(index)"
        >
          <img :src="getPhotoUrl(photo)" :alt="photo.description" loading="lazy" />
          <div class="photo-info">
            <p class="photo-desc">{{ photo.description || photo.filename }}</p>
            <p v-if="photo.datetime" class="photo-date">{{ formatDate(photo.datetime) }}</p>
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

    <!-- 无结果 -->
    <el-empty 
      v-else-if="searched && results.length === 0" 
      class="empty-state"
      :image-size="180"
    >
      <template #description>
        <div class="empty-content">
          <p class="empty-title">没有找到相关照片</p>
          <p class="empty-desc">换个关键词试试，或使用语音搜索</p>
        </div>
      </template>
    </el-empty>

    <!-- 搜索提示 -->
    <div v-else class="search-tips">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8">
          <div class="tip-card">
            <div class="tip-icon">🏖️</div>
            <h4>场景搜索</h4>
            <p>"海边"、"山顶"、"城市夜景"</p>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <div class="tip-card">
            <div class="tip-icon">👥</div>
            <h4>人物搜索</h4>
            <p>"家人合照"、"小朋友"、"朋友聚会"</p>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <div class="tip-card">
            <div class="tip-icon">📅</div>
            <h4>时间搜索</h4>
            <p>"2024年春节"、"去年夏天"</p>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import ImageViewer from '../components/ImageViewer.vue'

const router = useRouter()
const API_BASE = 'http://localhost:8000'

const searchMode = ref('text')
const viewerVisible = ref(false)
const viewerIndex = ref(0)
const searchQuery = ref('')
const searching = ref(false)
const searched = ref(false)
const results = ref([])
const recording = ref(false)
const voiceText = ref('')

const hotSearches = ['海边', '日落', '家人', '旅行', '生日', '宠物']

let mediaRecorder = null
let audioChunks = []

const getPhotoUrl = (photo) => {
  return `${API_BASE}/api/photo/${photo.id}/thumbnail`
}

const getPhotoFileUrl = (photo) => {
  return `${API_BASE}/api/photo/${photo.id}/file`
}

// 图片浏览器数据
const viewerImages = computed(() => {
  return results.value.map(photo => ({
    src: getPhotoFileUrl(photo),
    thumbnail: getPhotoUrl(photo),
    filename: photo.filename,
    description: photo.description,
    datetime: photo.datetime,
    location: photo.location,
    camera: photo.camera
  }))
})

const openViewer = (index) => {
  viewerIndex.value = index
  viewerVisible.value = true
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const goToDetail = (id) => {
  router.push(`/photo/${id}`)
}

const clearResults = () => {
  results.value = []
  searched.value = false
  searchQuery.value = ''
  voiceText.value = ''
}

const searchByText = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }

  try {
    searching.value = true
    const res = await axios.post(`${API_BASE}/api/search/text`, {
      query: searchQuery.value
    })
    results.value = res.data.photos || []
    searched.value = true
  } catch (e) {
    ElMessage.error('搜索失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    searching.value = false
  }
}

const toggleRecording = async () => {
  if (recording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    audioChunks = []

    mediaRecorder.ondataavailable = (e) => {
      audioChunks.push(e.data)
    }

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      await searchByVoice(audioBlob)
      stream.getTracks().forEach(track => track.stop())
    }

    mediaRecorder.start()
    recording.value = true
    voiceText.value = ''
  } catch (e) {
    ElMessage.error('无法访问麦克风')
  }
}

const stopRecording = () => {
  if (mediaRecorder) {
    mediaRecorder.stop()
    recording.value = false
  }
}

const searchByVoice = async (audioBlob) => {
  try {
    searching.value = true
    
    const reader = new FileReader()
    reader.onload = async () => {
      const base64 = reader.result.split(',')[1]
      
      try {
        const res = await axios.post(`${API_BASE}/api/search/voice`, {
          audio: base64
        })
        voiceText.value = res.data.text
        results.value = res.data.photos || []
        searched.value = true
        
        if (res.data.text) {
          ElMessage.success(`识别: "${res.data.text}"`)
        }
      } catch (e) {
        ElMessage.error('语音搜索失败')
      } finally {
        searching.value = false
      }
    }
    reader.readAsDataURL(audioBlob)
  } catch (e) {
    searching.value = false
    ElMessage.error('语音识别失败')
  }
}
</script>

<style scoped>
.search-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

/* 搜索卡片 */
.search-card {
  margin-bottom: 32px;
}

.search-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.search-tab {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  color: var(--text-secondary);
  transition: var(--transition);
}

.search-tab:hover {
  background: var(--bg-color);
  color: var(--text-primary);
}

.search-tab.active {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  color: white;
}

.tab-icon {
  font-size: 18px;
}

/* 搜索区域 */
.search-section {
  padding: 10px 0;
}

.search-box {
  display: flex;
  gap: 12px;
}

.search-box .el-input {
  flex: 1;
}

.search-prefix {
  font-size: 18px;
  margin-right: 8px;
}

/* 热门搜索 */
.hot-searches {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.hot-label {
  font-size: 14px;
  color: var(--text-muted);
}

.hot-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.hot-tag {
  padding: 6px 14px;
  background: var(--bg-color);
  border-radius: 20px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: var(--transition);
}

.hot-tag:hover {
  background: var(--primary-color);
  color: white;
}

/* 语音搜索 */
.voice-section {
  text-align: center;
  padding: 40px 20px;
}

.voice-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.voice-btn {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
  color: white;
  font-size: 40px;
  cursor: pointer;
  transition: var(--transition);
  box-shadow: 0 8px 30px rgba(99, 102, 241, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-btn:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 12px 40px rgba(99, 102, 241, 0.5);
}

.voice-btn.recording {
  background: linear-gradient(135deg, var(--accent-color), #e11d48);
  animation: pulse-record 1.5s infinite;
}

@keyframes pulse-record {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(244, 63, 94, 0.4);
  }
  50% {
    box-shadow: 0 0 0 30px rgba(244, 63, 94, 0);
  }
}

.voice-icon {
  filter: grayscale(100%) brightness(200);
}

.voice-hint {
  color: var(--text-secondary);
  font-size: 16px;
}

.voice-result {
  margin-top: 24px;
}

.voice-text-box {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(6, 182, 212, 0.1));
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.voice-label {
  font-size: 14px;
  color: var(--text-muted);
}

.voice-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-color);
}

/* 搜索结果 */
.results-section {
  animation: slide-up 0.3s ease;
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.results-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 搜索提示 */
.search-tips {
  margin-top: 20px;
}

.tip-card {
  background: var(--card-bg);
  border-radius: var(--radius);
  padding: 24px;
  text-align: center;
  border: 1px solid var(--border-color);
  transition: var(--transition);
  margin-bottom: 20px;
}

.tip-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-4px);
  box-shadow: var(--shadow);
}

.tip-icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.tip-card h4 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.tip-card p {
  font-size: 14px;
  color: var(--text-muted);
}

/* 响应式 */
@media (max-width: 768px) {
  .search-box {
    flex-direction: column;
  }
  
  .search-box .el-button {
    width: 100%;
  }
  
  .hot-searches {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .search-tabs {
    justify-content: center;
  }
  
  .tip-card {
    margin-bottom: 16px;
  }
}
</style>
