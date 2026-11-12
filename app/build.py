#!/usr/bin/env python3
"""Rebuild index.html from data/monarch-2026.json + the template pieces in src/.

Run:  python3 build.py
Then open index.html in a browser. Everything (font, data, code) ends up inside that one file.
"""
import json, re, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)

data = json.load(open(P('data', 'monarch-2026.json'), encoding='utf-8'))
YEAR = 2026
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
ACTUAL_THROUGH = 9  # Oct is the last closed month; Nov and Dec come from the Monarch budget

# ---------- category lookup ----------
cat = {}      # id -> (name, icon, group)
by_name = {}  # (group, name) -> id
for g in data['cats']['category_groups']:
    for c in g['categories']:
        cat[c['id']] = (c['name'], c['icon'], g['name'])
        by_name[(g['name'], c['name'])] = c['id']

TRANSFER_GROUPS = {'Transfers'}

# ---------- where each Monarch category lands in the P&L ----------
# tab key, section name, P&L map
def place(cid):
    name, icon, grp = cat[cid]
    if grp == 'Income':
        if icon == '\U0001F501': return ('income', 'Retainers', 'retainers')
        if icon == '☝️': return ('income', 'One-offs', 'oneoffs')
        if icon == '\U0001F47B': return ('income', 'Past clients', 'retainers')
        if icon == '\U0001F3AF': return ('income', 'Projected', 'pipe_oneoffs')
        return ('income', 'Other income', 'oneoffs')
    person = icon.startswith('\U0001F64B')
    if grp == 'Operations':
        return ('ops', 'Team', 'planilla') if person else ('ops', 'Software', 'software')
    if grp == 'Growth':
        return ('mkt', 'Team', 'marketing') if person else ('mkt', 'Tools and ads', 'marketing')
    if grp == 'Admin':
        return ('admin', 'Team', 'admin') if person else ('admin', 'Tools and office', 'admin')
    if grp == 'Debt':
        return ('debt', 'Cards and loans', 'debt')
    if grp == 'Other':
        if name == 'Fees': return ('tax', 'Bank and card fees', 'taxes')
        if name == 'Profits': return ('founders', 'Owner payouts', 'founders')
        if name == 'Travel': return ('unc', 'Travel', 'fixed_unc')
        return ('unc', 'Uncategorized', 'fixed_unc')
    return ('unc', 'Uncategorized', 'fixed_unc')

TABS = [('income', 'Income'), ('ops', 'Operations'), ('mkt', 'Marketing'), ('admin', 'Admin'),
        ('debt', 'Debt'), ('tax', 'Taxes & fees'), ('founders', 'Founders'), ('unc', 'Uncategorized')]
SECTION_ORDER = ['Retainers', 'One-offs', 'Past clients', 'Other income', 'Projected', 'Team', 'Software',
                 'Tools and ads', 'Tools and office', 'Cards and loans', 'Bank and card fees', 'Owner payouts',
                 'Travel', 'Uncategorized']

# ---------- actuals from transactions ----------
vals = collections.defaultdict(lambda: [0.0] * 12)
txs = []
for t in data['tx']:
    cid = t['category_id']
    if cid not in cat or cat[cid][2] in TRANSFER_GROUPS:
        continue
    m = int(t['date'][5:7]) - 1
    if int(t['date'][:4]) != YEAR or m > ACTUAL_THROUGH:
        continue
    sign = 1 if cat[cid][2] == 'Income' else -1      # costs shown as positive numbers, like the sheet
    vals[cid][m] += sign * t['amount']
    txs.append([t['date'], t['merchant'], cid, round(sign * t['amount'], 2), t['account']])

# ---------- forecast from the Monarch budget ----------
for b in data['bud']['data']:
    m = int(b['month'][5:7]) - 1
    if m <= ACTUAL_THROUGH:
        continue
    cid = by_name.get((b['category_group'], b['category']))
    if cid:
        vals[cid][m] += b['budget_amount']

# ---------- planned numbers: the Monarch budget for every month ----------
plan = collections.defaultdict(lambda: [0.0] * 12)
for b in list(data.get('bud_ytd', {}).get('data', [])) + list(data['bud']['data']):
    cid = by_name.get((b['category_group'], b['category']))
    if cid and int(b['month'][:4]) == YEAR:
        plan[cid][int(b['month'][5:7]) - 1] = b['budget_amount']

# ---------- assemble tabs (same rows for both views so they line up) ----------
cat_tab = {}
keep = []
for cid, (name, icon, grp) in cat.items():
    if grp in TRANSFER_GROUPS:
        continue
    has = any(abs(v) > 0.004 for v in vals.get(cid, [])) or any(abs(v) > 0.004 for v in plan.get(cid, []))
    tk, sec, mp = place(cid)
    if not has and mp != 'pipe_oneoffs':
        continue                      # skip empty and disabled categories, keep the projected lines to type into
    cat_tab[cid] = tk
    keep.append(cid)

def make_tabs(src):
    tabs = {k: collections.OrderedDict() for k, _ in TABS}
    for cid in keep:
        tk, sec, mp = place(cid)
        tabs[tk].setdefault((sec, mp), []).append([cat[cid][0], [round(v, 2) for v in src.get(cid, [0.0] * 12)], cid])
    out = []
    for k, label in TABS:
        secs = sorted(tabs[k].items(), key=lambda kv: SECTION_ORDER.index(kv[0][0]))
        sections = []
        for (sec, mp), rows in secs:
            rows.sort(key=lambda r: (-sum(plan.get(r[2], [0] * 12)) - sum(vals.get(r[2], [0] * 12)[:ACTUAL_THROUGH + 1]), r[0]))
            sections.append({'name': sec, 'map': mp, 'rows': [r[:2] for r in rows]})
        if not sections:
            sections = [{'name': label, 'map': {'tax': 'taxes', 'debt': 'debt', 'unc': 'fixed_unc'}.get(k, k), 'rows': []}]
        out.append({'key': k, 'name': label, 'sections': sections})
    return out

D_tabs_actual = make_tabs(vals)   # Feb to Oct from transactions, Nov and Dec from the budget
D_tabs_plan = make_tabs(plan)     # every month from the Monarch budget, same numbers as the Budget view
D_tabs = D_tabs_plan

acc = data['acc']
cash_accts = [a for a in acc['accounts'] if a['type'] != 'Credit Card']
card_accts = [a for a in acc['accounts'] if a['type'] == 'Credit Card']

D = {
    'months': MONTHS, 'actualThrough': ACTUAL_THROUGH, 'year': YEAR,
    'tabs': D_tabs,
    'tabsPlan': D_tabs_plan,
    'tabsActual': D_tabs_actual,
    'pl': [
        {'name': 'Income', 'rows': [['One-offs', 'oneoffs', 'oneoffs', 'income'], ['Retainers', 'retainers', 'retainers', 'income']]},
        {'name': 'Cost of delivery', 'rows': [['Team', 'team', 'planilla', 'ops'], ['Software', 'software', 'software', 'ops']]},
        {'name': 'Fixed costs', 'rows': [['Admin', 'admin', 'admin', 'admin'], ['Marketing', 'marketing', 'marketing', 'mkt'],
                                         ['Taxes & fees', 'taxes', 'taxes', 'tax'], ['Owner payouts', 'payouts', 'founders', 'founders'],
                                         ['Debt', 'debt', 'debt', 'debt'], ['Uncategorized', 'unc', 'fixed_unc', 'unc']]},
    ],
    'feeds': {'oneoffs': 'One-offs', 'retainers': 'Retainers', 'pipe_oneoffs': 'Pipeline', 'pipe_retainers': 'Pipeline',
              'planilla': 'Team (delivery)', 'software': 'Software (delivery)', 'marketing': 'Marketing', 'admin': 'Admin',
              'debt': 'Debt', 'taxes': 'Taxes & fees', 'founders': 'Owner payouts', 'fixed_unc': 'Uncategorized (fixed)'},
    'owners': {'income': 'David Arrué', 'ops': 'Jonathan', 'mkt': 'Meybell Morales', 'admin': 'Jimena Resinos',
               'debt': 'Jeffrey', 'tax': 'Jeffrey', 'founders': 'Jeffrey', 'unc': 'Jeffrey'},
    'team': ['Jonathan', 'David Arrué', 'Meybell Morales', 'Jimena Resinos', 'Jeffrey', 'Ana Lucía Martínez Shi'],
    'admin': 'Andrés',
    'cash': {'label': 'today, from Monarch',
             'onHand': round(sum(a['balance'] for a in cash_accts), 2),
             'card': round(-sum(a['balance'] for a in card_accts), 2),
             'net': round(acc['total_balance'], 2),
             'accounts': [[a['name'], a['balance']] for a in acc['accounts']]},
    'tx': sorted(txs, key=lambda x: x[0], reverse=True),
    'txcat': {cid: [cat[cid][0], cat[cid][1], cat_tab.get(cid, 'unc')] for cid in {t[2] for t in txs}},
}

# ---------- budget view: Monarch budget per category per month + what was actually paid ----------
GROUP_ORDER = ['Income', 'Growth', 'Operations', 'Admin', 'Debt', 'Other', 'Transfers']
bud_rows = list(data.get('bud_ytd', {}).get('data', [])) + list(data['bud']['data'])
budget = collections.defaultdict(dict)   # 'YYYY-MM' -> {cid: amount}
for b in bud_rows:
    cid = by_name.get((b['category_group'], b['category']))
    if cid and b['budget_amount']:
        budget[b['month'][:7]][cid] = b['budget_amount']
D['budget'] = budget
D['cats'] = {cid: [n, g] for cid, (n, ic, g) in cat.items()}
D['groups'] = GROUP_ORDER
# every transaction, transfers included, raw Monarch sign (money in positive, money out negative)
D['atx'] = [[t['date'], t['merchant'], t['category_id'], t['amount'], t['account_id']]
            for t in sorted(data['tx'], key=lambda x: x['date'], reverse=True) if t['date'][:4] == str(YEAR)]

# ---------- accounts view ----------
hist = collections.defaultdict(list)
for snap in (data.get('nw') or {}).get('snapshots', []):
    for ab in snap['account_balances']:
        hist[ab['account_id']].append([snap['date'], ab['balance']])
D['accounts'] = [{'id': a['id'], 'name': a['name'], 'type': a['type'], 'balance': a['balance'],
                  'group': 'Credit cards' if a['type'] == 'Credit Card' else 'Cash',
                  'hist': hist.get(a['id'], [])} for a in acc['accounts']]
D['nw'] = [[s['date'], s['net_worth'], s['assets_balance'], s['liabilities_balance']]
           for s in (data.get('nw') or {}).get('snapshots', [])]
D['today'] = '2026-11-11'
# ---------- daily balances: walk each account's transactions back from today's balance ----------
daily = {}
snaps = (data.get('nw') or {}).get('snapshots', [])
for a in acc['accounts']:
    tx = [t for t in data['tx'] if t['account_id'] == a['id']]
    if not tx:   # no transactions: use the monthly balance readings
        daily[a['id']] = [[sn['date'], ab['balance']] for sn in snaps for ab in sn['account_balances'] if ab['account_id'] == a['id']]
        continue
    by = collections.defaultdict(float)
    for t in tx: by[t['date']] += t['amount']
    pts, b = [[D['today'], a['balance']]], a['balance']
    for day in sorted(by, reverse=True):
        if day < D['today']: pts.append([day, round(b, 2)])
        b -= by[day]
    first = min(by)
    prev = (collections.datetime if False else None)
    pts.append([first[:8] + '01' if first[8:] != '01' else first, round(b, 2)])   # opening balance before the first transaction
    daily[a['id']] = sorted({p[0]: p for p in pts}.values())
D['daily'] = daily


# ---------- stitch the page ----------
tpl = open(P('src', 'template.html'), encoding='utf-8').read()
out = (tpl.replace('__DATA__', json.dumps(D, ensure_ascii=False, separators=(',', ':')))
          .replace('__GEIST__', open(P('src', 'geist.b64')).read().strip())
          .replace('__AVATAR__', open(P('src', 'avatar.b64')).read().strip())
          .replace('__DSLOGO__', open(P('src', 'ds-logo.b64')).read().strip()))
open(os.path.join(HERE, '..', 'public', 'index.html'), 'w', encoding='utf-8').write(out)

# quick totals so the numbers can be checked against Monarch
inc = sum(sum(r[1][:ACTUAL_THROUGH + 1]) for s in D_tabs_actual[0]['sections'] for r in s['rows'])
cost = sum(sum(r[1][:ACTUAL_THROUGH + 1]) for t in D_tabs_actual[1:] for s in t['sections'] for r in s['rows'])
pin = [sum(r[1][m] for s in D_tabs_plan[0]['sections'] for r in s['rows']) for m in range(12)]
pex = [sum(r[1][m] for t in D_tabs_plan[1:] for s in t['sections'] for r in s['rows']) for m in range(12)]
print('Budgeted income by month  ', [round(x) for x in pin])
print('Budgeted expenses by month', [round(x) for x in pex])
print('public/index.html written, %d transactions' % len(txs))
print('Jan-Oct income  %.2f' % inc)
print('Jan-Oct costs   %.2f' % cost)
print('Jan-Oct net     %.2f' % (inc - cost))
