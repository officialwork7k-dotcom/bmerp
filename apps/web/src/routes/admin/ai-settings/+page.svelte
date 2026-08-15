<script lang="ts">
	import { api } from '$lib/api';
	import { toast } from '$lib/toast.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// svelte-ignore state_referenced_locally -- one-time seed from load()
	let enabled = $state(data.settings.enabled);
	// svelte-ignore state_referenced_locally
	let provider = $state(data.settings.provider);
	// svelte-ignore state_referenced_locally
	let geminiModel = $state(data.settings.gemini_model);
	// svelte-ignore state_referenced_locally
	let openaiModel = $state(data.settings.openai_model);
	let geminiKeyInput = $state('');
	let openaiKeyInput = $state('');
	// svelte-ignore state_referenced_locally
	let geminiKeySet = $state(data.settings.gemini_key_set);
	// svelte-ignore state_referenced_locally
	let openaiKeySet = $state(data.settings.openai_key_set);
	// svelte-ignore state_referenced_locally
	let amountCap = $state<string>(data.settings.auto_post_amount_cap != null ? String(data.settings.auto_post_amount_cap) : '');
	// svelte-ignore state_referenced_locally
	let discountTaxTreatment = $state(data.settings.discount_tax_treatment ?? 'before_tax');
	// svelte-ignore state_referenced_locally
	let writeAllowed = $state<Record<string, string | null>>(
		Object.fromEntries(data.settings.write_allowed_modules.map((m) => [m.module, m.amount_field]))
	);
	let saving = $state(false);
	let geminiModels = $state<string[] | null>(null);
	let openaiModels = $state<string[] | null>(null);
	let fetchingGeminiModels = $state(false);
	let fetchingOpenaiModels = $state(false);

	// svelte-ignore state_referenced_locally
	let telegramEnabled = $state(data.settings.telegram_enabled);
	let telegramTokenInput = $state('');
	// svelte-ignore state_referenced_locally
	let telegramTokenSet = $state(data.settings.telegram_token_set);
	// svelte-ignore state_referenced_locally
	let telegramBotUsername = $state(data.settings.telegram_bot_username);
	// svelte-ignore state_referenced_locally
	let publicBaseUrl = $state(data.settings.public_base_url ?? '');
	let verifyingTelegram = $state(false);

	async function verifyTelegram() {
		verifyingTelegram = true;
		try {
			const { bot_username } = await api.verifyTelegramToken(telegramTokenInput || undefined);
			telegramBotUsername = bot_username;
			toast.success(`Verified — bot is @${bot_username}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not verify bot token');
		} finally {
			verifyingTelegram = false;
		}
	}

	const inputClass =
		'w-full rounded-md border border-neutral-300 px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-800';

	async function fetchModels(target: 'gemini' | 'openai') {
		const keyInput = target === 'gemini' ? geminiKeyInput : openaiKeyInput;
		const keySet = target === 'gemini' ? geminiKeySet : openaiKeySet;
		if (!keyInput && !keySet) {
			toast.error('Enter an API key first');
			return;
		}
		if (target === 'gemini') fetchingGeminiModels = true;
		else fetchingOpenaiModels = true;
		try {
			const { models } = await api.listAiModels(target, keyInput);
			if (models.length === 0) {
				toast.error('That key returned no chat-capable models');
				return;
			}
			if (target === 'gemini') {
				geminiModels = models;
				if (!models.includes(geminiModel)) geminiModel = models[0];
			} else {
				openaiModels = models;
				if (!models.includes(openaiModel)) openaiModel = models[0];
			}
			toast.success(`Found ${models.length} model${models.length === 1 ? '' : 's'}`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to list models');
		} finally {
			if (target === 'gemini') fetchingGeminiModels = false;
			else fetchingOpenaiModels = false;
		}
	}

	function toggleModule(name: string) {
		if (name in writeAllowed) {
			const { [name]: _, ...rest } = writeAllowed;
			writeAllowed = rest;
		} else {
			writeAllowed = { ...writeAllowed, [name]: null };
		}
	}

	function setAmountField(name: string, value: string) {
		writeAllowed = { ...writeAllowed, [name]: value.trim() || null };
	}

	async function save() {
		saving = true;
		try {
			const body = {
				enabled,
				provider,
				gemini_model: geminiModel,
				openai_model: openaiModel,
				auto_post_amount_cap: amountCap.trim() ? Number(amountCap) : null,
				discount_tax_treatment: discountTaxTreatment,
				write_allowed_modules: Object.entries(writeAllowed).map(([module, amount_field]) => ({ module, amount_field })),
				telegram_enabled: telegramEnabled,
				public_base_url: publicBaseUrl.trim() || null,
				...(geminiKeyInput ? { gemini_api_key: geminiKeyInput } : {}),
				...(openaiKeyInput ? { openai_api_key: openaiKeyInput } : {}),
				...(telegramTokenInput ? { telegram_bot_token: telegramTokenInput } : {})
			};
			const result = await api.saveAiSettings(body);
			geminiKeySet = result.gemini_key_set;
			openaiKeySet = result.openai_key_set;
			telegramTokenSet = result.telegram_token_set;
			telegramBotUsername = result.telegram_bot_username;
			geminiKeyInput = '';
			openaiKeyInput = '';
			telegramTokenInput = '';
			toast.success('AI settings saved');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Failed to save AI settings');
		} finally {
			saving = false;
		}
	}
</script>

<div class="mx-auto max-w-2xl space-y-6 p-6">
	<div>
		<h1 class="text-xl font-semibold">AI Assistant</h1>
		<p class="text-sm text-neutral-500">
			Instance-wide config for the chat assistant. Keys are write-only — once saved, this page never shows the real
			value again, only whether one is set.
		</p>
	</div>

	<div class="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<label class="flex items-center gap-2 text-sm font-medium">
			<input type="checkbox" bind:checked={enabled} />
			Enable AI assistant
		</label>
	</div>

	<div class="space-y-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div>
			<label class="mb-1 block text-xs font-medium text-neutral-500" for="provider">Provider</label>
			<select id="provider" class={inputClass} bind:value={provider}>
				<option value="gemini">Google Gemini</option>
				<option value="openai">OpenAI</option>
			</select>
		</div>

		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			<div>
				<label class="mb-1 block text-xs font-medium text-neutral-500" for="gemini-model">Gemini model</label>
				<div class="flex gap-1.5">
					{#if geminiModels}
						<select id="gemini-model" class={inputClass} bind:value={geminiModel}>
							{#each geminiModels as m (m)}
								<option value={m}>{m}</option>
							{/each}
						</select>
					{:else}
						<input id="gemini-model" class={inputClass} bind:value={geminiModel} />
					{/if}
					<button
						type="button"
						disabled={fetchingGeminiModels}
						onclick={() => fetchModels('gemini')}
						class="shrink-0 rounded-md border border-neutral-300 px-2 py-1.5 text-xs text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
						title="List models available for this key"
					>
						{fetchingGeminiModels ? '…' : 'Fetch'}
					</button>
				</div>
			</div>
			<div>
				<label class="mb-1 block text-xs font-medium text-neutral-500" for="gemini-key">
					Gemini API key {geminiKeySet ? '(set — leave blank to keep)' : '(not set)'}
				</label>
				<input id="gemini-key" type="password" class={inputClass} bind:value={geminiKeyInput} placeholder="•••••••••" />
			</div>
		</div>

		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			<div>
				<label class="mb-1 block text-xs font-medium text-neutral-500" for="openai-model">OpenAI model</label>
				<div class="flex gap-1.5">
					{#if openaiModels}
						<select id="openai-model" class={inputClass} bind:value={openaiModel}>
							{#each openaiModels as m (m)}
								<option value={m}>{m}</option>
							{/each}
						</select>
					{:else}
						<input id="openai-model" class={inputClass} bind:value={openaiModel} />
					{/if}
					<button
						type="button"
						disabled={fetchingOpenaiModels}
						onclick={() => fetchModels('openai')}
						class="shrink-0 rounded-md border border-neutral-300 px-2 py-1.5 text-xs text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
						title="List models available for this key"
					>
						{fetchingOpenaiModels ? '…' : 'Fetch'}
					</button>
				</div>
			</div>
			<div>
				<label class="mb-1 block text-xs font-medium text-neutral-500" for="openai-key">
					OpenAI API key {openaiKeySet ? '(set — leave blank to keep)' : '(not set)'}
				</label>
				<input id="openai-key" type="password" class={inputClass} bind:value={openaiKeyInput} placeholder="•••••••••" />
			</div>
		</div>
		<p class="text-xs text-neutral-400">
			"Fetch" calls the provider with the key above (or the already-saved key if you leave it blank) to list models
			your key can actually use — nothing is saved until you click Save below.
		</p>
	</div>

	<div class="space-y-2 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<label class="mb-1 block text-xs font-medium text-neutral-500" for="amount-cap">
			Auto-post amount cap (only applied to modules below with an amount field set — above this, the assistant asks
			for confirmation instead of posting immediately)
		</label>
		<input id="amount-cap" class={inputClass} placeholder="e.g. 50000 (blank = no cap)" bind:value={amountCap} />
	</div>

	<div class="space-y-2 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<label class="mb-1 block text-xs font-medium text-neutral-500" for="discount-tax-treatment">
			Scanned document discount handling — when should tax be computed?
		</label>
		<select id="discount-tax-treatment" class={inputClass} bind:value={discountTaxTreatment}>
			<option value="before_tax">Before tax (standard — discount reduces the taxable amount)</option>
			<option value="after_tax">After tax (settlement/early-payment discount — deducted from the already-taxed total)</option>
		</select>
		<p class="text-xs text-neutral-400">
			Controls how the assistant records a discount it reads off a scanned vendor/customer invoice. "Before tax" is
			how most invoices actually work — matches the printed total in the vast majority of cases; only switch this
			to "after tax" if your vendors' documents consistently apply their discount after tax instead.
		</p>
	</div>

	<div class="space-y-2 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<p class="mb-1 text-xs font-medium text-neutral-500">
			Modules the assistant may create/post records in. Everything else stays read-only to the assistant (it can
			still search/list/report on any module you have permission for).
		</p>
		<ul class="space-y-1.5">
			{#each data.modules as m (m.name)}
				<li class="flex items-center gap-2 text-sm">
					<input type="checkbox" checked={m.name in writeAllowed} onchange={() => toggleModule(m.name)} />
					<span class="w-40 shrink-0">{m.label}</span>
					{#if m.name in writeAllowed}
						<input
							class="flex-1 rounded-md border border-neutral-300 px-2 py-1 text-xs outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-800"
							placeholder="amount field for the cap above (optional)"
							value={writeAllowed[m.name] ?? ''}
							oninput={(e) => setAmountField(m.name, (e.target as HTMLInputElement).value)}
						/>
					{/if}
				</li>
			{/each}
		</ul>
	</div>

	<div class="space-y-3 rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
		<div>
			<h2 class="text-sm font-semibold">Telegram</h2>
			<p class="text-xs text-neutral-500">
				Lets users chat with the same assistant — including receipt/invoice photos — from Telegram. Each user links
				their own MetaForge account from their own AI Assistant settings; this section only configures the bot itself.
			</p>
		</div>
		<label class="flex items-center gap-2 text-sm font-medium">
			<input type="checkbox" bind:checked={telegramEnabled} />
			Enable Telegram integration
		</label>
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			<div>
				<label class="mb-1 block text-xs font-medium text-neutral-500" for="telegram-token">
					Bot token {telegramTokenSet ? '(set — leave blank to keep)' : '(not set)'}
					{#if telegramBotUsername}<span class="text-neutral-400">— verified as @{telegramBotUsername}</span>{/if}
				</label>
				<div class="flex gap-1.5">
					<input
						id="telegram-token"
						type="password"
						class={inputClass}
						bind:value={telegramTokenInput}
						placeholder="•••••••••"
					/>
					<button
						type="button"
						disabled={verifyingTelegram}
						onclick={verifyTelegram}
						class="shrink-0 rounded-md border border-neutral-300 px-2 py-1.5 text-xs text-neutral-600 hover:bg-neutral-50 disabled:opacity-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
						title="Verify this token with Telegram and save the bot's username"
					>
						{verifyingTelegram ? '…' : 'Verify'}
					</button>
				</div>
				<p class="mt-1 text-xs text-neutral-400">Create a bot with @BotFather on Telegram to get a token.</p>
			</div>
			<div>
				<label class="mb-1 block text-xs font-medium text-neutral-500" for="public-base-url">
					Public base URL <span class="text-neutral-400">(optional)</span>
				</label>
				<input
					id="public-base-url"
					class={inputClass}
					bind:value={publicBaseUrl}
					placeholder="e.g. http://localhost:5173"
				/>
				<p class="mt-1 text-xs text-neutral-400">
					Used to make record links in Telegram replies clickable. Left blank, links show as plain text.
				</p>
			</div>
		</div>
	</div>

	<button
		type="button"
		disabled={saving}
		onclick={save}
		class="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
	>
		{saving ? 'Saving…' : 'Save'}
	</button>
</div>
