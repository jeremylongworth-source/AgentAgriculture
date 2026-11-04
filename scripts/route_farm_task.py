"""Route one explicitly supplied task-context JSON; perform no farm/external action."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from router.core import Catalog, read_document

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = Catalog().route(read_document(args.context))
    except (OSError, ValueError, TypeError, RecursionError) as error:
        # Never echo imported content or a full document in diagnostics.
        print(json.dumps({'state': 'input_invalid', 'code': 'route.document_or_catalog', 'detail': type(error).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 2 if result['state'] == 'input_invalid' else 0

if __name__ == '__main__':
    raise SystemExit(main())
