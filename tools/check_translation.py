"""Validate English row coverage, formatting tokens and glyph coverage.

Read-only by default. --write saves an ignored report. --complete also fails
when a source row has no translation decision. Review rows are tracked,
not silently treated as proofread.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONTROL = re.compile(r'@(?:RS|[0-9]+r|[A-Z]r)')
PRINTF = re.compile(r'%(?:[1-9]\d*\$)?[-+#0 \']*(?:\d+|\*(?:\d+\$)?)?(?:\.(?:\d+|\*(?:\d+\$)?))?(?:hh|ll|[hljztL])?[diuoxXfFeEgGaAcspn%]')
JAPANESE_PROSE = re.compile(r'[\u3041-\u3096\u30a1-\u30fa\u3400-\u9fff\uff66-\uff9f]')


def read_sources():
    result = {}
    for name in ('events', 'executable', 'trophies', 'dungeons', 'ui_literals'):
        for row in json.loads((ROOT/'work/translation/ja'/(name+'.json')).read_text(encoding='utf8')):
            if row['id'] in result:
                raise ValueError('Duplicate source ID')
            result[row['id']] = dict(row, source=name)
    for path in sorted((ROOT/'work/translation/ja/databases').glob('*.json')):
        name=path.stem
        for row in json.loads(path.read_text(encoding='utf8')):
            if row['id'] in result:
                raise ValueError('Duplicate database source ID')
            result[row['id']]=dict(row,source='databases/'+name)
    return result


def read_english():
    result = {}
    paths = [p for name in ('events','executable','trophies','dungeons','ui_literals')
             for p in (ROOT/'work/translation/en'/name).glob('*.en.json')]
    paths += list((ROOT/'work/translation/en/databases').rglob('*.en.json'))
    for path in sorted(paths):
        doc = json.loads(path.read_text(encoding='utf8'))
        rows = doc.get('translations', [])
        if doc.get('rows_in_slice') != len(rows) or doc.get('rows_examined', 0) < len(rows):
            raise ValueError('Invalid slice accounting: '+str(path))
        for row in rows:
            if row['id'] in result:
                raise ValueError('Duplicate English ID '+row['id'])
            result[row['id']] = dict(row, output_file=path.relative_to(ROOT).as_posix())
    return result


def validate(sources, english):
    errors, reviews = [], []
    for key, row in english.items():
        if key not in sources:
            errors.append(dict(id=key, error='Unknown source ID'))
            continue
        src = sources[key]['ja']
        status, en = row.get('status'), row.get('en')
        if status == 'exclude':
            if en is not None or not row.get('note'):
                errors.append(dict(id=key, error='Exclusion requires null English and a reason'))
            continue
        if status not in ('translated', 'review') or not isinstance(en, str) or not en:
            errors.append(dict(id=key, error='Invalid translation/status'))
            continue
        patterns = [('controls', CONTROL)]
        # A percentage in ordinary English prose can resemble a printf token
        # ("100% of"). Check format arguments when the source is a format string.
        if PRINTF.findall(src):
            patterns.append(('printf', PRINTF))
        for label, pattern in patterns:
            if pattern.findall(src) != pattern.findall(en):
                errors.append(dict(id=key, error=label+' changed', source_tokens=pattern.findall(src), english_tokens=pattern.findall(en)))
        if src.count('\n') != en.count('\n'):
            errors.append(dict(id=key, error='Newline count changed', source_count=src.count('\n'), english_count=en.count('\n')))
        if '\0' in en:
            errors.append(dict(id=key, error='Embedded NUL'))
        from executable_context import reference_overrides
        try:
            overrides = reference_overrides(sources[key], row)
        except ValueError as exc:
            errors.append(dict(id=key, error=str(exc)))
            overrides = {}
        for pointer, override in overrides.items():
            for label, pattern in patterns:
                if pattern.findall(src) != pattern.findall(override['en']):
                    errors.append(dict(id=key, pointer_offset=hex(pointer), error=label+' changed in reference translation'))
            if src.count('\n') != override['en'].count('\n'):
                errors.append(dict(id=key, pointer_offset=hex(pointer), error='Newline count changed in reference translation'))
            if JAPANESE_PROSE.search(override['en']):
                reviews.append(dict(id=key, pointer_offset=hex(pointer), issue='Japanese glyphs retained in reference translation'))
        if 'display' in row:
            display=row['display']
            if not isinstance(display,str) or not display or '\0' in display or '\n' in display or JAPANESE_PROSE.search(display):
                errors.append(dict(id=key,error='Invalid compact display label'))
        if JAPANESE_PROSE.search(en):
            reviews.append(dict(id=key, issue='Japanese glyphs retained', output_file=row['output_file']))
        if status == 'review':
            reviews.append(dict(id=key, issue=row.get('note') or 'Meaning/context review required', output_file=row['output_file']))
    from executable_context import collect_reference_overrides
    try:
        collect_reference_overrides(sources, english)
    except ValueError as exc:
        errors.append(dict(error=str(exc)))
    stats = {}
    for source in dict.fromkeys(v['source'] for v in sources.values()):
        ids = [k for k, v in sources.items() if v['source']==source]
        count = Counter(english[k]['status'] if k in english else 'missing' for k in ids)
        stats[source] = dict(total=len(ids), **count)
    return dict(rows=len(sources), decisions=len(english), missing=[k for k in sources if k not in english],
                by_source=stats, errors=errors, review_count=len(reviews), reviews=reviews,
                note='Draft coverage is not a complete-game or in-game verification claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    report = validate(read_sources(), read_english())
    print(json.dumps({k:v for k,v in report.items() if k not in ('reviews','missing','errors')}, indent=2))
    print('Errors:', len(report['errors']))
    print(json.dumps(report['errors'][:30], indent=2))
    print('Missing:', len(report['missing']), 'Review flags:', report['review_count'])
    if args.write:
        out = ROOT/'work/output/translation'
        out.mkdir(parents=True, exist_ok=True)
        (out/'validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    else:
        print('Dry run: no files written.')
    if report['errors'] or args.complete and report['missing']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
