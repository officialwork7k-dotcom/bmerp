<script lang="ts">
	import { onMount } from 'svelte';
	import {
		aiChat,
		closeChat,
		deleteConversation,
		generateTelegramLinkCode,
		loadAiChatPrefs,
		loadConversation,
		refreshTelegramLink,
		resetConversation,
		sendMessage,
		setAutoSendDelayMs,
		setAutoSendVoice,
		setPendingImage,
		setSpeakReplies,
		toggleHistory,
		unlinkTelegram
	} from '$lib/ai.svelte';
	import { ImagePrepError, preprocessReceiptImage } from '$lib/imagePrep';
	import { renderMarkdown } from '$lib/markdown';

	let confirmDeleteId = $state<string | null>(null);

	async function onSelectConversation(id: string) {
		if (id === aiChat.conversationId) return;
		await loadConversation(id);
	}

	async function onDeleteConversation(e: MouseEvent, id: string) {
		e.stopPropagation();
		if (confirmDeleteId !== id) {
			confirmDeleteId = id;
			return;
		}
		confirmDeleteId = null;
		await deleteConversation(id);
	}

	let telegramPanelOpen = $state(false);

	async function toggleTelegramPanel() {
		telegramPanelOpen = !telegramPanelOpen;
		if (telegramPanelOpen) await refreshTelegramLink();
	}

	async function onGenerateTelegramLinkCode() {
		try {
			await generateTelegramLinkCode();
		} catch (e) {
			// Surfaced inline via the panel staying on the "generate" state; a
			// toast would be redundant with the button itself failing to progress.
			console.error(e);
		}
	}

	async function onUnlinkTelegram() {
		await unlinkTelegram();
	}

	let input = $state('');
	let listening = $state(false);
	let voiceSupported = $state(false);
	let scrollEl: HTMLDivElement | undefined = $state();
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	let recognition: any = null;

	let fileInput: HTMLInputElement | undefined = $state();
	let processingImage = $state(false);
	let imageError = $state<string | null>(null);

	function openCamera() {
		imageError = null;
		fileInput?.click();
	}

	async function onFilePicked(e: Event) {
		const file = (e.target as HTMLInputElement).files?.[0];
		(e.target as HTMLInputElement).value = ''; // allow re-picking the same file
		if (!file) return;
		processingImage = true;
		imageError = null;
		try {
			const prepped = await preprocessReceiptImage(file);
			setPendingImage({ dataUrl: prepped.dataUrl, base64: prepped.base64, mimeType: prepped.mimeType });
		} catch (err) {
			imageError = err instanceof ImagePrepError ? err.message : "Couldn't process that image — try again.";
		} finally {
			processingImage = false;
		}
	}

	// Countdown for a pending voice auto-send — see aiChat.autoSendDelayMs's
	// doc comment for why this lives here rather than in the Web Speech API
	// itself. `pendingSendMs` is the total delay this specific pending send
	// was armed with (captured at arm time so a mid-countdown settings
	// change doesn't retroactively resize an already-running bar);
	// `pendingSendRemaining` ticks down for the visible countdown text.
	let pendingSendTimeout: ReturnType<typeof setTimeout> | null = null;
	let pendingSendInterval: ReturnType<typeof setInterval> | null = null;
	let pendingSendMs = $state(0);
	let pendingSendRemaining = $state(0);

	function cancelPendingSend() {
		if (pendingSendTimeout) clearTimeout(pendingSendTimeout);
		if (pendingSendInterval) clearInterval(pendingSendInterval);
		pendingSendTimeout = null;
		pendingSendInterval = null;
		pendingSendMs = 0;
		pendingSendRemaining = 0;
	}

	// Stops the mic outright — used once the countdown either fires (nothing
	// left to capture) or is cancelled (further speech shouldn't silently
	// resume a countdown the user just backed out of).
	function stopListening() {
		if (!listening) return;
		listening = false;
		try {
			recognition?.stop();
		} catch {
			// already stopped — nothing to do
		}
	}

	function armPendingSend(text: string) {
		cancelPendingSend();
		input = text;
		if (aiChat.autoSendDelayMs <= 0) {
			input = '';
			stopListening();
			sendMessage(text);
			return;
		}
		pendingSendMs = aiChat.autoSendDelayMs;
		pendingSendRemaining = aiChat.autoSendDelayMs;
		pendingSendInterval = setInterval(() => {
			pendingSendRemaining = Math.max(0, pendingSendRemaining - 100);
		}, 100);
		pendingSendTimeout = setTimeout(() => {
			const toSend = input;
			cancelPendingSend();
			input = '';
			stopListening();
			sendMessage(toSend);
		}, aiChat.autoSendDelayMs);
	}

	onMount(() => {
		loadAiChatPrefs();
		const SpeechRecognitionCtor =
			(window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition;
		voiceSupported = !!SpeechRecognitionCtor;
		if (voiceSupported) {
			recognition = new SpeechRecognitionCtor();
			recognition.continuous = false;
			recognition.interimResults = false;
			recognition.onresult = (e: any) => {
				const text = e.results[0][0].transcript;
				if (aiChat.autoSendVoice) {
					// Merge onto whatever's already pending rather than
					// replacing it — a result arriving mid-countdown means
					// the user kept talking, not that they restarted.
					const merged = pendingSendMs > 0 ? `${input} ${text}`.trim() : text.trim();
					armPendingSend(merged);
				} else {
					cancelPendingSend();
					input = input ? `${input} ${text}` : text;
				}
			};
			recognition.onend = () => {
				// The recognizer is single-utterance (continuous=false) —
				// it ends itself after every result, and after a bit of
				// silence even with nothing captured. While a send is
				// still counting down and the mic hasn't been stopped by
				// the user, restart it so speech during the "keep
				// talking" window actually gets heard instead of being
				// silently dropped.
				if (aiChat.autoSendVoice && listening && pendingSendMs > 0) {
					try {
						recognition.start();
						return;
					} catch {
						// fall through to stopping below
					}
				}
				listening = false;
			};
			recognition.onerror = () => (listening = false);
		}
		return () => {
			cancelPendingSend();
			stopListening();
		};
	});

	function toggleMic() {
		if (!recognition) return;
		if (listening) {
			listening = false;
			recognition.stop();
		} else {
			cancelPendingSend();
			recognition.start();
			listening = true;
		}
	}

	function onSubmit(e: SubmitEvent) {
		e.preventDefault();
		cancelPendingSend();
		stopListening();
		const text = input;
		input = '';
		sendMessage(text);
	}

	function onInputEdit() {
		// Manual edits mean the user is taking over — a countdown ticking
		// down toward sending whatever they're now busy rewriting would be
		// exactly the "sent too soon" problem this feature exists to fix.
		if (pendingSendTimeout) {
			cancelPendingSend();
			stopListening();
		}
	}

	// Record links inside assistant replies (see markdown.ts) are plain
	// internal <a href="/module/id"> tags — SvelteKit's router already
	// intercepts the navigation itself, this just gets the panel out of
	// the way so the destination page is actually visible afterward.
	function onMessagesClick(e: MouseEvent) {
		const link = (e.target as HTMLElement).closest('a.chat-link');
		if (link) closeChat();
	}

	$effect(() => {
		// Re-run whenever the message list grows.
		void aiChat.messages.length;
		if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
	});
</script>

{#if aiChat.open}
	<div class="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-neutral-200 bg-white shadow-2xl dark:border-neutral-800 dark:bg-neutral-950">
		<div class="flex items-center justify-between border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
			<div class="min-w-0">
				<p class="truncate text-sm font-semibold">
					{#if aiChat.seqNumber}Chat #{aiChat.seqNumber}{#if aiChat.title} — {aiChat.title}{/if}{:else}AI Assistant{/if}
				</p>
				<p class="truncate text-xs text-neutral-400">Ask questions, create and post documents, run reports.</p>
			</div>
			<div class="flex shrink-0 items-center gap-1">
				<button
					type="button"
					onclick={toggleTelegramPanel}
					class="rounded-md px-2 py-1 text-xs {telegramPanelOpen
						? 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200'
						: 'text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					title="Use this assistant from Telegram"
				>
					Telegram
				</button>
				<button
					type="button"
					onclick={toggleHistory}
					class="rounded-md px-2 py-1 text-xs {aiChat.historyOpen
						? 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200'
						: 'text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					title="Past chats"
				>
					History
				</button>
				<button
					type="button"
					onclick={resetConversation}
					class="rounded-md px-2 py-1 text-xs text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
					title="New conversation"
				>
					New
				</button>
				<button
					type="button"
					onclick={closeChat}
					class="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800"
					aria-label="Close"
				>
					✕
				</button>
			</div>
		</div>

		{#if telegramPanelOpen}
			<div class="space-y-2 border-b border-neutral-200 px-4 py-3 text-sm dark:border-neutral-800">
				{#if aiChat.loadingTelegram && aiChat.telegramLinked === null}
					<p class="text-neutral-400">Loading…</p>
				{:else if aiChat.telegramLinked}
					<p>
						Linked to Telegram{#if aiChat.telegramUsername}&nbsp;as <span class="font-medium">@{aiChat.telegramUsername}</span>{/if}.
						You can chat with this assistant — including sending receipt photos — directly from Telegram.
					</p>
					<button
						type="button"
						onclick={onUnlinkTelegram}
						class="rounded-md border border-neutral-300 px-2 py-1 text-xs text-neutral-600 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
					>
						Unlink
					</button>
				{:else if aiChat.telegramLinkCode}
					{#if aiChat.telegramLinkCode.bot_username}
						<p class="text-neutral-500">
							On your own phone, open Telegram and message
							<span class="font-medium">@{aiChat.telegramLinkCode.bot_username}</span>
							— it's the same assistant bot everyone in MetaForge uses; linking your own account keeps your chat
							with it private to you.
						</p>
					{/if}
					<p class="text-neutral-500">
						Send it this code:
						<code class="rounded bg-neutral-100 px-1.5 py-0.5 font-mono text-xs dark:bg-neutral-800">/link {aiChat.telegramLinkCode.code}</code>
					</p>
					{#if aiChat.telegramLinkCode.deep_link}
						<a
							href={aiChat.telegramLinkCode.deep_link}
							target="_blank"
							rel="noreferrer"
							class="inline-block rounded-md bg-primary-600 px-2 py-1 text-xs font-medium text-white hover:bg-primary-700"
						>
							Open in Telegram
						</a>
					{:else}
						<p class="text-xs text-amber-600 dark:text-amber-400">
							The bot's username isn't set up yet — ask your administrator to finish the Telegram configuration.
						</p>
					{/if}
					<p class="text-xs text-neutral-400">Expires {new Date(aiChat.telegramLinkCode.expires_at).toLocaleTimeString()}.</p>
				{:else}
					<p class="text-neutral-500">Connect your Telegram account to chat with this assistant from there too.</p>
					<button
						type="button"
						onclick={onGenerateTelegramLinkCode}
						disabled={aiChat.loadingTelegram}
						class="rounded-md bg-primary-600 px-2 py-1 text-xs font-medium text-white hover:bg-primary-700 disabled:opacity-50"
					>
						{aiChat.loadingTelegram ? '…' : 'Generate link code'}
					</button>
				{/if}
			</div>
		{/if}

		{#if aiChat.historyOpen}
			<div class="max-h-56 overflow-y-auto border-b border-neutral-200 dark:border-neutral-800">
				{#if aiChat.loadingHistory}
					<p class="px-4 py-3 text-sm text-neutral-400">Loading…</p>
				{:else if aiChat.conversations.length === 0}
					<p class="px-4 py-3 text-sm text-neutral-400">No saved chats yet.</p>
				{:else}
					<ul>
						{#each aiChat.conversations as c (c.id)}
							<li
								class="flex w-full items-center gap-2 border-b border-neutral-100 px-4 py-2 text-sm last:border-0 hover:bg-neutral-50 dark:border-neutral-900 dark:hover:bg-neutral-900 {c.id ===
								aiChat.conversationId
									? 'bg-primary-50/60 dark:bg-primary-950/40'
									: ''}"
							>
								<button
									type="button"
									onclick={() => onSelectConversation(c.id)}
									class="flex min-w-0 flex-1 items-center gap-2 text-left"
								>
									<span class="shrink-0 text-xs font-medium text-neutral-400">#{c.seq_number}</span>
									<span class="min-w-0 flex-1 truncate">{c.title || '(untitled)'}</span>
									<span class="shrink-0 text-xs text-neutral-400">{c.message_count}</span>
								</button>
								<button
									type="button"
									onclick={(e) => onDeleteConversation(e, c.id)}
									class="shrink-0 rounded px-1.5 py-0.5 text-xs {confirmDeleteId === c.id
										? 'bg-red-600 text-white'
										: 'text-neutral-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950'}"
									title={confirmDeleteId === c.id ? 'Click again to confirm delete' : 'Delete this chat'}
								>
									{confirmDeleteId === c.id ? 'Confirm?' : '🗑'}
								</button>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		{/if}

		<div class="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-b border-neutral-100 px-4 py-2 text-xs text-neutral-500 dark:border-neutral-900">
			<label class="flex items-center gap-1.5">
				<input
					type="checkbox"
					checked={aiChat.autoSendVoice}
					onchange={(e) => {
						setAutoSendVoice((e.target as HTMLInputElement).checked);
						cancelPendingSend();
						stopListening();
					}}
				/>
				Auto-send voice
			</label>
			{#if aiChat.autoSendVoice}
				<label class="flex items-center gap-1.5" title="How long to wait after you stop talking before it actually sends — gives you a moment to keep speaking or edit first.">
					Delay
					<select
						class="rounded border border-neutral-300 bg-white px-1 py-0.5 text-xs dark:border-neutral-700 dark:bg-neutral-900"
						onchange={(e) => setAutoSendDelayMs(Number((e.target as HTMLSelectElement).value))}
					>
						<option value={0} selected={aiChat.autoSendDelayMs === 0}>Immediately</option>
						<option value={1500} selected={aiChat.autoSendDelayMs === 1500}>1.5s</option>
						<option value={2500} selected={aiChat.autoSendDelayMs === 2500}>2.5s</option>
						<option value={4000} selected={aiChat.autoSendDelayMs === 4000}>4s</option>
						<option value={6000} selected={aiChat.autoSendDelayMs === 6000}>6s</option>
					</select>
				</label>
			{/if}
			<label class="flex items-center gap-1.5">
				<input type="checkbox" checked={aiChat.speakReplies} onchange={(e) => setSpeakReplies((e.target as HTMLInputElement).checked)} />
				Read replies aloud
			</label>
		</div>

		{#if pendingSendMs > 0}
			<div class="flex items-center justify-between gap-2 border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
				<span>Sending in {(pendingSendRemaining / 1000).toFixed(1)}s — keep talking or edit to change it</span>
				<button
					type="button"
					onclick={() => {
						cancelPendingSend();
						stopListening();
					}}
					class="shrink-0 rounded px-2 py-0.5 font-medium text-amber-800 hover:bg-amber-100 dark:text-amber-300 dark:hover:bg-amber-900"
				>
					Cancel
				</button>
			</div>
		{/if}

		<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions --
		     event delegation over the actual interactive elements (the <a class="chat-link">
		     tags rendered inside via @html) — those are the real, independently-clickable
		     controls; this container only closes the panel after one is activated. -->
		<div bind:this={scrollEl} onclick={onMessagesClick} class="flex-1 space-y-3 overflow-y-auto px-4 py-3">
			{#if aiChat.messages.length === 0}
				<p class="mt-8 text-center text-sm text-neutral-400">
					Try: "purchased 1 pc steel at 1000 from vendor ram, post the invoice" or "what's the AP aging as of today"
				</p>
			{/if}
			{#each aiChat.messages as m, i (i)}
				<div class={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
					<div
						class="max-w-[85%] rounded-lg px-3 py-2 text-sm {m.role === 'user'
							? 'bg-primary-600 text-white'
							: m.isError
								? 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400'
								: 'bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100'}"
					>
						{#if m.imageDataUrl}
							<img src={m.imageDataUrl} alt="Scanned document" class="mb-2 max-h-48 rounded border border-black/10 dark:border-white/10" />
						{/if}
						{#if m.role === 'assistant' && !m.isError}
							<div class="chat-markdown">{@html renderMarkdown(m.content)}</div>
						{:else if m.content}
							<p class="whitespace-pre-wrap">{m.content}</p>
						{/if}
						{#if m.actions && m.actions.length > 0}
							<div class="mt-2 space-y-1 border-t border-black/10 pt-2 dark:border-white/10">
								{#each m.actions as a, ai (ai)}
									<p class="flex items-center gap-1.5 text-xs">
										<span>
											{#if a.status === 'executed'}✓{:else if a.status === 'requires_confirmation' || a.status === 'requires_approval'}⚠{:else}✗{/if}
										</span>
										{a.summary}
									</p>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			{/each}
			{#if aiChat.sending}
				<div class="flex justify-start">
					<div class="rounded-lg bg-neutral-100 px-3 py-2 text-sm text-neutral-400 dark:bg-neutral-800">Thinking…</div>
				</div>
			{/if}
		</div>

		{#if aiChat.pendingImage || processingImage || imageError}
			<div class="flex items-center gap-2 border-t border-neutral-200 px-4 py-2 dark:border-neutral-800">
				{#if processingImage}
					<span class="text-xs text-neutral-400">Processing photo…</span>
				{:else if imageError}
					<span class="text-xs text-red-600 dark:text-red-400">{imageError}</span>
					<button type="button" onclick={() => (imageError = null)} class="text-xs text-neutral-400 hover:underline">Dismiss</button>
				{:else if aiChat.pendingImage}
					<img src={aiChat.pendingImage.dataUrl} alt="Attached document" class="h-14 rounded border border-neutral-200 dark:border-neutral-700" />
					<span class="text-xs text-neutral-400">Ready to send with your message</span>
					<button
						type="button"
						onclick={() => setPendingImage(null)}
						class="ml-auto shrink-0 rounded px-2 py-0.5 text-xs text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800"
					>
						Remove
					</button>
				{/if}
			</div>
		{/if}

		<form onsubmit={onSubmit} class="flex items-end gap-2 border-t border-neutral-200 p-3 dark:border-neutral-800">
			<input
				bind:this={fileInput}
				type="file"
				accept="image/*"
				capture="environment"
				class="hidden"
				onchange={onFilePicked}
			/>
			<button
				type="button"
				onclick={openCamera}
				disabled={aiChat.sending || processingImage}
				class="shrink-0 rounded-md p-2 text-sm text-neutral-500 hover:bg-neutral-100 disabled:opacity-50 dark:hover:bg-neutral-800"
				aria-label="Scan receipt or invoice"
				title="Scan a receipt or invoice"
			>
				📷
			</button>
			{#if voiceSupported}
				<button
					type="button"
					onclick={toggleMic}
					class="shrink-0 rounded-md p-2 text-sm {listening
						? 'bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400'
						: 'text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					aria-label={listening ? 'Stop listening' : 'Speak'}
					title={listening ? 'Stop listening' : 'Speak'}
				>
					{listening ? '⏹' : '🎤'}
				</button>
			{/if}
			<textarea
				bind:value={input}
				rows={1}
				placeholder="Type or speak…"
				class="flex-1 resize-none rounded-md border border-neutral-300 px-3 py-2 text-sm outline-none focus:border-primary-500 dark:border-neutral-700 dark:bg-neutral-900"
				onkeydown={(e) => {
					if (e.key === 'Enter' && !e.shiftKey) {
						e.preventDefault();
						(e.currentTarget.form as HTMLFormElement)?.requestSubmit();
					}
				}}
				oninput={onInputEdit}
			></textarea>
			<button
				type="submit"
				disabled={aiChat.sending || (!input.trim() && !aiChat.pendingImage)}
				class="shrink-0 rounded-md bg-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
			>
				Send
			</button>
		</form>
	</div>
{/if}

<style>
	/* @html-injected markup (renderMarkdown's output) isn't covered by
	   Svelte's default per-component style scoping, hence :global() here. */
	:global(.chat-markdown p) {
		margin: 0;
	}
	:global(.chat-markdown p + p) {
		margin-top: 0.5em;
	}
	:global(.chat-markdown ul),
	:global(.chat-markdown ol) {
		margin: 0.4em 0;
		padding-left: 1.25em;
	}
	:global(.chat-markdown ul) {
		list-style-type: disc;
	}
	:global(.chat-markdown ol) {
		list-style-type: decimal;
	}
	:global(.chat-markdown li) {
		margin: 0.15em 0;
	}
	:global(.chat-markdown li + p),
	:global(.chat-markdown p + ul),
	:global(.chat-markdown p + ol) {
		margin-top: 0.4em;
	}
	:global(.chat-markdown code) {
		border-radius: 0.25em;
		background: rgba(127, 127, 127, 0.18);
		padding: 0.1em 0.35em;
		font-size: 0.85em;
		font-family:
			ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
	}
	:global(.chat-markdown strong) {
		font-weight: 600;
	}
	:global(.chat-markdown a.chat-link) {
		color: var(--color-primary-600);
		text-decoration: underline;
		text-underline-offset: 0.15em;
		font-weight: 500;
	}
	:global(.chat-markdown a.chat-link:hover) {
		text-decoration-thickness: 2px;
	}
</style>
