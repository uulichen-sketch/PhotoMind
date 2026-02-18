<template>
  <div class="faces-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">👤 人物相册</h1>
        <p class="page-subtitle">按人物分类浏览照片</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="showAddPersonDialog = true" :disabled="!faceServiceAvailable">
          <span class="btn-icon">+</span>
          添加人物
        </el-button>
      </div>
    </div>

    <!-- 服务状态提示 -->
    <el-alert
      v-if="!faceServiceAvailable"
      title="人脸识别服务不可用"
      type="warning"
      description="请安装 face-recognition 库：pip install face-recognition"
      show-icon
      :closable="false"
      class="service-alert"
    />

    <!-- 人物列表 -->
    <div v-if="faceServiceAvailable && persons.length > 0" class="persons-grid">
      <div 
        v-for="person in persons" 
        :key="person.id" 
        class="person-card"
        @click="showPersonPhotos(person)"
      >
        <div class="person-avatar">
          <span class="avatar-text">{{ person.name.charAt(0) }}</span>
        </div>
        <div class="person-info">
          <h3 class="person-name">{{ person.name }}</h3>
          <p class="person-count">{{ person.face_count }} 张照片</p>
        </div>
        <el-button 
          class="delete-btn"
          type="danger"
          text
          size="small"
          @click.stop="deletePerson(person)"
        >
          🗑️
        </el-button>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty 
      v-if="faceServiceAvailable && persons.length === 0" 
      description="还没有添加人物"
      class="empty-state"
    >
      <template #description>
        <p>从照片中识别并添加人物</p>
      </template>
      <el-button type="primary" @click="showAddPersonDialog = true">
        添加第一个人物
      </el-button>
    </el-empty>

    <!-- 扫描进度 -->
    <div v-if="scanning" class="scanning-overlay">
      <div class="scanning-content">
        <el-icon class="is-loading" :size="48"><Loading /></el-icon>
        <p>正在扫描照片中的人脸...</p>
        <p class="scan-progress">{{ scanProgress }}</p>
      </div>
    </div>

    <!-- 添加人物对话框 -->
    <el-dialog 
      v-model="showAddPersonDialog" 
      title="添加人物"
      width="500px"
    >
      <el-form :model="newPersonForm" label-width="80px">
        <el-form-item label="人物名称">
          <el-input 
            v-model="newPersonForm.name" 
            placeholder="例如：爸爸、妈妈、小明"
          />
        </el-form-item>
        <el-form-item label="选择照片">
          <el-select 
            v-model="newPersonForm.photo_id" 
            placeholder="选择一张包含该人物的照片"
            filterable
            style="width: 100%"
          >
            <el-option 
              v-for="photo in photos" 
              :key="photo.id"
              :label="photo.filename"
              :value="photo.id"
            >
              <div class="photo-option">
                <img :src="getPhotoUrl(photo)" class="photo-thumb" />
                <span>{{ photo.filename }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddPersonDialog = false">取消</el-button>
        <el-button type="primary" @click="createPerson" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 人物照片详情对话框 -->
    <el-dialog 
      v-model="showPersonDetail" 
      :title="selectedPerson?.name || '人物'"
      width="800px"
    >
      <div class="person-photos">
        <div 
          v-for="photo in personPhotos" 
          :key="photo.id"
          class="person-photo-item"
        >
          <img :src="getPhotoUrl(photo)" :alt="photo.filename" />
          <p class="photo-date">{{ formatDate(photo.datetime) }}</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

// 状态
const faceServiceAvailable = ref(false)
const persons = ref([])
const photos = ref([])
const showAddPersonDialog = ref(false)
const showPersonDetail = ref(false)
const selectedPerson = ref(null)
const personPhotos = ref([])
const scanning = ref(false)
const scanProgress = ref('')
const creating = ref(false)

const newPersonForm = ref({
  name: '',
  photo_id: ''
})

// 检查服务状态
const checkServiceStatus = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/faces/status`)
    faceServiceAvailable.value = res.data.available
  } catch (e) {
    faceServiceAvailable.value = false
  }
}

// 加载人物列表
const loadPersons = async () => {
  if (!faceServiceAvailable.value) return
  
  try {
    const res = await axios.get(`${API_BASE}/api/faces/persons`)
    persons.value = res.data || []
  } catch (e) {
    console.error('加载人物列表失败', e)
  }
}

// 加载照片列表
const loadPhotos = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/photos?status=all`)
    photos.value = res.data || []
  } catch (e) {
    console.error('加载照片列表失败', e)
  }
}

// 获取照片URL
const getPhotoUrl = (photo) => {
  return `${API_BASE}/api/photos/${photo.id}/thumbnail`
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// 创建人物
const createPerson = async () => {
  if (!newPersonForm.value.name) {
    ElMessage.warning('请输入人物名称')
    return
  }
  if (!newPersonForm.value.photo_id) {
    ElMessage.warning('请选择一张照片')
    return
  }
  
  creating.value = true
  try {
    await axios.post(`${API_BASE}/api/faces/persons`, {
      name: newPersonForm.value.name,
      photo_id: newPersonForm.value.photo_id
    })
    
    ElMessage.success('人物创建成功')
    showAddPersonDialog.value = false
    newPersonForm.value = { name: '', photo_id: '' }
    loadPersons()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

// 显示人物照片
const showPersonPhotos = (person) => {
  selectedPerson.value = person
  // TODO: 获取该人物的所有照片
  personPhotos.value = []
  showPersonDetail.value = true
}

// 删除人物
const deletePerson = async (person) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除人物 "${person.name}" 吗？`,
      '确认删除',
      { type: 'warning' }
    )
    
    await axios.delete(`${API_BASE}/api/faces/persons/${person.id}`)
    ElMessage.success('删除成功')
    loadPersons()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 扫描所有照片
const scanAllPhotos = async () => {
  scanning.value = true
  scanProgress.value = '准备扫描...'
  
  try {
    const res = await axios.post(`${API_BASE}/api/faces/scan-all`)
    ElMessage.success(`扫描完成，发现 ${res.data.photos_with_faces} 张包含人脸的照片`)
    loadPersons()
  } catch (e) {
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

onMounted(async () => {
  await checkServiceStatus()
  await loadPhotos()
  await loadPersons()
})
</script>

<style scoped>
.faces-page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.btn-icon {
  margin-right: 8px;
}

.service-alert {
  margin-bottom: 24px;
}

.persons-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
}

.person-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.person-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.person-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-color), var(--primary-hover));
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-text {
  font-size: 28px;
  font-weight: 700;
  color: white;
}

.person-info {
  flex: 1;
}

.person-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.person-count {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.person-card:hover .delete-btn {
  opacity: 1;
}

.empty-state {
  padding: 60px 0;
}

.scanning-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.scanning-content {
  text-align: center;
  color: white;
}

.scanning-content p {
  margin-top: 16px;
  font-size: 16px;
}

.scan-progress {
  font-size: 14px !important;
  color: rgba(255, 255, 255, 0.7);
}

.photo-option {
  display: flex;
  align-items: center;
  gap: 12px;
}

.photo-thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
}

.person-photos {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.person-photo-item {
  text-align: center;
}

.person-photo-item img {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 8px;
}

.photo-date {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
