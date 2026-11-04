"""Run a bounded synthetic workflow helper after explicit context routing."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from router.core import Catalog, read_document
from workflow_tools.execute import RUNNERS, build
from workflow_tools.render import markdown


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context',required=True,type=Path)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--format',choices=['json','markdown'],default='json')
    args=parser.parse_args()
    try:
        context=read_document(args.context);catalog=Catalog();route=catalog.route(context)
        if route['state']!='ready_for_preparation' or context['intent']=='explain':
            print(json.dumps({'route':route,'data_read':False},ensure_ascii=False,indent=2));return 0
        if context['workflow'] not in RUNNERS or args.input is None:
            raise ValueError('workflow.helper_or_input_unavailable')
        data=read_document(args.input)
        result=build(context,data,catalog)
        print(markdown(result) if args.format=='markdown' else json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
        return 0
    except (OSError,ValueError,TypeError,RecursionError) as error:
        code=str(error).split(':',1)[0]
        code=code if code.startswith(('workflow.','season.','crop.','document.')) else 'workflow.input_or_scope'
        print(json.dumps({'state':'input_invalid','code':code,'detail':type(error).__name__}),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
