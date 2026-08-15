<script lang="ts">
	import { createSearchController, type LookupOption } from '$lib/lookup';

	let {
		module,
		initialValue,
		initialLabel,
		initialQuery = '',
		filters,
		commit,
		cancel
	}: {
		module: string;
		initialValue: string | null;
		initialLabel: string;
		initialQuery?: string;
		/** Narrows candidates to rows matching a sibling field already
		 * selected — see FieldMetadata.lookup_filter. */
		filters?: Record<string, string>;
		commit: (value: string | null, label: string) => void;
		cancel: () => void;
	} = $props();

	// svelte-ignore state_referenced_locally -- intentional one-time seed from the initial prop
	let query = $state(initialQuery);
	let options = $state<LookupOption[]>([]);
	let loading = $state(false);
	let activeIndex = $state(0);
	let inputEl: HTMLInputElement;

	// Race-safe: cancels the previous request (timer + in-flight fetch)
	// before starting a new one, so typing faster than the debounce window
	// can never let an earlier, shorter query's response land after a
	// later one's and silently regress the list. See createSearchController's
	// own docstring for the full "why" — this exact component is what
	// surfaced the bug.
	const searchController = createSearchController(200);
	$effect(() => {
		searchController.run(
			module,
			query,
			(results) => {
				options = results;
				// Clamped, not reset to a fixed 0 — a still-in-range activeIndex
				// (e.g. the user already arrowed down to match 2 of 5, then kept
				// typing to narrow the list to 3) shouldn't jump back to the top
				// of the list on every keystroke; it only needs correcting when
				// the new list is shorter than where the cursor was.
				activeIndex = options.length === 0 ? 0 : Math.min(activeIndex, options.length - 1);
			},
			(l) => (loading = l),
			filters
		);
	});
	$effect(() => () => searchController.dispose());

	export function focus() {
		inputEl?.focus();
		inputEl?.select();
	}

	function selectActive() {
		// Defensive clamp — activeIndex should never be out of range by this
		// point, but a negative index silently no-ops here instead of
		// throwing, so it's worth being sure rather than relying on every
		// call site upstream to have gotten the clamping right.
		const opt = options[Math.max(0, Math.min(activeIndex, options.length - 1))];
		if (opt) commit(opt.value, opt.label);
		else if (query.trim() === '') commit(null, '');
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			// `options.length - 1` is -1 while a search is still pending (the
			// user typed and immediately pressed Down before the debounced
			// result arrived) — clamping the floor to 0 as well as the
			// ceiling stops activeIndex from going negative and getting
			// stuck there, which silently broke Enter (`options[-1]` is
			// `undefined`, not the last item) for anyone who didn't pause to
			// let the list load first.
			activeIndex = options.length === 0 ? 0 : Math.min(activeIndex + 1, options.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			activeIndex = Math.max(activeIndex - 1, 0);
		} else if (e.key === 'Enter') {
			e.preventDefault();
			selectActive();
		} else if (e.key === 'Escape') {
			e.preventDefault();
			cancel();
		} else if (e.key === 'Tab') {
			// Commit whatever's highlighted, then let the grid's default
			// tab-to-next-cell behavior proceed — don't preventDefault.
			selectActive();
		}
	}
</script>

<div class="w-72 rounded-md border border-neutral-200 bg-white p-1 shadow-lg dark:border-neutral-700 dark:bg-neutral-900">
	<input
		bind:this={inputEl}
		bind:value={query}
		onkeydown={onKeydown}
		class="mb-1 h-8 w-full border-b border-neutral-200 px-2 text-sm outline-none dark:border-neutral-700 dark:bg-neutral-900"
		placeholder="Search…"
		role="combobox"
		aria-expanded="true"
		aria-controls="lookup-editor-listbox"
		aria-autocomplete="list"
		aria-activedescendant={options[activeIndex] ? `lookup-opt-${activeIndex}` : undefined}
	/>
	<ul id="lookup-editor-listbox" role="listbox" class="max-h-56 overflow-y-auto">
		{#if loading}
			<li class="px-2 py-1.5 text-sm text-neutral-500">Loading…</li>
		{:else if options.length === 0}
			<li class="px-2 py-1.5 text-sm text-neutral-500">No matches</li>
		{/if}
		{#each options as opt, i (opt.value)}
			<li id={`lookup-opt-${i}`} role="option" aria-selected={i === activeIndex}>
				<button
					type="button"
					class="block w-full truncate rounded px-2 py-1.5 text-left text-sm {i === activeIndex
						? 'bg-primary-50 dark:bg-primary-950'
						: 'hover:bg-neutral-100 dark:hover:bg-neutral-800'}"
					onmouseenter={() => (activeIndex = i)}
					onclick={() => commit(opt.value, opt.label)}
				>
					{opt.label}
				</button>
			</li>
		{/each}
	</ul>
</div>
