<script lang="ts">
	import { aiChat, toggleChat } from '$lib/ai.svelte';
</script>

<button
	type="button"
	onclick={toggleChat}
	class="relative rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800 {aiChat.open ? 'bg-neutral-100 dark:bg-neutral-800' : ''}"
	aria-label="AI Assistant"
	title="AI Assistant"
>
	💬
</button>
