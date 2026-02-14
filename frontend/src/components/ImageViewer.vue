<template>
  <teleport to="body">
    <transition name="viewer-fade">
      <div v-if="visible" class="image-viewer" @click.self="close">
        <!-- 关闭按钮 -->
        <button class="viewer-close" @click="close">
          <span>×</span>
        </button>

        <!-- 顶部信息栏 -->
        <div class="viewer-header">
          <span class="viewer-counter">{{ currentIndex + 1 }} / {{ images.length }}</span>
          <span class="viewer-filename">{{ currentImage?.filename || '' }}</span>
        </div>

        <!-- 工具栏 -->
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

        <!-- 左右切换按钮 -->
        <button 
          v-if="images.length > 1" 
          class="nav-btn nav-prev" 
          @click="prev"
          :disabled="currentIndex === 0"
        >
          <span>‹</span>
        </button>
        <button 
          v-if="images.length > 1" 
          class="nav-btn nav-next" 
          @click="next"
          :disabled="currentIndex === images.length - 1"
        >
          <span>›</span>
        </button>

        <!-- 图片容器 -->
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

        <!-- 缩略图列表 -->
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

        <!-- 底部信息 -->
        <div v-if="currentImage" class="viewer-footer">
          <div class="image-info">
            <span v-if="currentImage.datetime" class="info-item">
              📅 {{ formatDate(currentImage.datetime) }}
            </span>
            <span v-if="currentImage.location" class="info-item">
              📍 {{ currentImage.location }}
            </span>
            <span v-if="currentImage.camera" class="info-item">
              📷 {{ currentImage.camera }}
            </span>
          </div>
          <p v-if="currentImage.description" class="image-desc">
            {{ currentImage.description }}
          </p>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

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

// 当前索引
const currentIndex = ref(props.initialIndex)

// 缩放和拖拽状态
const scale = ref(1)
const translateX = ref(0)
const translateY = ref(0)
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })

// 计算当前图片
const currentImage = computed(() => {
  return props.images[currentIndex.value] || null
})

// 图片样式
const imageStyle = computed(() => {
  return {
    transform: `translate(${translateX.value}px, ${translateY.value}px) scale(${scale.value})`,
    cursor: isDragging.value ? 'grabbing' : scale.value > 1 ? 'grab' : 'default',
    transition: isDragging.value ? 'none' : 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
  }
})

// 工具栏
const toolbarTools = computed(() => [
  { name: 'zoomIn', icon: '🔍+', title: '放大', action: zoomIn },
  { name: 'zoomOut', icon: '🔍-', title: '缩小', action: zoomOut },
  { name: 'reset', icon: '⟲', title: '重置', action: reset },
  { name: 'download', icon: '⬇️', title: '下载', action: download },
])

// 监听可见性变化
watch(() => props.visible, (val) => {
  if (val) {
    currentIndex.value = props.initialIndex
    reset()
    document.body.style.overflow = 'hidden'
  } else {
    document.body.style.overflow = ''
  }
})

// 监听 initialIndex 变化
watch(() => props.initialIndex, (val) => {
  currentIndex.value = val
})

// 键盘事件处理
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

// 挂载时添加键盘监听
onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})

// 方法
const close = () => {
  emit('update:visible', false)
  emit('close')
}

const prev = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
    reset()
    emit('change', currentIndex.value)
  }
}

const next = () => {
  if (currentIndex.value < props.images.length - 1) {
    currentIndex.value++
    reset()
    emit('change', currentIndex.value)
  }
}

const goTo = (index) => {
  if (index !== currentIndex.value) {
    currentIndex.value = index
    reset()
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

const handleImageLoad = () => {
  // 图片加载完成
}

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

/* 关闭按钮 */
.viewer-close {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  z-index: 10;
}

.viewer-close:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: rotate(90deg);
}

/* 顶部信息栏 */
.viewer-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 20px 80px 20px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  background: linear-gradient(to bottom, rgba(0,0,0,0.6), transparent);
  z-index: 5;
}

.viewer-counter {
  color: white;
  font-size: 14px;
  font-weight: 500;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 20px;
}

.viewer-filename {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 工具栏 */
.viewer-toolbar {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  z-index: 10;
}

.toolbar-btn {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  background: rgba(255, 255, 255, 0.15);
}

.toolbar-icon {
  font-size: 18px;
}

/* 导航按钮 */
.nav-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 60px;
  height: 100px;
  border: none;
  background: rgba(255, 255, 255, 0.05);
  color: white;
  font-size: 48px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  z-index: 10;
  border-radius: 8px;
}

.nav-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.15);
}

.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.nav-prev {
  left: 20px;
}

.nav-next {
  right: 20px;
}

/* 图片容器 */
.viewer-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 80px 100px;
}

.viewer-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
}

/* 缩略图列表 */
.viewer-thumbnails {
  display: flex;
  gap: 8px;
  padding: 16px 20px;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
  overflow-x: auto;
}

.thumb-item {
  width: 60px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.thumb-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-item:hover {
  border-color: rgba(255, 255, 255, 0.5);
}

.thumb-item.active {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px var(--primary-color);
}

/* 底部信息 */
.viewer-footer {
  padding: 16px 20px;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(10px);
}

.image-info {
  display: flex;
  gap: 20px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.info-item {
  color: rgba(255, 255, 255, 0.8);
  font-size: 13px;
}

.image-desc {
  color: white;
  font-size: 14px;
  text-align: center;
  margin: 0;
  line-height: 1.6;
}

/* 过渡动画 */
.viewer-fade-enter-active,
.viewer-fade-leave-active {
  transition: all 0.3s ease;
}

.viewer-fade-enter-from,
.viewer-fade-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* 响应式 */
@media (max-width: 768px) {
  .viewer-content {
    padding: 60px 20px;
  }

  .nav-btn {
    width: 40px;
    height: 60px;
    font-size: 32px;
  }

  .nav-prev {
    left: 10px;
  }

  .nav-next {
    right: 10px;
  }

  .viewer-toolbar {
    bottom: 100px;
    top: auto;
  }

  .viewer-thumbnails {
    padding: 10px;
  }

  .thumb-item {
    width: 50px;
    height: 50px;
  }

  .image-info {
    gap: 12px;
  }

  .info-item {
    font-size: 12px;
  }
}
</style>
