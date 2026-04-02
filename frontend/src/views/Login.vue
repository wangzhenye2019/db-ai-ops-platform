<template>
  <div class="login-page">
    <div class="login-card">
      <div class="title">
        <div class="title-main">AI智能运维平台</div>
        <div class="title-sub">管理员登录</div>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @keyup.enter="onSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>

        <el-button type="primary" :loading="loading" class="submit" @click="onSubmit">
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authAPI } from '@/api/services'
import { getToken, setToken } from '@/utils/auth'

const router = useRouter()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const onSubmit = async () => {
  await formRef.value?.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const data = await authAPI.login({ username: form.username, password: form.password })
      setToken(data.token)
      ElMessage.success('登录成功')
      router.replace('/dashboard')
    } catch (e) {
      ElMessage.error(e.message || '登录失败')
    } finally {
      loading.value = false
    }
  })
}

onMounted(() => {
  if (getToken()) router.replace('/dashboard')
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(1200px 600px at 20% 20%, rgba(64, 158, 255, 0.25), transparent 60%),
    radial-gradient(900px 500px at 80% 30%, rgba(103, 194, 58, 0.18), transparent 55%),
    radial-gradient(1000px 650px at 60% 80%, rgba(230, 162, 60, 0.18), transparent 60%),
    #0f172a;
  padding: 24px;
}

.login-card {
  width: 420px;
  padding: 28px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
}

.title {
  margin-bottom: 18px;
}

.title-main {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.title-sub {
  margin-top: 6px;
  font-size: 13px;
  color: #64748b;
}

.submit {
  width: 100%;
  margin-top: 8px;
}
</style>
