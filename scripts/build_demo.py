from pathlib import Path
import json
from portfolio.gamepulse import analytics,load
folder=Path('data/gamepulse'); output=Path('docs/data');output.mkdir(parents=True,exist_ok=True)
summary=json.loads((folder/'summary.json').read_text())
events=load(folder/'telemetry.sqlite')
for platform in ['all','mobile','desktop','console']:
 result={**summary}
 if platform!='all':result['analytics']=analytics(events,platform=platform)
 (output/(platform+'.json')).write_text(json.dumps(result))
