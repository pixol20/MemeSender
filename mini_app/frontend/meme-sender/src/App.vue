<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
import Navbar from './components/Navbar.vue';
</script>

<template>
  <div class="flex flex-col h-full">
      <!-- Content -->
      <RouterView />

      <!-- Footer -->
      <Navbar />
  </div>
</template>

