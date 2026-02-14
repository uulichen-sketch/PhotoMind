<template>
  <div class="import-page">
    <el-card>
      <template #header>
        <h2>📥 导入照片</h2>
      </template>

      <el-form label-width="120px" label-position="top">
        <el-form-item label="选择照片文件夹">
          <el-input 
            v-model="folderPath" 
            placeholder="输入照片文件夹路径，如: /home/user/photos"
            size="large"
          />
        </el-form-item>

        <el-form-item>
          <el-button 
            type="primary" 
            size="large"
            :loading="importing"
            @click="startImport"
          >
            开始导入
          </el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <!-- 导入进度 -->
      <div v-if="taskId" class="import-progress">
        <h3>导入进度</h3>
        <el-progress 
          :percentage="progressPercent" 
          :status="progressStatus"
          :stroke-width="20"
        />
        <p class="progress-text">
          {{ statusText }}
        </p>
        <p v-if="currentFile" class="current-file">
          正在处理: {{ currentFile }}
        </p>
      </div>
    </el-card>

    <!-- 导入历史 -->
    <el-card v-if="importHistory.length > 0" style="margin-top: 20px;">
      <template #header>
        <h3>导入历史</h3>
      </template>
      <el-table :data="importHistory" style="width: 100%">
        <el-table-column prop="task_id" label="任务ID" />
        <el-table-column prop="status" label="状态" />
        <el-table-column prop="processed" label="已处理" />
        <el-table-column prop="total" label="总数" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE = 'http://localhost:8000'

const folderPath = ref('')
const taskId = ref('')
const importing = ref(false)
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

const statusText = computed(() => {
  switch (status.value) {
    case 'pending': return '等待开始...'
    case 'processing': return `处理中 (${processed.value}/${total.value})`
    case 'completed': return `完成！成功导入 ${processed.value - failed.value} 张照片`
    case 'failed': return '导入失败'
    default: return ''
  }
})

const startImport = async () => {
  if (!folderPath.value) {
    ElMessage.warning('请输入文件夹路径')
    return
  }

  try {
    importing.value = true
    const res = await axios.post(`${API_BASE}/api/import/start`, {
      folder_path: folderPath.value
    })
    
    taskId.value = res.data.task_id
    status.value = res.data.status
    
    // 开始轮询状态
    pollTimer = setInterval(pollStatus, 2000)
    
    ElMessage.success('导入任务已启动')
  } catch (e) {
    ElMessage.error('启动导入失败: ' + (e.response?.data?.detail || e.message))
    importing.value = false
  }
}

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
      importing.value = false
      
      // 添加到历史
      importHistory.value.unshift(data)
    }
  } catch (e) {
    console.error('获取状态失败', e)
  }
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
  padding: 20px;
}

.import-progress {
  margin-top: 20px;
}

.progress-text {
  font-size: 18px;
  margin-top: 10px;
}

.current-file {
  color: #909399;
  font-size: 16px;
}
</style>
