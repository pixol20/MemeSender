<script setup lang="ts">
    import { MediaType } from '@/enums';
    const props = defineProps<{
    title: string;
    tags?: string[];
    mediaType: MediaType;
    src: string;
    }>()
</script>

<template>
    <li class="bg-white dark:bg-gray-800 shadow rounded-xl overflow-hidden flex flex-wrap h-auto min-h-48">
      <div class="w-full sm:w-1/2 h-48 sm:h-auto">
        <img v-if="props.mediaType === MediaType.Image"
          class="w-full h-full object-cover"
          :src="props.src"
          :alt="props.title"
        />
        <video v-else-if="props.mediaType === MediaType.Video" :src="props.src"></video>
        <audio v-else-if="props.mediaType === MediaType.Audio" :src="props.src"></audio>
      </div>
      <div class="w-full sm:w-1/2 p-4 flex flex-col justify-center">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">{{ props.title }}</h3>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{{ props.tags }}</p>
      </div>
    </li>
</template>

