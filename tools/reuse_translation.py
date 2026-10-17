"""Match exact source text to the neighboring project; dry run by default.

Row IDs are edition-specific. Never copy translations by row number or transfer
binary pointers. Existing uncertainty and provenance remain attached.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_sources(root):
    base = root / 'work/translation/ja'
    paths = [base / (name + '.json') for name in ('events', 'executable', 'trophies')]
    paths += sorted((base / 'databases').glob('*.json'))
    return {p.relative_to(base).with_suffix('').as_posix(): json.loads(p.read_text(encoding='utf8')) for p in paths}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, default=ROOT.parent/'Wizardry Prisoners of the Lost City')
    p.add_argument('--write', action='store_true')
    args = p.parse_args()
    old = read_sources(args.reference)
    decisions = {}
    for path in (args.reference/'work/translation/en').rglob('*.en.json'):
        doc = json.loads(path.read_text(encoding='utf8'))
        for row in doc.get('translations', []):
            decisions[row['id']] = row
    lookup = defaultdict(list)
    for group, rows in old.items():
        for row in rows:
            if row['id'] in decisions:
                lookup[(group, row['ja'])].append(decisions[row['id']])
    summary, missing = {}, {}
    for group, rows in read_sources(ROOT).items():
        source_group = 'databases/' + group.split('_')[-1] if group.startswith('databases/addtable') else group
        translated, unresolved = [], []
        for row in rows:
            matches = lookup.get((source_group, row['ja']), [])
            if not matches:
                unresolved.append(row)
                continue
            if len({(r['en'], r['status']) for r in matches}) != 1:
                unresolved.append(row)
                continue
            result = dict(matches[0], id=row['id'])
            result.pop('ja', None)
            result['provenance'] = dict(project=args.reference.name, source_id=matches[0]['id'], match='exact Japanese source text', context_review='Inherited draft; edition-specific occurrences require review')
            translated.append(result)
        summary[group] = dict(total=len(rows), reused=len(translated), remaining=len(unresolved))
        missing[group] = unresolved
        if args.write:
            folder = ROOT/'work/translation/en'/group
            folder.mkdir(parents=True, exist_ok=True)
            existing = {r['id'] for file in folder.glob('*.en.json') for r in json.loads(file.read_text(encoding='utf8')).get('translations', [])}
            if existing:
                raise ValueError('Destination already contains decisions: '+group)
            for start in range(0, len(rows), 80):
                ids = {r['id'] for r in rows[start:start+80]}
                selected = [r for r in translated if r['id'] in ids]
                if selected:
                    doc = dict(rows_in_slice=len(selected), rows_examined=len(selected), provenance='Exact source matches imported; no new contextual review claimed', translations=selected)
                    (folder/('%04d.en.json'%start)).write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(summary, indent=2))
    print('Totals:', dict(Counter({k:sum(g[k] for g in summary.values()) for k in ('total','reused','remaining')})))
    if args.write:
        out=ROOT/'work/output/translation'
        out.mkdir(parents=True, exist_ok=True)
        (out/'reuse.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf8')
        (out/'remaining.ja.json').write_text(json.dumps(missing, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    else:
        print('Dry run: no writes. Exact matches retain review flags and provenance.')


if __name__ == '__main__':
    main()
