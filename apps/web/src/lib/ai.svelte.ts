import { api, type AiChatAction, type AiChatImage, type AiConversationSummary, type TelegramLinkCodeResult } from './api';
import { stripMarkdownForSpeech } from './markdown';

export interface ChatEntry {
	role: 'user' | 'assistant';
	content: string;
	actions?: AiChatAction[];
	isError?: boolean;
	imageDataUrl?: string;
}

export interface PendingImage {
	dataUrl: string;
	base64: string;
	mimeType: string;
}

interface AiChatState {
	open: boolean;
	messages: ChatEntry[];
	sending: boolean;
	conversationId: string | undefined;
	seqNumber: number | undefined;
	title: string;
	/** Persisted across sessions (localStorage) — a genuine preference, not
	 * ephemeral UI state, so it survives a reload/relogin. */
	autoSendVoice: boolean;
	/** Grace period (ms) between speech recognition finalizing a result and
	 * the message actually being sent, when autoSendVoice is on. The Web
	 * Speech API has no standard "wait longer" knob — it decides on its own
	 * when you've stopped talking and fires immediately — so this is
	 * implemented as a cancellable delay in ChatPanel.svelte instead: the
	 * recognized text lands in the input with a visible countdown, and
	 * speaking again / editing / hitting Send cancels the pending auto-send.
	 * 0 keeps the old immediate-send behavior. */
	autoSendDelayMs: number;
	speakReplies: boolean;
	/** Sidebar list of the user's own saved chats in this org — loaded
	 * lazily (only when the history panel is opened), not kept constantly
	 * in sync, since it's just a browsing aid, not something that needs
	 * to react to a chat happening in another tab. */
	conversations: AiConversationSummary[];
	historyOpen: boolean;
	loadingHistory: boolean;
	/** A photographed/picked receipt or invoice image, preprocessed
	 * (grayscale + resized — see imagePrep.ts) and waiting to go out with
	 * the next sendMessage call. Cleared once sent (or removed by hand). */
	pendingImage: PendingImage | null;
	/** Telegram link state — server-side (unlike the localStorage voice
	 * prefs above), so it's fetched on demand rather than seeded at
	 * module load. `null` = not yet fetched this session. */
	telegramLinked: boolean | null;
	telegramUsername: string | null;
	telegramLinkCode: TelegramLinkCodeResult | null;
	loadingTelegram: boolean;
}

const DEFAULT_AUTO_SEND_DELAY_MS = 2500;

export const aiChat: AiChatState = $state({
	open: false,
	messages: [],
	sending: false,
	conversationId: undefined,
	seqNumber: undefined,
	title: '',
	autoSendVoice: false,
	autoSendDelayMs: DEFAULT_AUTO_SEND_DELAY_MS,
	speakReplies: false,
	conversations: [],
	historyOpen: false,
	loadingHistory: false,
	pendingImage: null,
	telegramLinked: null,
	telegramUsername: null,
	telegramLinkCode: null,
	loadingTelegram: false
});

export function setPendingImage(image: PendingImage | null) {
	aiChat.pendingImage = image;
}

export async function refreshTelegramLink() {
	aiChat.loadingTelegram = true;
	try {
		const status = await api.getTelegramLink();
		aiChat.telegramLinked = status.linked;
		aiChat.telegramUsername = status.telegram_username ?? null;
		if (status.linked) aiChat.telegramLinkCode = null;
	} catch {
		// Non-critical — leave whatever was there; the user can retry by reopening.
	} finally {
		aiChat.loadingTelegram = false;
	}
}

export async function generateTelegramLinkCode() {
	aiChat.loadingTelegram = true;
	try {
		aiChat.telegramLinkCode = await api.generateTelegramLinkCode();
	} catch (e) {
		aiChat.telegramLinkCode = null;
		throw e;
	} finally {
		aiChat.loadingTelegram = false;
	}
}

export async function unlinkTelegram() {
	await api.unlinkTelegram();
	aiChat.telegramLinked = false;
	aiChat.telegramUsername = null;
	aiChat.telegramLinkCode = null;
}

export function loadAiChatPrefs() {
	if (typeof localStorage === 'undefined') return;
	aiChat.autoSendVoice = localStorage.getItem('mf:ai:autoSendVoice') === '1';
	aiChat.speakReplies = localStorage.getItem('mf:ai:speakReplies') === '1';
	const storedDelayRaw = localStorage.getItem('mf:ai:autoSendDelayMs');
	const storedDelay = storedDelayRaw === null ? NaN : Number(storedDelayRaw);
	aiChat.autoSendDelayMs = Number.isFinite(storedDelay) && storedDelay >= 0 ? storedDelay : DEFAULT_AUTO_SEND_DELAY_MS;
}

export function setAutoSendVoice(value: boolean) {
	aiChat.autoSendVoice = value;
	localStorage.setItem('mf:ai:autoSendVoice', value ? '1' : '0');
}

export function setAutoSendDelayMs(value: number) {
	aiChat.autoSendDelayMs = value;
	localStorage.setItem('mf:ai:autoSendDelayMs', String(value));
}

export function setSpeakReplies(value: boolean) {
	aiChat.speakReplies = value;
	localStorage.setItem('mf:ai:speakReplies', value ? '1' : '0');
}

export function toggleChat() {
	aiChat.open = !aiChat.open;
}

export function closeChat() {
	aiChat.open = false;
}

export function resetConversation() {
	aiChat.messages = [];
	aiChat.conversationId = undefined;
	aiChat.seqNumber = undefined;
	aiChat.title = '';
	aiChat.historyOpen = false;
}

export async function sendMessage(text: string) {
	const trimmed = text.trim();
	const image = aiChat.pendingImage;
	if ((!trimmed && !image) || aiChat.sending) return;
	aiChat.messages = [...aiChat.messages, { role: 'user', content: trimmed, imageDataUrl: image?.dataUrl }];
	aiChat.pendingImage = null;
	aiChat.sending = true;
	try {
		const res = image
			? await api.aiChatWithImage(trimmed, { mime_type: image.mimeType, data: image.base64 }, aiChat.conversationId)
			: await api.aiChat(trimmed, aiChat.conversationId);
		aiChat.conversationId = res.conversation_id;
		aiChat.seqNumber = res.seq_number;
		aiChat.title = res.title;
		aiChat.messages = [...aiChat.messages, { role: 'assistant', content: res.reply, actions: res.actions }];
		if (aiChat.speakReplies) speak(stripMarkdownForSpeech(res.reply));
	} catch (e) {
		const message = e instanceof Error ? e.message : 'Something went wrong talking to the assistant.';
		aiChat.messages = [...aiChat.messages, { role: 'assistant', content: message, isError: true }];
	} finally {
		aiChat.sending = false;
	}
}

export async function toggleHistory() {
	aiChat.historyOpen = !aiChat.historyOpen;
	if (aiChat.historyOpen) await refreshConversationList();
}

export async function refreshConversationList() {
	aiChat.loadingHistory = true;
	try {
		aiChat.conversations = await api.listAiConversations();
	} catch {
		// Non-critical — the list just stays empty/stale; the user can retry by reopening.
	} finally {
		aiChat.loadingHistory = false;
	}
}

export async function loadConversation(id: string) {
	aiChat.loadingHistory = true;
	try {
		const convo = await api.getAiConversation(id);
		aiChat.messages = convo.messages.map((m) => ({
			role: m.role,
			content: m.content,
			// Same-origin request through the SvelteKit proxy, so the browser
			// sends the session cookie automatically — no need to fetch the
			// bytes ourselves and build a data: URL.
			imageDataUrl: m.has_image && m.id ? `/api/ai/conversations/${id}/messages/${m.id}/image` : undefined
		}));
		aiChat.conversationId = convo.id;
		aiChat.seqNumber = convo.seq_number;
		aiChat.title = convo.title;
		aiChat.historyOpen = false;
	} catch (e) {
		aiChat.messages = [
			{
				role: 'assistant',
				content: e instanceof Error ? e.message : 'Could not load that chat.',
				isError: true
			}
		];
	} finally {
		aiChat.loadingHistory = false;
	}
}

export async function deleteConversation(id: string) {
	await api.deleteAiConversation(id);
	aiChat.conversations = aiChat.conversations.filter((c) => c.id !== id);
	if (aiChat.conversationId === id) resetConversation();
}

function speak(text: string) {
	if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
	window.speechSynthesis.cancel();
	window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}
