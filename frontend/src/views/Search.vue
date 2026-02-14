<template>
  <div class="search-page">
    <el-card>
      <template #header>
        <h2>🔍 搜索照片</h2>
      </template>

      <!-- 文字搜索 -->
      <el-form @submit.prevent="searchByText">
        <el-input
          v-model="searchQuery"
          placeholder="输入关键词搜索，如：海边、日落、2024年夏天"
          size="large"
          clearable
        >
          <template #append>
            <el-button type="primary" @click="searchByText" :loading="searching">
              搜索
            </el-button>
          </template>
        </el-input>
      </el-form>

      <el-divider>或者</el-divider>

      <!-- 语音搜索 -->
      <div class="voice-search">
        <el-button
          type="primary"
          size="large"
          :type="recording ? 'danger' : 'primary'"
          @click="toggleRecording"
        >
          {{ recording ? '🛑 停止录音' : '🎤 按住说话' }}
        </el-button>
        <p v-if="voiceText" class="voice-text">识别结果: {{ voiceText }}</p>
      </div>
    </el-card>

    <!-- 搜索结果 -->
    <div v-if="results.length > 0" class="search-results">
      <h3>找到 {{ results.length }} 张照片</h3>
      <div class="photo-grid">
        <div v-for="photo in results" :key="photo.id"
             class="photo-card"
             @click="goToDetail(photo.id)">
          <img :src="getPhotoUrl(photo)" :alt="photo.description" />
          <div class="photo-info">
            <p class="photo-desc">{{ photo.description || photo.filename }}</p>
            <p v-if="photo.datetime" class="photo-date">{{ formatDate(photo.datetime) }}</p>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-else-if="searched && results.length === 0" description="没有找到相关照片" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const API_BASE = 'http://localhost:8000'

const searchQuery = ref('')
const searching = ref(false)
const searched = ref(false)
const results = ref([])
const recording = ref(false)
const voiceText = ref('')

let mediaRecorder = null
let audioChunks = []

const getPhotoUrl = (photo) => {
  return `${API_BASE}/api/photo/${photo.id}/thumbnail`
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const goToDetail = (id) => {
  router.push(`/photo/${id}`)
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
    
    // 转为 base64
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
  padding: 20px;
}

.voice-search {
  text-align: center;
  padding: 20px;
}

.voice-text {
  margin-top: 10px;
  color: #409EFF;
  font-size: 18px;
}

.search-results {
  margin-top: 20px;
}

.photo-info {
  padding: 8px;
}

.photo-desc {
  font-size: 16px;
  margin: 0 0 4px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.photo-date {
  font-size: 14px;
  color: #909399;
  margin: 0;
}
</style>
