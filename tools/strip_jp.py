"""Prepare English-only translation copies; read-only validation by default.

--write removes source/context fields from JSON documents in the English tree.
The Japanese export is never edited. Existing English-only files are unchanged.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_KEYS = {'ja', 'jp', 'japanese', 'source_text', 'contexts', 'occurrences'}


def clean(value):
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {k:clean(v) for k,v in value.items() if k not in SOURCE_KEYS}
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    count = changes = 0
    for path in sorted((ROOT/'work/translation/en').rglob('*.en.json')):
        doc = json.loads(path.read_text(encoding='utf8'))
        result = clean(doc)
        count += 1
        if result != doc:
            changes += 1
            print('Remove source fields:', path.relative_to(ROOT))
            if args.write:
                path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print('English files:', count, 'requiring field removal:', changes)
    print('Updated source-free copies.' if args.write else 'Dry run: nothing changed.')


if __name__ == '__main__':
    main()
