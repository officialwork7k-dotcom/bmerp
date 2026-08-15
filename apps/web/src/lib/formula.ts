// Client-side mirror of apps/api domain/formulas.py — used only to preview a
// computed field's value as the user types; the server recomputes
// authoritatively on save.

type Token = { kind: 'num' | 'name' | 'op' | 'lparen' | 'rparen'; value: string };

function tokenize(expr: string): Token[] {
	const tokens: Token[] = [];
	const re = /\s*(?:([0-9]+(?:\.[0-9]+)?)|([A-Za-z_][A-Za-z0-9_]*)|([+\-*/])|(\()|(\)))/g;
	let match: RegExpExecArray | null;
	let pos = 0;
	while (pos < expr.length) {
		re.lastIndex = pos;
		match = re.exec(expr);
		if (!match || match.index !== pos) break;
		pos = re.lastIndex;
		if (match[1]) tokens.push({ kind: 'num', value: match[1] });
		else if (match[2]) tokens.push({ kind: 'name', value: match[2] });
		else if (match[3]) tokens.push({ kind: 'op', value: match[3] });
		else if (match[4]) tokens.push({ kind: 'lparen', value: '(' });
		else if (match[5]) tokens.push({ kind: 'rparen', value: ')' });
	}
	return tokens;
}

export function evaluate_formula_safe(expression: string, values: Record<string, unknown>): string {
	try {
		const tokens = tokenize(expression);
		let i = 0;

		function parseExpr(): number {
			let left = parseTerm();
			while (tokens[i]?.kind === 'op' && (tokens[i].value === '+' || tokens[i].value === '-')) {
				const op = tokens[i++].value;
				const right = parseTerm();
				left = op === '+' ? left + right : left - right;
			}
			return left;
		}
		function parseTerm(): number {
			let left = parseFactor();
			while (tokens[i]?.kind === 'op' && (tokens[i].value === '*' || tokens[i].value === '/')) {
				const op = tokens[i++].value;
				const right = parseFactor();
				left = op === '*' ? left * right : right === 0 ? 0 : left / right;
			}
			return left;
		}
		function parseFactor(): number {
			const tok = tokens[i];
			if (!tok) throw new Error('unexpected end');
			if (tok.kind === 'num') {
				i++;
				return Number(tok.value);
			}
			if (tok.kind === 'name') {
				i++;
				const raw = values[tok.value];
				return raw === undefined || raw === null || raw === '' ? 0 : Number(raw);
			}
			if (tok.kind === 'lparen') {
				i++;
				const v = parseExpr();
				if (tokens[i]?.kind === 'rparen') i++;
				return v;
			}
			throw new Error('unexpected token');
		}

		return String(parseExpr());
	} catch {
		return '';
	}
}
