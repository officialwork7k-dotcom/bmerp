<script lang="ts">
	import { api, type OrgUser, type OrgInvite, type OrgAiSettings } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import ConfirmDialog from '$lib/components/ui/ConfirmDialog.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let users = $state<OrgUser[]>(data.users);
	// svelte-ignore state_referenced_locally
	let invites = $state<OrgInvite[]>(data.invites);
	// svelte-ignore state_referenced_locally
	let aiSettings = $state<OrgAiSettings>(data.aiSettings);

	let activeTab = $state<'users' | 'ai'>('users');

	const ASSIGNABLE_ROLES = ['Org Admin', 'Org Approver', 'Org Operator', 'Org Viewer'];

	let inviteEmail = $state('');
	let inviteRole = $state('Org Operator');
	let inviting = $state(false);

	async function sendInvite() {
		if (!inviteEmail.trim()) {
			toast.error('Email is required');
			return;
		}
		inviting = true;
		try {
			const created = await api.createOrgInvite(inviteEmail.trim(), inviteRole);
			invites = [...invites.filter((i) => i.email !== created.email), created];
			inviteEmail = '';
			toast.success(`Invited ${created.email}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to send invite');
		} finally {
			inviting = false;
		}
	}

	let revokeTarget = $state<OrgInvite | null>(null);
	let revokeOpen = $state(false);
	async function confirmRevoke() {
		if (!revokeTarget) return;
		try {
			await api.revokeOrgInvite(revokeTarget.id);
			invites = invites.map((i) => (i.id === revokeTarget!.id ? { ...i, status: 'revoked' } : i));
			toast.success('Invite revoked');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to revoke invite');
		}
	}

	let deactivateTarget = $state<OrgUser | null>(null);
	let deactivateOpen = $state(false);
	async function confirmDeactivate() {
		if (!deactivateTarget) return;
		try {
			await api.deactivateOrgUser(deactivateTarget.id);
			users = users.map((u) => (u.id === deactivateTarget!.id ? { ...u, is_active: false } : u));
			toast.success(`Deactivated ${deactivateTarget.display_name}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to deactivate user');
		}
	}

	let geminiKeyInput = $state('');
	let openaiKeyInput = $state('');
	let aiSaving = $state(false);

	async function saveAi() {
		aiSaving = true;
		try {
			const body = {
				provider: aiSettings.provider,
				gemini_model: aiSettings.gemini_model,
				openai_model: aiSettings.openai_model,
				discount_tax_treatment: aiSettings.discount_tax_treatment,
				...(geminiKeyInput ? { gemini_api_key: geminiKeyInput } : {}),
				...(openaiKeyInput ? { openai_api_key: openaiKeyInput } : {})
			};
			const saved = await api.saveOrgAiSettings(body);
			aiSettings = saved;
			geminiKeyInput = '';
			openaiKeyInput = '';
			toast.success('AI settings saved');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save AI settings');
		} finally {
			aiSaving = false;
		}
	}

	async function clearAiOverride() {
		aiSaving = true;
		try {
			const saved = await api.saveOrgAiSettings({
				provider: null,
				gemini_model: null,
				openai_model: null,
				discount_tax_treatment: null,
				gemini_api_key: '',
				openai_api_key: ''
			});
			aiSettings = saved;
			toast.success('Reverted to the platform default AI settings');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to clear override');
		} finally {
			aiSaving = false;
		}
	}

	const inputClass =
		'h-9 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900';

	function statusColor(status: OrgInvite['status']): string {
		if (status === 'pending') return 'text-amber-600 dark:text-amber-400';
		if (status === 'accepted') return 'text-green-600 dark:text-green-400';
		return 'text-neutral-400';
	}
</script>

<div class="mx-auto max-w-4xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">Organization</h1>
		<p class="text-sm text-neutral-500">Manage who's in your organization and its own AI assistant settings.</p>
	</div>

	<div class="flex gap-1 border-b border-neutral-200 dark:border-neutral-800">
		<button
			type="button"
			onclick={() => (activeTab = 'users')}
			class="border-b-2 px-3 py-2 text-sm font-medium {activeTab === 'users'
				? 'border-primary-600 text-primary-600'
				: 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
		>
			Users & Invites
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'ai')}
			class="border-b-2 px-3 py-2 text-sm font-medium {activeTab === 'ai'
				? 'border-primary-600 text-primary-600'
				: 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
		>
			AI Assistant
		</button>
	</div>

	{#if activeTab === 'users'}
		<div class="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
			<h2 class="mb-3 text-sm font-semibold">Invite a teammate</h2>
			<div class="flex flex-wrap items-end gap-3">
				<label class="text-sm">
					<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Email</span>
					<input bind:value={inviteEmail} type="email" placeholder="teammate@example.com" class="{inputClass} w-64" />
				</label>
				<label class="text-sm">
					<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Role</span>
					<select bind:value={inviteRole} class="{inputClass} w-48">
						{#each ASSIGNABLE_ROLES as r (r)}
							<option value={r}>{r}</option>
						{/each}
					</select>
				</label>
				<button
					type="button"
					disabled={inviting}
					onclick={sendInvite}
					class="h-9 rounded-md bg-primary-600 px-4 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
				>
					{inviting ? 'Sending…' : 'Send invite'}
				</button>
			</div>
			<p class="mt-2 text-xs text-neutral-400">
				They'll be added automatically the first time they sign in with Google using this exact email address —
				no separate acceptance step needed.
			</p>
		</div>

		<div class="rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
			<h2 class="border-b border-neutral-200 px-6 py-3 text-sm font-semibold dark:border-neutral-800">Pending & past invites</h2>
			{#if invites.length === 0}
				<p class="px-6 py-4 text-sm text-neutral-400">No invites sent yet.</p>
			{:else}
				<table class="w-full text-sm">
					<thead class="bg-neutral-50 dark:bg-neutral-800/50">
						<tr>
							<th class="px-6 py-2 text-left font-medium">Email</th>
							<th class="px-3 py-2 text-left font-medium">Role</th>
							<th class="px-3 py-2 text-left font-medium">Status</th>
							<th class="px-3 py-2 text-left font-medium">Expires</th>
							<th class="px-3 py-2"></th>
						</tr>
					</thead>
					<tbody>
						{#each invites as inv (inv.id)}
							<tr class="border-t border-neutral-100 dark:border-neutral-800">
								<td class="px-6 py-1.5">{inv.email}</td>
								<td class="px-3 py-1.5 text-neutral-500">{inv.role_name}</td>
								<td class="px-3 py-1.5 {statusColor(inv.status)}">{inv.status}</td>
								<td class="px-3 py-1.5 text-neutral-400">{new Date(inv.expires_at).toLocaleDateString()}</td>
								<td class="px-3 py-1.5 text-right">
									{#if inv.status === 'pending'}
										<button
											type="button"
											onclick={() => {
												revokeTarget = inv;
												revokeOpen = true;
											}}
											class="text-xs text-red-600 hover:underline dark:text-red-400"
										>
											Revoke
										</button>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</div>

		<div class="rounded-lg border border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
			<h2 class="border-b border-neutral-200 px-6 py-3 text-sm font-semibold dark:border-neutral-800">Members</h2>
			<table class="w-full text-sm">
				<thead class="bg-neutral-50 dark:bg-neutral-800/50">
					<tr>
						<th class="px-6 py-2 text-left font-medium">User</th>
						<th class="px-3 py-2 text-left font-medium">Roles</th>
						<th class="px-3 py-2 text-left font-medium">Status</th>
						<th class="px-3 py-2"></th>
					</tr>
				</thead>
				<tbody>
					{#each users as u (u.id)}
						<tr class="border-t border-neutral-100 dark:border-neutral-800">
							<td class="px-6 py-1.5">
								<div class="font-medium">{u.display_name}</div>
								<div class="text-xs text-neutral-400">{u.username}</div>
							</td>
							<td class="px-3 py-1.5 text-neutral-500">{u.role_names.join(', ') || '—'}</td>
							<td class="px-3 py-1.5">
								{#if u.is_active}
									<span class="text-xs text-green-600 dark:text-green-400">Active</span>
								{:else}
									<span class="text-xs text-neutral-400">Disabled</span>
								{/if}
							</td>
							<td class="px-3 py-1.5 text-right">
								{#if u.is_active}
									<button
										type="button"
										onclick={() => {
											deactivateTarget = u;
											deactivateOpen = true;
										}}
										class="text-xs text-red-600 hover:underline dark:text-red-400"
									>
										Deactivate
									</button>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{:else}
		<div class="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
			<p class="mb-4 text-sm text-neutral-500">
				By default your organization uses the platform's shared AI assistant configuration. Set your own key below
				to use it instead — leave everything blank to keep inheriting the platform default.
			</p>

			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
				<label class="text-sm">
					<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Provider override</span>
					<select bind:value={aiSettings.provider} class={inputClass}>
						<option value={null}>Inherit platform default</option>
						<option value="gemini">Gemini</option>
						<option value="openai">OpenAI</option>
					</select>
				</label>
				<label class="text-sm">
					<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">
						Discount tax treatment override
					</span>
					<select bind:value={aiSettings.discount_tax_treatment} class={inputClass}>
						<option value={null}>Inherit platform default</option>
						<option value="before_tax">Before tax</option>
						<option value="after_tax">After tax</option>
					</select>
				</label>
			</div>

			{#if aiSettings.provider === 'gemini'}
				<div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">
							Gemini API key {aiSettings.gemini_key_set ? '(set — leave blank to keep)' : ''}
						</span>
						<input type="password" bind:value={geminiKeyInput} class={inputClass} placeholder="•••••••••" />
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Gemini model override</span>
						<input bind:value={aiSettings.gemini_model} class={inputClass} placeholder="e.g. gemini-2.0-flash" />
					</label>
				</div>
			{/if}
			{#if aiSettings.provider === 'openai'}
				<div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">
							OpenAI API key {aiSettings.openai_key_set ? '(set — leave blank to keep)' : ''}
						</span>
						<input type="password" bind:value={openaiKeyInput} class={inputClass} placeholder="•••••••••" />
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">OpenAI model override</span>
						<input bind:value={aiSettings.openai_model} class={inputClass} placeholder="e.g. gpt-4o-mini" />
					</label>
				</div>
			{/if}

			<div class="mt-6 flex items-center gap-3">
				<button
					type="button"
					disabled={aiSaving}
					onclick={saveAi}
					class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
				>
					{aiSaving ? 'Saving…' : 'Save'}
				</button>
				<button
					type="button"
					disabled={aiSaving}
					onclick={clearAiOverride}
					class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
				>
					Revert to platform default
				</button>
			</div>
		</div>
	{/if}
</div>

<ConfirmDialog
	bind:open={revokeOpen}
	title={`Revoke invite for ${revokeTarget?.email ?? ''}?`}
	description="They won't be able to join your organization with this invite anymore."
	confirmLabel="Revoke"
	danger
	onConfirm={confirmRevoke}
/>
<ConfirmDialog
	bind:open={deactivateOpen}
	title={`Deactivate ${deactivateTarget?.display_name ?? ''}?`}
	description="They'll immediately lose the ability to sign in."
	confirmLabel="Deactivate"
	danger
	onConfirm={confirmDeactivate}
/>
