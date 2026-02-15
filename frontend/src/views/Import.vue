<template>
  <div class="import-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">导入照片</h1>
        <p class="page-subtitle">上传照片，AI 分析将在后台自动进行</p>
      </div>
    </div>

    <el-card>
      <PhotoUploader />
    </el-card>

    <!-- 导入说明 -->
    <div class="import-tips">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8">
          <div class="tip-card">
            <div class="tip-icon">📤</div>
            <h4>快速上传</h4>
            <p>照片立即保存到云端，无需等待 AI 分析</p>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <div class="tip-card">
            <div class="tip-icon">🤖</div>
            <h4>后台分析</h4>
            <p>AI 自动识别场景、生成描述、智能评分</p>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="8">
          <div class="tip-card">
            <div class="tip-icon">🔍</div>
            <h4>随时搜索</h4>
            <p>分析完成后可通过文字或语音搜索照片</p>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import PhotoUploader from '../components/PhotoUploader.vue'
</script>

<style scoped>
.import-page {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.import-tips {
  margin-top: 32px;
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
  line-height: 1.6;
}
</style>
