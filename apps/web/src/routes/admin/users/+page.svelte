<script lang="ts">
	import { api, type AdminUser, type ApprovalRule, type Client, type Role } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import ConfirmDialog from '$lib/components/ui/ConfirmDialog.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let roles = $state<Role[]>(data.roles);
	// svelte-ignore state_referenced_locally
	let users = $state<AdminUser[]>(data.users);
	// svelte-ignore state_referenced_locally
	let clients = $state<Client[]>(data.clients);
	// svelte-ignore state_referenced_locally
	let approvalRules = $state<ApprovalRule[]>(data.approvalRules);
	// svelte-ignore state_referenced_locally -- static per navigation, not meant to react to `data` changes
	const modules = data.modules;

	let activeTab = $state<'roles' | 'users' | 'clients' | 'approval-rules'>('roles');

	// Only modules with a workflow have transitions an approval rule could
	// gate; a module with none wouldn't have a `to_status` to pick.
	const workflowModules = $derived(modules.filter((m) => m.workflow));
	function statusesFor(moduleName: string): string[] {
		const m = modules.find((x) => x.name === moduleName);
		return m?.workflow ? Object.keys(m.workflow.states) : [];
	}
	function moneyFieldsFor(moduleName: string): string[] {
		const m = modules.find((x) => x.name === moduleName);
		return m ? m.fields.filter((f) => f.data_type === 'MONEY' || f.data_type === 'DECIMAL').map((f) => f.name) : [];
	}

	function emptyApprovalRule(): ApprovalRule {
		return {
			id: '',
			client_code: null,
			module: workflowModules[0]?.name ?? '',
			to_status: '',
			approver_role_id: roles[0]?.id ?? '',
			amount_field: null,
			min_amount: null,
			is_active: true
		};
	}
	let ruleDraft = $state<ApprovalRule>(emptyApprovalRule());
	let ruleSaving = $state(false);
	let ruleDeleteOpen = $state(false);

	function selectRule(r: ApprovalRule) {
		ruleDraft = { ...r };
	}
	function newApprovalRule() {
		ruleDraft = emptyApprovalRule();
	}
	async function saveApprovalRule() {
		if (!ruleDraft.module || !ruleDraft.to_status || !ruleDraft.approver_role_id) {
			toast.error('Module, target status, and approver role are required');
			return;
		}
		ruleSaving = true;
		try {
			const body = {
				client_code: ruleDraft.client_code,
				module: ruleDraft.module,
				to_status: ruleDraft.to_status,
				approver_role_id: ruleDraft.approver_role_id,
				amount_field: ruleDraft.amount_field || null,
				min_amount: ruleDraft.amount_field ? ruleDraft.min_amount : null,
				is_active: ruleDraft.is_active
			};
			const saved = ruleDraft.id ? await api.updateApprovalRule(ruleDraft.id, body) : await api.createApprovalRule(body);
			approvalRules = ruleDraft.id ? approvalRules.map((r) => (r.id === saved.id ? saved : r)) : [...approvalRules, saved];
			ruleDraft = { ...saved };
			toast.success('Approval rule saved');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save approval rule');
		} finally {
			ruleSaving = false;
		}
	}
	async function confirmDeleteApprovalRule() {
		if (!ruleDraft.id) return;
		try {
			await api.deleteApprovalRule(ruleDraft.id);
			approvalRules = approvalRules.filter((r) => r.id !== ruleDraft.id);
			toast.success('Approval rule deleted');
			ruleDraft = emptyApprovalRule();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to delete approval rule');
		}
	}
	function roleName(id: string): string {
		return roles.find((r) => r.id === id)?.name ?? '?';
	}

	const ACTIONS = ['read', 'create', 'update', 'delete'] as const;

	function emptyRole(): Role {
		return { id: '', name: '', is_admin: false, module_permissions: {} };
	}
	function emptyUserDraft() {
		return {
			id: '',
			username: '',
			display_name: '',
			password: '',
			role_ids: [] as string[],
			client_codes: [] as string[],
			default_client_code: null as string | null,
			is_active: true
		};
	}

	function emptyClient(): Client {
		return { id: '', code: '', name: '', is_active: true };
	}
	let clientDraft = $state<Client>(emptyClient());
	let clientSaving = $state(false);
	function selectClient(c: Client) {
		clientDraft = { ...c };
	}
	function newClient() {
		clientDraft = emptyClient();
	}
	async function saveClient() {
		if (!clientDraft.code.trim() || !clientDraft.name.trim()) {
			toast.error('Code and name are required');
			return;
		}
		clientSaving = true;
		try {
			const body = { code: clientDraft.code.trim().toUpperCase(), name: clientDraft.name, is_active: clientDraft.is_active };
			const saved = clientDraft.id ? await api.updateClient(clientDraft.id, body) : await api.createClient(body);
			clients = clientDraft.id ? clients.map((c) => (c.id === saved.id ? saved : c)) : [...clients, saved];
			clientDraft = { ...saved };
			toast.success(`Client "${saved.code}" saved`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save client');
		} finally {
			clientSaving = false;
		}
	}

	let roleDraft = $state<Role>(emptyRole());
	let roleSaving = $state(false);
	let roleDeleteOpen = $state(false);

	function cloneRole(r: Role): Role {
		// `r` (and `saved` below) are entries of the `roles` $state array —
		// Svelte 5's reactive proxy wrapper isn't structured-cloneable, so
		// structuredClone() throws DataCloneError. JSON round-trip strips the
		// proxy the same way the builder page's structuredCloneModule() does.
		return JSON.parse(JSON.stringify(r));
	}
	function selectRole(r: Role) {
		roleDraft = cloneRole(r);
	}
	function newRole() {
		roleDraft = emptyRole();
	}
	function togglePermission(moduleName: string, action: (typeof ACTIONS)[number]) {
		const current = roleDraft.module_permissions[moduleName] ?? {};
		roleDraft.module_permissions = {
			...roleDraft.module_permissions,
			[moduleName]: { ...current, [action]: !current[action] }
		};
	}
	async function saveRole() {
		if (!roleDraft.name.trim()) {
			toast.error('Role name is required');
			return;
		}
		roleSaving = true;
		try {
			const body = { name: roleDraft.name, is_admin: roleDraft.is_admin, module_permissions: roleDraft.module_permissions };
			const saved = roleDraft.id ? await api.updateRole(roleDraft.id, body) : await api.createRole(body);
			roles = roleDraft.id ? roles.map((r) => (r.id === saved.id ? saved : r)) : [...roles, saved];
			roleDraft = cloneRole(saved);
			toast.success(`Role "${saved.name}" saved`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save role');
		} finally {
			roleSaving = false;
		}
	}
	async function confirmDeleteRole() {
		if (!roleDraft.id) return;
		try {
			await api.deleteRole(roleDraft.id);
			roles = roles.filter((r) => r.id !== roleDraft.id);
			toast.success('Role deleted');
			roleDraft = emptyRole();
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to delete role');
		}
	}

	let userDraft = $state(emptyUserDraft());
	let userSaving = $state(false);

	function selectUser(u: AdminUser) {
		userDraft = {
			id: u.id,
			username: u.username,
			display_name: u.display_name,
			password: '',
			role_ids: [...u.role_ids],
			client_codes: [...u.client_codes],
			default_client_code: u.default_client_code,
			is_active: u.is_active
		};
	}
	function newUser() {
		userDraft = emptyUserDraft();
	}
	function toggleUserRole(roleId: string) {
		userDraft.role_ids = userDraft.role_ids.includes(roleId)
			? userDraft.role_ids.filter((id) => id !== roleId)
			: [...userDraft.role_ids, roleId];
	}
	function toggleUserClient(code: string) {
		userDraft.client_codes = userDraft.client_codes.includes(code)
			? userDraft.client_codes.filter((c) => c !== code)
			: [...userDraft.client_codes, code];
		if (!userDraft.client_codes.includes(userDraft.default_client_code ?? '')) {
			userDraft.default_client_code = userDraft.client_codes[0] ?? null;
		}
	}
	async function saveUser() {
		if (!userDraft.username.trim() || !userDraft.display_name.trim()) {
			toast.error('Username and display name are required');
			return;
		}
		if (!userDraft.id && !userDraft.password) {
			toast.error('Password is required for a new user');
			return;
		}
		userSaving = true;
		try {
			if (userDraft.id) {
				await api.updateUser(userDraft.id, {
					username: userDraft.username,
					display_name: userDraft.display_name,
					password: userDraft.password || undefined,
					role_ids: userDraft.role_ids,
					client_codes: userDraft.client_codes,
					default_client_code: userDraft.default_client_code,
					is_active: userDraft.is_active
				});
			} else {
				await api.createUser({
					username: userDraft.username,
					display_name: userDraft.display_name,
					password: userDraft.password,
					role_ids: userDraft.role_ids,
					client_codes: userDraft.client_codes,
					default_client_code: userDraft.default_client_code,
					is_active: userDraft.is_active
				});
			}
			users = await api.listUsers();
			toast.success(`User "${userDraft.username}" saved`);
			const saved = users.find((u) => u.username === userDraft.username);
			if (saved) selectUser(saved);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save user');
		} finally {
			userSaving = false;
		}
	}
	async function forceLogout(u: AdminUser) {
		try {
			await api.forceLogoutUser(u.id);
			toast.success(`Signed out every active session for ${u.username}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to force logout');
		}
	}

	function roleNames(ids: string[]): string {
		if (ids.length === 0) return '—';
		return ids.map((id) => roles.find((r) => r.id === id)?.name ?? '?').join(', ');
	}

	const inputClass =
		'h-9 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900';
</script>

<div class="mx-auto max-w-5xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">Users & Roles</h1>
		<p class="text-sm text-neutral-500">
			Manage who can sign in and what each role can do. Not a generic module — the permission matrix is shaped
			against the live module list, which field metadata can't express.
		</p>
	</div>

	<div class="flex gap-1 border-b border-neutral-200 dark:border-neutral-800">
		<button
			type="button"
			onclick={() => (activeTab = 'roles')}
			class="border-b-2 px-3 py-2 text-sm font-medium {activeTab === 'roles'
				? 'border-primary-600 text-primary-600'
				: 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
		>
			Roles
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'users')}
			class="border-b-2 px-3 py-2 text-sm font-medium {activeTab === 'users'
				? 'border-primary-600 text-primary-600'
				: 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
		>
			Users
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'clients')}
			class="border-b-2 px-3 py-2 text-sm font-medium {activeTab === 'clients'
				? 'border-primary-600 text-primary-600'
				: 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
		>
			Clients
		</button>
		<button
			type="button"
			onclick={() => (activeTab = 'approval-rules')}
			class="border-b-2 px-3 py-2 text-sm font-medium {activeTab === 'approval-rules'
				? 'border-primary-600 text-primary-600'
				: 'border-transparent text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200'}"
		>
			Approval Rules
		</button>
	</div>

	{#if activeTab === 'roles'}
		<div class="grid grid-cols-1 gap-6 md:grid-cols-[14rem_1fr]">
			<div>
				<button
					type="button"
					onclick={newRole}
					class="mb-2 w-full rounded-md border border-dashed border-neutral-300 px-3 py-1.5 text-sm text-neutral-500 hover:border-neutral-400 hover:text-neutral-700 dark:border-neutral-700 dark:hover:text-neutral-300"
				>
					+ New role
				</button>
				<ul class="space-y-1">
					{#each roles as r (r.id)}
						<li>
							<button
								type="button"
								onclick={() => selectRole(r)}
								class="w-full rounded-md px-3 py-1.5 text-left text-sm {roleDraft.id === r.id
									? 'bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300'
									: 'hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
							>
								{r.name}
								{#if r.is_admin}<span class="ml-1 text-xs text-neutral-400">(admin)</span>{/if}
							</button>
						</li>
					{/each}
				</ul>
			</div>

			<div class="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
				<label class="mb-3 block text-sm">
					<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Role name</span>
					<input bind:value={roleDraft.name} class={inputClass} />
				</label>

				<label class="mb-4 flex items-center gap-2 text-sm">
					<input type="checkbox" bind:checked={roleDraft.is_admin} class="h-4 w-4" />
					<span>Administrator (bypasses all permission checks)</span>
				</label>

				{#if !roleDraft.is_admin}
					<h3 class="mb-2 text-xs font-semibold uppercase text-neutral-500">Module permissions</h3>
					<div class="overflow-x-auto rounded-md border border-neutral-200 dark:border-neutral-800">
						<table class="w-full text-sm">
							<thead class="bg-neutral-50 dark:bg-neutral-800/50">
								<tr>
									<th class="px-3 py-2 text-left font-medium">Module</th>
									{#each ACTIONS as action (action)}
										<th class="px-3 py-2 text-center font-medium capitalize">{action}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each modules as m (m.name)}
									<tr class="border-t border-neutral-100 dark:border-neutral-800">
										<td class="px-3 py-1.5">{m.label}</td>
										{#each ACTIONS as action (action)}
											<td class="px-3 py-1.5 text-center">
												<input
													type="checkbox"
													checked={!!roleDraft.module_permissions[m.name]?.[action]}
													onchange={() => togglePermission(m.name, action)}
													class="h-4 w-4"
												/>
											</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}

				<div class="mt-4 flex items-center gap-3">
					<button
						type="button"
						disabled={roleSaving}
						onclick={saveRole}
						class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
					>
						{roleSaving ? 'Saving…' : roleDraft.id ? 'Save role' : 'Create role'}
					</button>
					{#if roleDraft.id}
						<button
							type="button"
							onclick={() => (roleDeleteOpen = true)}
							class="rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950"
						>
							Delete
						</button>
					{/if}
				</div>
			</div>
		</div>
	{:else if activeTab === 'users'}
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-[20rem_1fr]">
			<div>
				<button
					type="button"
					onclick={newUser}
					class="mb-2 w-full rounded-md border border-dashed border-neutral-300 px-3 py-1.5 text-sm text-neutral-500 hover:border-neutral-400 hover:text-neutral-700 dark:border-neutral-700 dark:hover:text-neutral-300"
				>
					+ New user
				</button>
				<div class="overflow-hidden rounded-md border border-neutral-200 dark:border-neutral-800">
					<table class="w-full text-sm">
						<thead class="bg-neutral-50 dark:bg-neutral-800/50">
							<tr>
								<th class="px-3 py-2 text-left font-medium">User</th>
								<th class="px-3 py-2 text-left font-medium">Role</th>
								<th class="px-3 py-2 text-left font-medium">Status</th>
							</tr>
						</thead>
						<tbody>
							{#each users as u (u.id)}
								<tr
									class="cursor-pointer border-t border-neutral-100 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-800/50 {userDraft.id ===
									u.id
										? 'bg-primary-50 dark:bg-primary-950'
										: ''}"
									onclick={() => selectUser(u)}
								>
									<td class="px-3 py-1.5">
										<div class="font-medium">{u.display_name}</div>
										<div class="text-xs text-neutral-400">{u.username}</div>
									</td>
									<td class="px-3 py-1.5 text-neutral-500">{roleNames(u.role_ids)}</td>
									<td class="px-3 py-1.5">
										{#if u.locked_until && new Date(u.locked_until) > new Date()}
											<span class="text-xs text-amber-600 dark:text-amber-400">Locked</span>
										{:else if u.is_active}
											<span class="text-xs text-green-600 dark:text-green-400">Active</span>
										{:else}
											<span class="text-xs text-neutral-400">Disabled</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>

			<div class="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Username</span>
						<input bind:value={userDraft.username} disabled={!!userDraft.id} class={inputClass} />
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Display name</span>
						<input bind:value={userDraft.display_name} class={inputClass} />
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">
							{userDraft.id ? 'Reset password' : 'Password'}
						</span>
						<input type="password" bind:value={userDraft.password} class={inputClass} placeholder={userDraft.id ? 'Leave blank to keep current' : ''} />
					</label>
				</div>

				<div class="mt-4">
					<span class="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
						Roles <span class="font-normal text-neutral-400">(effective permissions are the union of all assigned roles)</span>
					</span>
					{#if roles.length === 0}
						<p class="text-sm text-neutral-400">No roles defined yet.</p>
					{:else}
						<div class="flex flex-wrap gap-2">
							{#each roles as r (r.id)}
								<label
									class="flex cursor-pointer items-center gap-2 rounded-md border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 {userDraft.role_ids.includes(
										r.id
									)
										? 'border-primary-400 bg-primary-50 text-primary-700 dark:border-primary-700 dark:bg-primary-950 dark:text-primary-300'
										: ''}"
								>
									<input
										type="checkbox"
										checked={userDraft.role_ids.includes(r.id)}
										onchange={() => toggleUserRole(r.id)}
										class="h-4 w-4"
									/>
									{r.name}
									{#if r.is_admin}<span class="text-xs text-neutral-400">(admin)</span>{/if}
								</label>
							{/each}
						</div>
					{/if}
				</div>

				<div class="mt-4">
					<span class="mb-1 block text-sm font-medium text-neutral-700 dark:text-neutral-300">
						Clients <span class="font-normal text-neutral-400">(which tenants this user may sign into)</span>
					</span>
					{#if clients.length === 0}
						<p class="text-sm text-neutral-400">No clients defined yet.</p>
					{:else}
						<div class="flex flex-wrap gap-2">
							{#each clients as c (c.id)}
								<label
									class="flex cursor-pointer items-center gap-2 rounded-md border border-neutral-300 px-3 py-1.5 text-sm dark:border-neutral-700 {userDraft.client_codes.includes(
										c.code
									)
										? 'border-primary-400 bg-primary-50 text-primary-700 dark:border-primary-700 dark:bg-primary-950 dark:text-primary-300'
										: ''}"
								>
									<input
										type="checkbox"
										checked={userDraft.client_codes.includes(c.code)}
										onchange={() => toggleUserClient(c.code)}
										class="h-4 w-4"
									/>
									{c.code} <span class="text-xs text-neutral-400">— {c.name}</span>
								</label>
							{/each}
						</div>
						{#if userDraft.client_codes.length > 1}
							<label class="mt-2 block text-sm">
								<span class="mb-1 block text-neutral-500">Default client at login</span>
								<select bind:value={userDraft.default_client_code} class={inputClass}>
									{#each userDraft.client_codes as code (code)}
										<option value={code}>{code}</option>
									{/each}
								</select>
							</label>
						{/if}
					{/if}
				</div>

				<label class="mt-4 flex items-center gap-2 text-sm">
					<input type="checkbox" bind:checked={userDraft.is_active} class="h-4 w-4" />
					<span>Active (unchecking blocks sign-in immediately)</span>
				</label>

				<div class="mt-4 flex items-center gap-3">
					<button
						type="button"
						disabled={userSaving}
						onclick={saveUser}
						class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
					>
						{userSaving ? 'Saving…' : userDraft.id ? 'Save user' : 'Create user'}
					</button>
					{#if userDraft.id}
						{@const u = users.find((x) => x.id === userDraft.id)}
						{#if u}
							<button
								type="button"
								onclick={() => forceLogout(u)}
								class="rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
							>
								Force sign-out
							</button>
						{/if}
					{/if}
				</div>
			</div>
		</div>
	{:else if activeTab === 'clients'}
		<div class="grid grid-cols-1 gap-6 md:grid-cols-[14rem_1fr]">
			<div>
				<button
					type="button"
					onclick={newClient}
					class="mb-2 w-full rounded-md border border-dashed border-neutral-300 px-3 py-1.5 text-sm text-neutral-500 hover:border-neutral-400 hover:text-neutral-700 dark:border-neutral-700 dark:hover:text-neutral-300"
				>
					+ New client
				</button>
				<ul class="space-y-1">
					{#each clients as c (c.id)}
						<li>
							<button
								type="button"
								onclick={() => selectClient(c)}
								class="w-full rounded-md px-3 py-1.5 text-left text-sm {clientDraft.id === c.id
									? 'bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300'
									: 'hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
							>
								{c.code} <span class="text-xs text-neutral-400">— {c.name}</span>
								{#if !c.is_active}<span class="ml-1 text-xs text-neutral-400">(inactive)</span>{/if}
							</button>
						</li>
					{/each}
				</ul>
			</div>

			<div class="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">
							Code <span class="font-normal text-neutral-400">(permanent, SAP MANDT-style, e.g. ORG1)</span>
						</span>
						<input bind:value={clientDraft.code} disabled={!!clientDraft.id} class={inputClass} maxlength="10" />
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Name</span>
						<input bind:value={clientDraft.name} class={inputClass} />
					</label>
				</div>
				<label class="mt-4 flex items-center gap-2 text-sm">
					<input type="checkbox" bind:checked={clientDraft.is_active} class="h-4 w-4" />
					<span>Active</span>
				</label>
				<div class="mt-4">
					<button
						type="button"
						disabled={clientSaving}
						onclick={saveClient}
						class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
					>
						{clientSaving ? 'Saving…' : clientDraft.id ? 'Save client' : 'Create client'}
					</button>
				</div>
			</div>
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-6 md:grid-cols-[16rem_1fr]">
			<div>
				<button
					type="button"
					onclick={newApprovalRule}
					class="mb-2 w-full rounded-md border border-dashed border-neutral-300 px-3 py-1.5 text-sm text-neutral-500 hover:border-neutral-400 hover:text-neutral-700 dark:border-neutral-700 dark:hover:text-neutral-300"
				>
					+ New approval rule
				</button>
				<ul class="space-y-1">
					{#each approvalRules as r (r.id)}
						<li>
							<button
								type="button"
								onclick={() => selectRule(r)}
								class="w-full rounded-md px-3 py-1.5 text-left text-sm {ruleDraft.id === r.id
									? 'bg-primary-50 text-primary-700 dark:bg-primary-950 dark:text-primary-300'
									: 'hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
							>
								<div class="truncate">{r.module} → {r.to_status}</div>
								<div class="truncate text-xs text-neutral-400">
									{roleName(r.approver_role_id)}{r.amount_field ? ` · ${r.amount_field} ≥ ${r.min_amount}` : ''}
									{#if !r.is_active}<span class="text-amber-500"> (inactive)</span>{/if}
								</div>
							</button>
						</li>
					{/each}
					{#if approvalRules.length === 0}
						<p class="px-3 text-sm text-neutral-400">No rules yet — every transition posts straight through.</p>
					{/if}
				</ul>
			</div>

			<div class="rounded-lg border border-neutral-200 bg-white p-6 dark:border-neutral-800 dark:bg-neutral-900">
				<p class="mb-4 text-sm text-neutral-500">
					A record in <span class="font-medium">Module</span> transitioning to
					<span class="font-medium">Target status</span> requires sign-off from someone holding
					<span class="font-medium">Approver role</span> — always, or only once the chosen amount field
					reaches the threshold (tiered approval). Once a rule matches, the transition is always routed
					through the approval queue, even for the approver's own role — decisions stay auditable per document.
				</p>
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Module</span>
						<select
							bind:value={ruleDraft.module}
							onchange={() => {
								ruleDraft.to_status = '';
								ruleDraft.amount_field = null;
							}}
							class={inputClass}
						>
							{#each workflowModules as m (m.name)}
								<option value={m.name}>{m.label}</option>
							{/each}
						</select>
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Target status</span>
						<select bind:value={ruleDraft.to_status} class={inputClass}>
							<option value="">Select…</option>
							{#each statusesFor(ruleDraft.module) as s (s)}
								<option value={s}>{s}</option>
							{/each}
						</select>
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Approver role</span>
						<select bind:value={ruleDraft.approver_role_id} class={inputClass}>
							{#each roles as r (r.id)}
								<option value={r.id}>{r.name}</option>
							{/each}
						</select>
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">
							Scope <span class="font-normal text-neutral-400">(blank = every org)</span>
						</span>
						<select bind:value={ruleDraft.client_code} class={inputClass}>
							<option value={null}>All organizations</option>
							{#each clients as c (c.id)}
								<option value={c.code}>{c.code} — {c.name}</option>
							{/each}
						</select>
					</label>
					<label class="text-sm">
						<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">
							Amount field <span class="font-normal text-neutral-400">(blank = always required)</span>
						</span>
						<select bind:value={ruleDraft.amount_field} class={inputClass}>
							<option value={null}>Always require approval</option>
							{#each moneyFieldsFor(ruleDraft.module) as f (f)}
								<option value={f}>{f}</option>
							{/each}
						</select>
					</label>
					{#if ruleDraft.amount_field}
						<label class="text-sm">
							<span class="mb-1 block font-medium text-neutral-700 dark:text-neutral-300">Minimum amount</span>
							<input type="number" bind:value={ruleDraft.min_amount} class={inputClass} />
						</label>
					{/if}
				</div>
				<label class="mt-4 flex items-center gap-2 text-sm">
					<input type="checkbox" bind:checked={ruleDraft.is_active} class="h-4 w-4" />
					<span>Active</span>
				</label>
				<div class="mt-4 flex items-center gap-3">
					<button
						type="button"
						disabled={ruleSaving}
						onclick={saveApprovalRule}
						class="rounded-md bg-primary-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
					>
						{ruleSaving ? 'Saving…' : ruleDraft.id ? 'Save rule' : 'Create rule'}
					</button>
					{#if ruleDraft.id}
						<button
							type="button"
							onclick={() => (ruleDeleteOpen = true)}
							class="rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 dark:border-red-900 dark:hover:bg-red-950"
						>
							Delete
						</button>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

<ConfirmDialog
	bind:open={roleDeleteOpen}
	title={`Delete role "${roleDraft.name}"?`}
	description="Users assigned to this role will lose its permissions."
	confirmLabel="Delete"
	danger
	onConfirm={confirmDeleteRole}
/>
<ConfirmDialog
	bind:open={ruleDeleteOpen}
	title={`Delete this approval rule?`}
	description="Matching transitions will post straight through again, with no approval gate."
	confirmLabel="Delete"
	danger
	onConfirm={confirmDeleteApprovalRule}
/>
