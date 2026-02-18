<template>
  <teleport to="body">
    <transition name="viewer-fade">
      <div v-if="visible" class="image-viewer" @click.self="close">
        <button class="viewer-close" @click="close" aria-label="Close viewer">
          <span>x</span>
        </button>

        <div class="viewer-header">
          <span class="viewer-counter">{{ currentIndex + 1 }} / {{ images.length }}</span>
          <span class="viewer-filename">{{ currentImage?.filename || '' }}</span>
        </div>

        <div class="viewer-toolbar">
          <button
            v-for="tool in toolbarTools"
            :key="tool.name"
            class="toolbar-btn"
            :title="tool.title"
            @click="tool.action"
          >
            <span class="toolbar-icon">{{ tool.icon }}</span>
          </button>
        </div>

        <button
          v-if="images.length > 1"
          class="nav-btn nav-prev"
          @click="prev"
          :disabled="currentIndex === 0"
        >
          <span>&lt;</span>
        </button>
        <button
          v-if="images.length > 1"
          class="nav-btn nav-next"
          @click="next"
          :disabled="currentIndex === images.length - 1"
        >
          <span>&gt;</span>
        </button>

        <div class="viewer-body">
          <div
            class="viewer-content"
            @wheel.prevent="handleWheel"
            @mousedown.prevent="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseUp"
          >
            <img
              v-if="currentImage"
              :src="currentImage.src"
              :alt="currentImage.filename"
              class="viewer-image"
              :style="imageStyle"
              @load="handleImageLoad"
              @error="handleImageError"
              draggable="false"
            />
          </div>

          <aside v-if="currentImage" class="viewer-side-panel">
            <div class="panel-section">
              <h3>Photo Info</h3>
              <p class="image-desc">{{ currentImage.description || '-' }}</p>
            </div>

            <div v-if="currentImage.scores" class="panel-section score-section">
              <div class="score-head">
                <span class="score-badge" :style="getScoreStyle(currentImage.scores.overall)">
                  {{ currentImage.scores.overall.toFixed(1) }}
                </span>
                <button class="score-detail-btn" @click="showScoreDetail = !showScoreDetail">
                  {{ showScoreDetail ? 'Hide Score' : 'Show Score' }}
                </button>
              </div>
              <div v-if="showScoreDetail" class="score-detail-panel">
                <PhotoScore :scores="currentImage.scores" />
              </div>
            </div>

            <div class="panel-section">
              <h3>EXIF</h3>
              <div class="exif-list">
                <div v-for="item in exifItems" :key="item.label" class="exif-item">
                  <span class="exif-label">{{ item.label }}</span>
                  <span class="exif-value" :title="item.value">{{ item.value }}</span>
                </div>
              </div>
            </div>
          </aside>
        </div>

        <div v-if="images.length > 1" class="viewer-thumbnails">
          <div
            v-for="(img, index) in images"
            :key="index"
            :class="['thumb-item', { active: index === currentIndex }]"
            @click="goTo(index)"
          >
            <img :src="img.thumbnail || img.src" :alt="img.filename" />
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import PhotoScore from './PhotoScore.vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  images: {
    type: Array,
    default: () => []
  },
  initialIndex: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:visible', 'change', 'close'])

const currentIndex = ref(props.initialIndex)
const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const showScoreDetail = ref(false)

const currentImage = computed(() => props.images[currentIndex.value] || null)

const imageStyle = computed(() => ({
  transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
  cursor: isDragging.value ? 'grabbing' : scale.value > 1 ? 'grab' : 'default',
  transition: isDragging.value ? 'none' : 'transform 0.25s ease'
}))

const toolbarTools = computed(() => [
  { name: 'zoomIn', icon: '+', title: 'Zoom in', action: zoomIn },
  { name: 'zoomOut', icon: '-', title: 'Zoom out', action: zoomOut },
  { name: 'reset', icon: 'o', title: 'Reset', action: reset },
  { name: 'download', icon: 'v', title: 'Download', action: download }
])

const exifItems = computed(() => {
  const img = currentImage.value || {}
  return [
    { label: 'Filename', value: img.filename || '-' },
    { label: 'DateTime', value: formatDate(img.datetime) || '-' },
    { label: 'Location', value: img.location || '-' },
    { label: 'GPS', value: img.gps_latitude && img.gps_longitude ? `${img.gps_latitude}, ${img.gps_longitude}` : '-' },
    { label: 'Camera', value: img.camera || '-' },
    { label: 'Lens', value: img.lens || '-' },
    { label: 'ISO', value: stringify(img.iso) },
    { label: 'Aperture', value: img.aperture || '-' },
    { label: 'Shutter', value: img.shutter || '-' },
    { label: 'Focal Length', value: img.focal_length || '-' },
    { label: 'Size', value: formatFileSize(img.file_size) || '-' },
    { label: 'Resolution', value: img.width && img.height ? `${img.width} x ${img.height}` : '-' },
    { label: 'Photo ID', value: img.id || '-' }
  ]
})

watch(() => props.visible, (val) => {
  if (val) {
    currentIndex.value = props.initialIndex
    reset()
    showScoreDetail.value = false
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

watch(() => props.initialIndex, (val) => {
  currentIndex.value = val
})

const handleKeydown = (e) => {
  if (!props.visible) return

  switch (e.key) {
    case 'Escape':
      close()
      break
    case 'ArrowLeft':
      prev()
      break
    case 'ArrowRight':
      next()
      break
    case '+':
    case '=':
      zoomIn()
      break
    case '-':
      zoomOut()
      break
    case '0':
      reset()
      break
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})

const close = () => {
  emit('update:visible', false)
  emit('close')
}

const prev = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
    reset()
    showScoreDetail.value = false
    emit('change', currentIndex.value)
  }
}

const next = () => {
  if (currentIndex.value < props.images.length - 1) {
    currentIndex.value++
    reset()
    showScoreDetail.value = false
    emit('change', currentIndex.value)
  }
}

const goTo = (index) => {
  if (index !== currentIndex.value) {
    currentIndex.value = index
    reset()
    showScoreDetail.value = false
    emit('change', currentIndex.value)
  }
}

const zoomIn = () => {
  scale.value = Math.min(scale.value * 1.2, 5)
}

const zoomOut = () => {
  scale.value = Math.max(scale.value / 1.2, 0.5)
  if (scale.value <= 1) {
    translateX.value = 0
    translateY.value = 0
  }
}

const reset = () => {
  scale.value = 1
  translateX.value = 0
  translateY.value = 0
}

const handleWheel = (e) => {
  if (e.deltaY < 0) {
    zoomIn()
  } else {
    zoomOut()
  }
}

const handleMouseDown = (e) => {
  if (scale.value > 1) {
    isDragging.value = true
    dragStart.value = {
      x: e.clientX - translateX.value,
      y: e.clientY - translateY.value
    }
  }
}

const handleMouseMove = (e) => {
  if (isDragging.value && scale.value > 1) {
    translateX.value = e.clientX - dragStart.value.x
    translateY.value = e.clientY - dragStart.value.y
  }
}

const handleMouseUp = () => {
  isDragging.value = false
}

const handleImageLoad = () => {}

const handleImageError = () => {
  ElMessage.error('图片加载失败')
}

const download = () => {
  if (currentImage.value?.src) {
    const link = document.createElement('a')
    link.href = currentImage.value.src
    link.download = currentImage.value.filename || 'image.jpg'
    link.click()
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getScoreStyle = (score) => {
  let color = '#ef4444'
  if (score >= 4.5) color = '#10b981'
  else if (score >= 4.0) color = '#6366f1'
  else if (score >= 3.0) color = '#f59e0b'

  return {
    background: color,
    color: 'white'
  }
}

const formatFileSize = (bytes) => {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const stringify = (value) => {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}
</script>

<style scoped>
.image-viewer {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  flex-direction: column;
  backdrop-filter: blur(10px);
}

.viewer-close {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.12);
  color: white;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 30;
}

.viewer-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 16px 72px 16px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(to bottom, rgba(0, 0, 0, 0.72), transparent);
  z-index: 20;
}

.viewer-counter {
  color: white;
  font-size: 13px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.16);
  border-radius: 999px;
}

.viewer-filename {
  color: rgba(255, 255, 255, 0.92);
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.viewer-toolbar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  z-index: 20;
}

.toolbar-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: white;
  cursor: pointer;
}

.toolbar-btn:hover {
  background: rgba(255, 255, 255, 0.18);
}

.toolbar-icon {
  font-size: 16px;
}

.viewer-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
  padding: 72px 16px 12px;
}

.viewer-content {
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.02);
}

.viewer-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
}

.viewer-side-panel {
  min-height: 0;
  overflow: auto;
  border-radius: 12px;
  background: rgba(17, 24, 39, 0.88);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 14px;
}

.panel-section {
  padding-bottom: 14px;
  margin-bottom: 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.panel-section h3 {
  margin: 0 0 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.95);
}

.image-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.86);
}

.score-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.score-badge {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
}

.score-detail-btn {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: white;
  background: rgba(255, 255, 255, 0.08);
  cursor: pointer;
  font-size: 12px;
}

.exif-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.exif-item {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 8px;
  align-items: start;
  font-size: 12px;
}

.exif-label {
  color: rgba(255, 255, 255, 0.6);
}

.exif-value {
  color: rgba(255, 255, 255, 0.9);
  word-break: break-word;
}

.score-detail-panel {
  margin-top: 8px;
}

.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 82px;
  border: none;
  background: rgba(255, 255, 255, 0.08);
  color: white;
  font-size: 28px;
  cursor: pointer;
  border-radius: 10px;
  z-index: 20;
}

.nav-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.nav-prev {
  left: 16px;
}

.nav-next {
  right: 16px;
}

.viewer-thumbnails {
  display: flex;
  gap: 8px;
  padding: 12px 16px 16px;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  overflow-x: auto;
}

.thumb-item {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  flex-shrink: 0;
}

.thumb-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-item.active {
  border-color: var(--primary-color);
}

.viewer-fade-enter-active,
.viewer-fade-leave-active {
  transition: all 0.25s ease;
}

.viewer-fade-enter-from,
.viewer-fade-leave-to {
  opacity: 0;
}

@media (max-width: 1024px) {
  .viewer-body {
    grid-template-columns: 1fr;
    padding-top: 64px;
    gap: 10px;
  }

  .viewer-side-panel {
    max-height: 38vh;
  }

  .nav-btn {
    width: 42px;
    height: 66px;
    font-size: 24px;
  }
}

@media (max-width: 768px) {
  .viewer-toolbar {
    bottom: 84px;
    top: auto;
  }

  .viewer-content {
    min-height: 320px;
  }

  .exif-item {
    grid-template-columns: 88px 1fr;
  }
}
</style>
