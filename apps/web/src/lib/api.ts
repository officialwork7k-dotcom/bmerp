import type { ChildDiff, ModuleMetadata, RecordRow } from './types';

/** Thrown on a 409 whose body is the {error:"version_conflict", current}
 * shape the repository's optimistic-concurrency check returns — lets
 * callers offer a specific "reload to see the latest version" action
 * instead of a generic error toast. */
export class ConflictError extends Error {
	current: RecordRow | undefined;
	constructor(message: string, current?: RecordRow) {
		super(message);
		this.name = 'ConflictError';
		this.current = current;
	}
}

export interface Role {
	id: string;
	name: string;
	is_admin: boolean;
	module_permissions: Record<string, { read?: boolean; create?: boolean; update?: boolean; delete?: boolean }>;
}

export interface ApprovalRule {
	id: string;
	client_code: string | null;
	module: string;
	to_status: string;
	approver_role_id: string;
	amount_field: string | null;
	min_amount: number | null;
	is_active: boolean;
}

export interface ApprovalRequest {
	id: string;
	module: string;
	record_id: string;
	from_status: string;
	to_status: string;
	status: 'pending' | 'approved' | 'rejected';
	note: string | null;
	requested_by: string;
	decided_by: string | null;
	created_at: string;
	decided_at: string | null;
}

export interface AppNotification {
	id: string;
	title: string;
	body: string;
	link: string | null;
	read: boolean;
	created_at: string;
}

export interface AdminUser {
	id: string;
	username: string;
	display_name: string;
	is_active: boolean;
	role_ids: string[];
	client_codes: string[];
	default_client_code: string | null;
	locked_until: string | null;
}

export interface ReportMeasure {
	field?: string | null;
	op: 'sum' | 'count' | 'avg' | 'min' | 'max';
	label?: string | null;
}

export interface ReportFilter {
	field: string;
	op: 'eq' | 'neq' | 'gt' | 'gte' | 'lt' | 'lte';
	value: unknown;
}

export interface ReportDefinition {
	source_module: string;
	group_by: string[];
	measures: ReportMeasure[];
	filters: ReportFilter[];
}

export interface SavedReport {
	id: string;
	name: string;
	definition: ReportDefinition;
	created_at: string;
}

export interface Client {
	id: string;
	code: string;
	name: string;
	is_active: boolean;
}

export interface TrialBalanceRow {
	account_code: string;
	account_name: string;
	debit: number;
	credit: number;
	balance_debit: number;
	balance_credit: number;
}

export interface TrialBalance {
	as_of_date: string;
	rows: TrialBalanceRow[];
	total_debit: number;
	total_credit: number;
	balanced: boolean;
}

export interface AgingRow {
	module: string;
	record_id: string;
	document_label: string;
	party_module: string | null;
	party_id: string | null;
	party_label: string | null;
	due_date: string | null;
	days_overdue: number;
	bucket: 'current' | '1-30' | '31-60' | '61-90' | '90+';
	amount: number;
}

export interface LedgerEntry {
	module: string;
	record_id: string;
	date: string;
	document_label: string;
	amount: number;
	balance: number;
}

export interface PartyLedger {
	party_id: string;
	party_label: string | null;
	date_from: string;
	date_to: string;
	opening_balance: number;
	entries: LedgerEntry[];
	closing_balance: number;
}

export interface SubledgerReconciliationAccount {
	account_code: string;
	account_name: string;
	gl_balance: number;
	subledger_balance: number;
	variance: number;
	matched: boolean;
	sources: Record<string, number>;
}

export interface SubledgerReconciliation {
	as_of_date: string;
	accounts: SubledgerReconciliationAccount[];
	all_matched: boolean;
}

export interface StatementLine {
	account_code: string | null;
	account_name: string;
	amount: number;
}

export interface BalanceSheet {
	as_of_date: string;
	assets: StatementLine[];
	liabilities: StatementLine[];
	equity: StatementLine[];
	total_assets: number;
	total_liabilities: number;
	total_equity: number;
	total_liabilities_and_equity: number;
	balanced: boolean;
}

export interface IncomeStatement {
	date_from: string;
	date_to: string;
	revenue: StatementLine[];
	expenses: StatementLine[];
	total_revenue: number;
	total_expenses: number;
	net_income: number;
}

export interface InventoryValuationRow {
	item_module: string;
	item_id: string;
	item_label: string;
	on_hand_qty: number;
	avg_cost: number;
	value: number;
}

export interface InventoryValuation {
	rows: InventoryValuationRow[];
	total_value: number;
}

export interface FiscalPeriod {
	id: string;
	client_code: string;
	period_key: string;
	start_date: string;
	end_date: string;
	status: 'open' | 'closed';
}

export interface PeriodicRun {
	id: string;
	run_type: string;
	period_key: string;
	status: string;
	result_summary: Record<string, unknown> | null;
	started_at: string;
	completed_at: string | null;
}

export interface Webhook {
	id: string;
	module: string;
	url: string;
	events: string[];
	is_active: boolean;
}

export interface AiSettings {
	enabled: boolean;
	provider: 'gemini' | 'openai';
	gemini_model: string;
	openai_model: string;
	gemini_key_set: boolean;
	openai_key_set: boolean;
	auto_post_amount_cap: number | null;
	write_allowed_modules: { module: string; amount_field: string | null }[];
	discount_tax_treatment: 'before_tax' | 'after_tax';
	telegram_enabled: boolean;
	telegram_token_set: boolean;
	telegram_bot_username: string | null;
	public_base_url: string | null;
}

export interface OrgUser {
	id: string;
	username: string;
	display_name: string;
	is_active: boolean;
	role_names: string[];
}

export interface OrgInvite {
	id: string;
	email: string;
	role_name: string;
	status: 'pending' | 'accepted' | 'revoked' | 'expired';
	expires_at: string;
	created_at: string;
}

export interface OrgAiSettings {
	provider: 'gemini' | 'openai' | null;
	gemini_model: string | null;
	openai_model: string | null;
	gemini_key_set: boolean;
	openai_key_set: boolean;
	discount_tax_treatment: 'before_tax' | 'after_tax' | null;
}

export interface TelegramLinkStatus {
	linked: boolean;
	telegram_username?: string | null;
	linked_at?: string;
	preferred_client_code?: string | null;
}

export interface TelegramLinkCodeResult {
	code: string;
	expires_at: string;
	bot_username: string | null;
	deep_link: string | null;
}

export interface AiChatAction {
	tool: string;
	status: 'executed' | 'rejected' | 'requires_confirmation' | 'requires_approval';
	summary: string;
}

export interface AiChatImage {
	mime_type: string;
	data: string; // base64, no "data:" prefix
}

export interface AiChatMessage {
	id?: string;
	role: 'user' | 'assistant';
	content: string;
	has_image?: boolean;
}

export interface AiChatResponse {
	reply: string;
	actions: AiChatAction[];
	conversation_id: string;
	seq_number: number;
	title: string;
}

export interface AiConversationSummary {
	id: string;
	seq_number: number;
	title: string;
	updated_at: string;
	message_count: number;
}

export interface AiConversationDetail {
	id: string;
	seq_number: number;
	title: string;
	messages: AiChatMessage[];
}

export interface ApiToken {
	id: string;
	name: string;
	last_used_at: string | null;
}

export interface StockMovement {
	id: string;
	movement_type: string;
	quantity: number;
	unit_cost: number | null;
	resulting_qty: number;
	resulting_avg_cost: number;
	document_module: string | null;
	document_id: string | null;
	created_at: string;
}

/**
 * Factory instead of a bare `fetch` reference: SvelteKit's `load` functions
 * run during SSR and must use the `fetch` they're given (it handles
 * relative URLs and forwards cookies) — the global `fetch` throws on a
 * relative URL server-side. Client-only call sites (button handlers, etc.)
 * never run during SSR, so the default export below (bound to the global
 * `fetch`) is fine for them.
 */
export function createApi(fetchImpl: typeof fetch = fetch) {
	async function request<T>(path: string, init?: RequestInit): Promise<T> {
		const res = await fetchImpl(`/api${path}`, {
			...init,
			headers: { 'Content-Type': 'application/json', ...init?.headers },
			credentials: 'include'
		});
		if (!res.ok) {
			const bodyText = await res.text();
			if (res.status === 409) {
				let detail: { error?: string; message?: string; current?: RecordRow } | undefined;
				try {
					const parsed = JSON.parse(bodyText);
					detail = parsed.detail ?? parsed;
				} catch {
					// Not JSON — fall through to the generic error below.
				}
				if (detail?.error === 'version_conflict') {
					throw new ConflictError(detail.message ?? 'Version conflict', detail.current);
				}
				// Every other structured 409 (period_closed, create_blocked,
				// posting_failed, stock_failed, sod_conflict, ...) carries a
				// human-readable `message` — surface just that instead of the
				// raw `{"error": "...", "message": "..."}` blob, which used to
				// go straight into toast.error() unparsed.
				if (typeof detail?.message === 'string') {
					throw new Error(detail.message);
				}
			}
			throw new Error(`${res.status} ${res.statusText}: ${bodyText}`);
		}
		if (res.status === 204) return undefined as T;
		return res.json();
	}

	return {
		listModules: () => request<ModuleMetadata[]>('/modules'),
		getModule: (name: string) => request<ModuleMetadata>(`/modules/${name}`),
		saveModule: (name: string, body: Omit<ModuleMetadata, 'version'>) =>
			request<{ module: ModuleMetadata; migration_written: string | null; warnings: string[] }>(
				`/modules/${name}`,
				{ method: 'PUT', body: JSON.stringify(body) }
			),

		getRecord: (module: string, id: string) => request<RecordRow>(`/data/${module}/${id}`),
		listRecords: (module: string, params: Record<string, string> = {}) =>
			request<RecordRow[]>(`/data/${module}${new URLSearchParams(params).toString() ? '?' + new URLSearchParams(params).toString() : ''}`),
		createRecord: (module: string, data: Record<string, unknown>, children: Record<string, ChildDiff> = {}) =>
			request<RecordRow>(`/data/${module}`, { method: 'POST', body: JSON.stringify({ data, children }) }),
		updateRecord: (
			module: string,
			id: string,
			data: Record<string, unknown>,
			children: Record<string, ChildDiff> = {}
		) =>
			request<RecordRow>(`/data/${module}/${id}`, {
				method: 'PATCH',
				body: JSON.stringify({ data, children })
			}),
		deleteRecord: (module: string, id: string) => request<void>(`/data/${module}/${id}`, { method: 'DELETE' }),
		transitionRecord: (module: string, id: string, to: string, note?: string, version?: number) =>
			request<RecordRow>(`/data/${module}/${id}/transition`, { method: 'POST', body: JSON.stringify({ to, note, version }) }),
		getRecordHistory: (module: string, id: string) =>
			request<
				{ id: string; action: string; changes: Record<string, unknown> | null; actor: string; created_at: string }[]
			>(`/data/${module}/${id}/history`),

		listRoles: () => request<Role[]>('/admin/roles'),
		createRole: (body: Omit<Role, 'id'>) => request<Role>('/admin/roles', { method: 'POST', body: JSON.stringify(body) }),
		updateRole: (id: string, body: Omit<Role, 'id'>) =>
			request<Role>(`/admin/roles/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
		deleteRole: (id: string) => request<void>(`/admin/roles/${id}`, { method: 'DELETE' }),

		listUsers: () => request<AdminUser[]>('/admin/users'),
		createUser: (body: {
			username: string;
			display_name: string;
			password: string;
			role_ids: string[];
			is_active: boolean;
			client_codes?: string[];
			default_client_code?: string | null;
		}) => request<{ id: string; username: string }>('/admin/users', { method: 'POST', body: JSON.stringify(body) }),
		updateUser: (
			id: string,
			body: {
				username: string;
				display_name: string;
				password?: string;
				role_ids: string[];
				is_active: boolean;
				client_codes?: string[];
				default_client_code?: string | null;
			}
		) => request<{ id: string; username: string }>(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
		forceLogoutUser: (id: string) => request<{ ok: boolean }>(`/admin/users/${id}/force-logout`, { method: 'POST' }),

		listClients: () => request<Client[]>('/admin/clients'),
		createClient: (body: Omit<Client, 'id'>) => request<Client>('/admin/clients', { method: 'POST', body: JSON.stringify(body) }),
		updateClient: (id: string, body: Omit<Client, 'id'>) =>
			request<Client>(`/admin/clients/${id}`, { method: 'PUT', body: JSON.stringify(body) }),

		setTheme: (theme: string) => request<{ theme: string }>('/auth/theme', { method: 'PUT', body: JSON.stringify({ theme }) }),

		requestApproval: (module: string, recordId: string, fromStatus: string, toStatus: string, note?: string) =>
			request<ApprovalRequest>('/approvals', {
				method: 'POST',
				body: JSON.stringify({ module, record_id: recordId, from_status: fromStatus, to_status: toStatus, note })
			}),
		listPendingApprovals: () => request<ApprovalRequest[]>('/approvals/pending'),
		listApprovalHistory: () => request<ApprovalRequest[]>('/approvals/history'),
		decideApproval: (id: string, approve: boolean, note?: string) =>
			request<ApprovalRequest>(`/approvals/${id}/decide`, { method: 'POST', body: JSON.stringify({ approve, note }) }),

		listApprovalRules: () => request<ApprovalRule[]>('/admin/approval-rules'),
		createApprovalRule: (body: Omit<ApprovalRule, 'id'>) =>
			request<ApprovalRule>('/admin/approval-rules', { method: 'POST', body: JSON.stringify(body) }),
		updateApprovalRule: (id: string, body: Omit<ApprovalRule, 'id'>) =>
			request<ApprovalRule>(`/admin/approval-rules/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
		deleteApprovalRule: (id: string) => request<void>(`/admin/approval-rules/${id}`, { method: 'DELETE' }),

		listNotifications: () => request<AppNotification[]>('/notifications'),
		unreadNotificationCount: () => request<{ count: number }>('/notifications/unread-count'),
		markNotificationRead: (id: string) => request<{ ok: boolean }>(`/notifications/${id}/read`, { method: 'POST' }),
		markAllNotificationsRead: () => request<{ ok: boolean }>('/notifications/read-all', { method: 'POST' }),

		getNumberSeries: (module: string, field: string) =>
			request<{ prefix: string; pad_width: number; reset_policy: string; next_value: number }>(
				`/admin/number-series/${module}/${field}`
			),
		setNumberSeries: (module: string, field: string, body: { prefix: string; pad_width: number; reset_policy: string }) =>
			request<{ prefix: string; pad_width: number; reset_policy: string; next_value: number }>(
				`/admin/number-series/${module}/${field}`,
				{ method: 'PUT', body: JSON.stringify(body) }
			),

		listDeleted: (module: string) => request<RecordRow[]>(`/data/${module}/deleted`),
		restoreRecord: (module: string, id: string) => request<RecordRow>(`/data/${module}/${id}/restore`, { method: 'POST' }),

		exportRecords: async (module: string) => {
			const res = await fetchImpl(`/api/data/${module}/export`, { method: 'POST', credentials: 'include' });
			if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
			return res.blob();
		},
		importRecords: async (module: string, file: File) => {
			const form = new FormData();
			form.append('file', file);
			const res = await fetchImpl(`/api/data/${module}/import`, { method: 'POST', body: form, credentials: 'include' });
			if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
			return res.json() as Promise<{ created: number; errors: { row: number; error: string }[] }>;
		},

		listReports: () => request<SavedReport[]>('/reports'),
		getReport: (id: string) => request<SavedReport>(`/reports/${id}`),
		createReport: (name: string, definition: ReportDefinition) =>
			request<SavedReport>('/reports', { method: 'POST', body: JSON.stringify({ name, definition }) }),
		updateReport: (id: string, name: string, definition: ReportDefinition) =>
			request<SavedReport>(`/reports/${id}`, { method: 'PUT', body: JSON.stringify({ name, definition }) }),
		deleteReport: (id: string) => request<void>(`/reports/${id}`, { method: 'DELETE' }),
		runReport: (definition: ReportDefinition) =>
			request<Record<string, unknown>[]>('/reports/run', { method: 'POST', body: JSON.stringify(definition) }),
		runSavedReport: (id: string) => request<Record<string, unknown>[]>(`/reports/${id}/run`),

		flowsInto: (module: string) =>
			request<
				{ source_module: string; flow_name: string; header_field_map: Record<string, string>; target_line_relation: string | null }[]
			>(`/document-flow/flows-into/${module}`),
		previewFlowCopy: (sourceModule: string, sourceId: string, flowName: string) =>
			request<{
				header: Record<string, unknown>;
				lines: Record<string, unknown>[];
				/** Untracked child relations copied alongside `lines` (e.g. a GR's
				 * other-charges rows), keyed by the target relation name. */
				extra: Record<string, Record<string, unknown>[]>;
			}>('/document-flow/preview', {
				method: 'POST',
				body: JSON.stringify({ source_module: sourceModule, source_id: sourceId, flow_name: flowName })
			}),
		openFlowLines: (module: string, recordId: string, flowName: string) =>
			request<{ line_id: string; total_qty: number; open_qty: number }[]>(
				`/document-flow/open-lines/${module}/${recordId}?flow=${encodeURIComponent(flowName)}`
			),
		copyDocument: (sourceModule: string, sourceId: string, flowName: string) =>
			request<RecordRow>('/document-flow/copy', {
				method: 'POST',
				body: JSON.stringify({ source_module: sourceModule, source_id: sourceId, flow_name: flowName })
			}),

		trialBalance: (asOfDate: string) =>
			request<TrialBalance>(`/financial-reports/trial-balance?as_of_date=${asOfDate}`),
		balanceSheet: (asOfDate: string) =>
			request<BalanceSheet>(`/financial-reports/balance-sheet?as_of_date=${asOfDate}`),
		incomeStatement: (dateFrom: string, dateTo: string) =>
			request<IncomeStatement>(`/financial-reports/income-statement?date_from=${dateFrom}&date_to=${dateTo}`),
		subledgerReconciliation: (asOfDate: string) =>
			request<SubledgerReconciliation>(`/financial-reports/subledger-reconciliation?as_of_date=${asOfDate}`),

		listWebhooks: () => request<Webhook[]>('/webhooks'),
		createWebhook: (module: string, url: string, events: string[]) =>
			request<Webhook & { secret: string }>('/webhooks', { method: 'POST', body: JSON.stringify({ module, url, events }) }),
		deleteWebhook: (id: string) => request<void>(`/webhooks/${id}`, { method: 'DELETE' }),

		listTokens: () => request<ApiToken[]>('/tokens'),
		createToken: (name: string) => request<ApiToken & { token: string }>('/tokens', { method: 'POST', body: JSON.stringify({ name }) }),
		revokeToken: (id: string) => request<void>(`/tokens/${id}`, { method: 'DELETE' }),

		listFiscalPeriods: () => request<FiscalPeriod[]>('/admin/fiscal-periods'),
		generateFiscalYear: (year: number) =>
			request<FiscalPeriod[]>('/admin/fiscal-periods/generate-year', { method: 'POST', body: JSON.stringify({ year }) }),
		closeFiscalPeriod: (id: string) => request<FiscalPeriod>(`/admin/fiscal-periods/${id}/close`, { method: 'POST' }),
		reopenFiscalPeriod: (id: string) => request<FiscalPeriod>(`/admin/fiscal-periods/${id}/reopen`, { method: 'POST' }),

		listPeriodicRuns: (runType?: string) => request<PeriodicRun[]>(`/periodic-runs${runType ? `?run_type=${runType}` : ''}`),
		triggerPeriodicRun: (runType: string, periodKey: string) =>
			request<PeriodicRun>(`/periodic-runs/${runType}/${periodKey}`, { method: 'POST' }),

		globalSearch: (q: string) =>
			request<{ results: { module: string; module_label: string; id: string; label: string }[] }>(`/search?q=${encodeURIComponent(q)}`),

		inventoryValuation: () => request<InventoryValuation>('/stock/valuation'),
		stockMovements: (itemModule: string, itemId: string, limit = 50) =>
			request<StockMovement[]>(`/stock/movements/${itemModule}/${itemId}?limit=${limit}`),
		aging: (group: 'AP' | 'AR', asOfDate: string) =>
			request<AgingRow[]>(`/financial-reports/aging?group=${group}&as_of_date=${asOfDate}`),
		ledger: (group: 'AP' | 'AR', partyId: string, dateFrom: string, dateTo: string) =>
			request<PartyLedger>(
				`/financial-reports/ledger?group=${group}&party_id=${partyId}&date_from=${dateFrom}&date_to=${dateTo}`
			),

		getAiSettings: () => request<AiSettings>('/admin/ai-settings'),
		saveAiSettings: (
			body: Omit<AiSettings, 'gemini_key_set' | 'openai_key_set' | 'telegram_token_set' | 'telegram_bot_username'> & {
				gemini_api_key?: string;
				openai_api_key?: string;
				telegram_bot_token?: string;
			}
		) => request<AiSettings>('/admin/ai-settings', { method: 'PUT', body: JSON.stringify(body) }),
		listAiModels: (provider: 'gemini' | 'openai', apiKey?: string) =>
			request<{ models: string[] }>('/admin/ai-settings/models', {
				method: 'POST',
				body: JSON.stringify({ provider, api_key: apiKey || undefined })
			}),
		verifyTelegramToken: (token?: string) =>
			request<{ ok: boolean; bot_username: string | null }>('/admin/ai-settings/telegram/verify', {
				method: 'POST',
				body: JSON.stringify({ token: token || undefined })
			}),

		aiChat: (message: string, conversationId?: string) =>
			request<AiChatResponse>('/ai/chat', { method: 'POST', body: JSON.stringify({ message, conversation_id: conversationId }) }),
		aiChatWithImage: (message: string, image: AiChatImage, conversationId?: string) =>
			request<AiChatResponse>('/ai/chat', { method: 'POST', body: JSON.stringify({ message, conversation_id: conversationId, image }) }),

		listAiConversations: () => request<AiConversationSummary[]>('/ai/conversations'),
		getAiConversation: (id: string) => request<AiConversationDetail>(`/ai/conversations/${id}`),
		deleteAiConversation: (id: string) => request<void>(`/ai/conversations/${id}`, { method: 'DELETE' }),

		getTelegramLink: () => request<TelegramLinkStatus>('/telegram/link'),
		generateTelegramLinkCode: () => request<TelegramLinkCodeResult>('/telegram/link-code', { method: 'POST' }),
		unlinkTelegram: () => request<{ ok: boolean }>('/telegram/link', { method: 'DELETE' }),

		listOrgUsers: () => request<OrgUser[]>('/org/users'),
		deactivateOrgUser: (id: string) => request<{ ok: boolean }>(`/org/users/${id}/deactivate`, { method: 'POST' }),
		listOrgInvites: () => request<OrgInvite[]>('/org/invites'),
		createOrgInvite: (email: string, roleName: string) =>
			request<OrgInvite>('/org/invites', { method: 'POST', body: JSON.stringify({ email, role_name: roleName }) }),
		revokeOrgInvite: (id: string) => request<void>(`/org/invites/${id}`, { method: 'DELETE' }),
		getOrgAiSettings: () => request<OrgAiSettings>('/org/ai-settings'),
		saveOrgAiSettings: (
			body: Omit<OrgAiSettings, 'gemini_key_set' | 'openai_key_set'> & { gemini_api_key?: string; openai_api_key?: string }
		) => request<OrgAiSettings>('/org/ai-settings', { method: 'PUT', body: JSON.stringify(body) })
	};
}

/** Client-only default instance — never call this from a `load` function. */
export const api = createApi();
