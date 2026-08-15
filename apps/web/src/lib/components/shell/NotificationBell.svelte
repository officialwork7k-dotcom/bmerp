<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { goto } from '$app/navigation';
	import { api, type AppNotification } from '$lib/api';
	import { toast } from '$lib/toast.svelte';

	let unreadCount = $state(0);
	let notifications = $state<AppNotification[]>([]);
	let loaded = $state(false);
	let open = $state(false);

	async function refreshCount() {
		try {
			const { count } = await api.unreadNotificationCount();
			unreadCount = count;
		} catch {
			// Polling — a transient failure here just tries again next tick.
		}
	}

	async function onOpenChange(next: boolean) {
		open = next;
		if (next && !loaded) {
			try {
				notifications = await api.listNotifications();
				loaded = true;
			} catch (e) {
				toast.error(e instanceof Error ? e.message : 'Failed to load notifications');
			}
		}
	}

	async function openNotification(n: AppNotification) {
		if (!n.read) {
			try {
				await api.markNotificationRead(n.id);
				n.read = true;
				unreadCount = Math.max(0, unreadCount - 1);
			} catch {
				// Non-critical — the notification still opens even if marking read failed.
			}
		}
		open = false;
		if (n.link) goto(n.link);
	}

	async function markAllRead() {
		try {
			await api.markAllNotificationsRead();
			notifications = notifications.map((n) => ({ ...n, read: true }));
			unreadCount = 0;
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to mark all read');
		}
	}

	$effect(() => {
		refreshCount();
		const interval = setInterval(refreshCount, 20_000);
		return () => clearInterval(interval);
	});
</script>

<DropdownMenu.Root {open} onOpenChange={onOpenChange}>
	<DropdownMenu.Trigger
		class="relative rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
		aria-label="Notifications"
	>
		🔔
		{#if unreadCount > 0}
			<span class="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
				{unreadCount > 99 ? '99+' : unreadCount}
			</span>
		{/if}
	</DropdownMenu.Trigger>
	<DropdownMenu.Portal>
		<DropdownMenu.Content
			class="z-50 w-80 rounded-lg border border-neutral-200 bg-white p-1 shadow-xl dark:border-neutral-800 dark:bg-neutral-900"
			align="end"
			sideOffset={6}
		>
			<div class="flex items-center justify-between px-2 py-1.5">
				<span class="text-sm font-semibold">Notifications</span>
				{#if unreadCount > 0}
					<button type="button" onclick={markAllRead} class="text-xs text-primary-600 hover:underline">Mark all read</button>
				{/if}
			</div>
			<div class="max-h-80 overflow-y-auto">
				{#if notifications.length === 0}
					<p class="px-2 py-6 text-center text-sm text-neutral-400">No notifications yet.</p>
				{:else}
					{#each notifications as n (n.id)}
						<button
							type="button"
							onclick={() => openNotification(n)}
							class="block w-full rounded-md px-2 py-2 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-800 {n.read
								? ''
								: 'bg-primary-50/60 dark:bg-primary-950/40'}"
						>
							<div class="flex items-center gap-1.5 font-medium">
								{#if !n.read}<span class="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-600"></span>{/if}
								{n.title}
							</div>
							{#if n.body}<p class="mt-0.5 text-xs text-neutral-500">{n.body}</p>{/if}
							<p class="mt-0.5 text-xs text-neutral-400">{new Date(n.created_at).toLocaleString()}</p>
						</button>
					{/each}
				{/if}
			</div>
		</DropdownMenu.Content>
	</DropdownMenu.Portal>
</DropdownMenu.Root>
