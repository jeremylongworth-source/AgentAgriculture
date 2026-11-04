"""One checked domain-helper path shared by CLI and scenario evaluator."""
import hashlib
import json
from router.core import Catalog
from . import crop, season, livestock, resources, harvest, business
from .common import validate

RUNNERS={'season-work-planning':season.run,'crop-production-review':crop.run,'livestock-record-review':livestock.run,'resource-team-coordination':resources.run,'harvest-storage-delivery':harvest.run,'business-stewardship-review':business.run}

def build(context,data,catalog=None):
    catalog=catalog or Catalog()
    route=catalog.route(context)
    if route['state']!='ready_for_preparation' or context['intent']=='explain':
        return {'route':route,'data_read':False}
    if not isinstance(data,dict):
        raise ValueError('workflow.object_required')
    if context['workflow'] not in RUNNERS:
        raise ValueError('workflow.helper_unavailable')
    for key in ['task_id','enterprise_id','jurisdiction','period']:
        if data.get(key)!=context[key]:
            raise ValueError('workflow.context_mismatch')
    if context['evidence_kind']!='synthetic' or data.get('synthetic_only') is not True:
        raise ValueError('workflow.synthetic_helper_only')
    result=RUNNERS[context['workflow']](data,context['language'],catalog.root)
    result['parsed_input_sha256']=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    result['catalog_sha256']=route['catalog_sha256']
    validate('workflow-result',result,catalog.root)
    return result
