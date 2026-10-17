"""Summarize the current extracted corpus without copying Japanese prose.

Read-only by default. --write saves an English-only census snapshot.
"""
import argparse
from collections import Counter
import json
from check_translation import ROOT, read_sources, read_english, validate


def report():
    sources, english = read_sources(), read_english()
    validation = validate(sources, english)
    groups = {}
    for group in dict.fromkeys(r['source'] for r in sources.values()):
        rows = [r for r in sources.values() if r['source'] == group]
        groups[group] = dict(rows=len(rows), occurrences=sum(len(r['occurrences']) for r in rows))
    statuses = Counter(r['status'] for r in english.values())
    reused = sum(isinstance(r.get('provenance'), dict) and
                 r['provenance'].get('match') == 'exact Japanese source text'
                 for r in english.values())
    return dict(target='NPJB00162', date='2026-10-17',
                source_rows=len(sources), occurrences=sum(v['occurrences'] for v in groups.values()),
                distinct_source_strings=len({r['ja'] for r in sources.values()}),
                groups=groups, decisions=len(english), statuses=dict(statuses),
                exact_source_reused=reused, new_decisions=len(english)-reused,
                english_drafts=sum(r['en'] is not None for r in english.values()),
                missing=len(validation['missing']), errors=len(validation['errors']),
                review_notices=validation['review_count'],
                limits=['Rows are deduplicated within sources; occurrences are stored uses, not screen lines.',
                        'Executable candidates include internal/parser exclusions.',
                        'Movie captions and image regions are counted separately.',
                        'This inventory does not establish full-game runtime coverage.'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write', action='store_true')
    args = p.parse_args()
    result = report()
    print(json.dumps(result, indent=2))
    if args.write:
        folder = ROOT/'work/output/text_census'
        folder.mkdir(parents=True, exist_ok=True)
        (folder/'corpus.en.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    else:
        print('Dry run: nothing written.')


if __name__ == '__main__':
    main()
