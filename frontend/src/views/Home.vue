<template>
  <div class="home">
    <el-empty v-if="photos.length === 0" description="暂无照片，请先导入">
      <el-button type="primary" size="large" @click="$router.push('/import')">
        导入照片
      </el-button>
    </el-empty>

    <div v-else class="photo-grid">
      <div v-for="photo in photos" :key="photo.id" 
           class="photo-card"
           @click="goToDetail(photo.id)">
        <img :src="getPhotoUrl(photo)" :alt="photo.description" />
        <div class="photo-info">
          <p class="photo-desc">{{ photo.description || photo.filename }}</p>
          <div class="photo-tags">
            <el-tag v-for="tag in (photo.tags || []).slice(0, 3)" :key="tag" size="small">
              {{ tag }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const photos = ref([])

const API_BASE = 'http://localhost:8000'

const getPhotoUrl = (photo) => {
  // 返回本地照片路径的 URL
  return `${API_BASE}/api/photo/${photo.id}/thumbnail`
}

const goToDetail = (id) => {
  router.push(`/photo/${id}`)
}

const loadPhotos = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/photos`)
    photos.value = res.data.photos || []
  } catch (e) {
    console.error('加载照片失败', e)
  }
}

onMounted(() => {
  // loadPhotos() // 暂时注释，等后端接口完善
})
</script>

<style scoped>
.photo-info {
  padding: 8px;
}

.photo-desc {
  font-size: 16px;
  margin: 0 0 8px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.photo-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
</style>
