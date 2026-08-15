<script lang="ts">
	import { AlertDialog } from 'bits-ui';

	let {
		open = $bindable(false),
		title,
		description,
		confirmLabel = 'Confirm',
		danger = false,
		onConfirm
	}: {
		open?: boolean;
		title: string;
		description?: string;
		confirmLabel?: string;
		danger?: boolean;
		onConfirm: () => void;
	} = $props();
</script>

<AlertDialog.Root bind:open>
	<AlertDialog.Portal>
		<AlertDialog.Overlay class="fixed inset-0 z-50 bg-black/40" />
		<AlertDialog.Content
			class="fixed left-1/2 top-1/2 z-50 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-lg border border-neutral-200 bg-white p-5 shadow-xl dark:border-neutral-800 dark:bg-neutral-900"
		>
			<AlertDialog.Title class="text-base font-semibold">{title}</AlertDialog.Title>
			{#if description}
				<AlertDialog.Description class="mt-1.5 text-sm text-neutral-500">{description}</AlertDialog.Description>
			{/if}
			<div class="mt-5 flex justify-end gap-2">
				<AlertDialog.Cancel
					class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-800"
				>
					Cancel
				</AlertDialog.Cancel>
				<AlertDialog.Action
					onclick={onConfirm}
					class="rounded-md px-3 py-1.5 text-sm font-medium text-white {danger
						? 'bg-red-600 hover:bg-red-700'
						: 'bg-primary-600 hover:bg-primary-700'}"
				>
					{confirmLabel}
				</AlertDialog.Action>
			</div>
		</AlertDialog.Content>
	</AlertDialog.Portal>
</AlertDialog.Root>
