#!/usr/bin/env python3
from __future__ import annotations
import base64,csv,gzip,hashlib,io,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
EXPECTED_CATS={'CAMERA_OPEN':1,'SESSION_CREATE':2,'SESSION_PARAMETER':2,'OUTPUT_CONFIGURATION':23,'REQUEST_BUILD':39,'REQUEST_TARGET':134,'REPEATING':8,'CAPTURE_SUBMIT':42,'SESSION_CONTROL':12,'IMAGE_READER':94}
EXPECTED_APIS={'openCamera':1,'createCaptureSession':1,'createCaptureSessionByOutputConfigurations':1,'setSessionParameters':1,'setInputConfiguration':1,'createCaptureRequest':25,'createReprocessCaptureRequest':14,'setPhysicalCameraId':12,'createHighSpeedRequestList':2,'setRepeatingRequest':4,'setRepeatingBurst':2,'capture':25,'captureBurst':17,'finalizeOutputConfigurations':5}
def load(root=ROOT):
 b=root/'data/apk/nothing-camera-camera2-setup';i=json.loads((b/'index.v1.json').read_text())
 core_encoded=''.join((b/n).read_text().strip() for n in i['parts']['core'])
 if len(core_encoded)!=i['coreEncoding']['concatenatedCharacters'] or hashlib.sha256(core_encoded.encode()).hexdigest()!=i['coreEncoding']['encodedSha256']:raise ValueError('core encoding integrity drift')
 c=json.loads(gzip.decompress(base64.b64decode(core_encoded)).decode())
 encoded=''.join((b/n).read_text().strip() for n in i['parts']['operations'])
 if len(encoded)!=i['encoding']['concatenatedCharacters'] or hashlib.sha256(encoded.encode()).hexdigest()!=i['encoding']['encodedSha256']:raise ValueError('operation encoding integrity drift')
 text=gzip.decompress(base64.b64decode(encoded)).decode();rows=list(csv.DictReader(io.StringIO(text),delimiter='\t'))
 return i,c,rows
def validate(v,root=ROOT):
 i,c,rows=v;s=i['summary']
 if (i.get('schemaVersion'),i.get('issue'),i.get('referenceVersion'))!=(1,34,'2026.08.04-1') or i.get('status')!='COMPLETE_STATIC_CAMERA2_SETUP_MAP':raise ValueError('identity/status drift')
 if i['apk']['sha256']!='f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea':raise ValueError('APK hash drift')
 if len(rows)!=357 or s['directOperationRowCount']!=357 or len({r['method'] for r in rows})!=252:raise ValueError('operation coverage drift')
 cats={k:sum(r['category']==k for r in rows) for k in EXPECTED_CATS}
 if cats!=EXPECTED_CATS or s['categoryCallCounts']!=EXPECTED_CATS:raise ValueError('category count drift')
 apis={k:sum(r['apiName']==k for r in rows) for k in EXPECTED_APIS}
 if apis!=EXPECTED_APIS:raise ValueError('API count drift')
 if s['reprocessBuilderCallSiteCount']!=14 or s['physicalOutputConfigurationCallSiteCount']!=12 or s['physicalIdRequestBuilderCallSiteCount']!=12:raise ValueError('mode/lens count drift')
 if c['templates']!={'preview':1,'stillCapture':2,'record':3}:raise ValueError('template drift')
 phases=[x['phase'] for x in c['orderedSetup']]
 if phases!=['OPEN','PREVIEW_BUILDER','SESSION_KEYS','SESSION_CREATE','PREVIEW_KEYS','SESSION_CONFIGURED','REPEATING','PREVIEW_UPDATE','STILL_CAPTURE','REPROCESS']:raise ValueError('ordering drift')
 if c['sessionBranches']['modernSessionConfiguration']['inputConfigurationCallSiteCount']!=1:raise ValueError('input configuration drift')
 modes={x['modeFamily'] for x in c['modeDifferences']}
 if modes!={'PHOTO_BASE','VIDEO','DUAL_OR_PHYSICAL','BOKEH','NIGHT_HDR_REPROCESS','SLOW_MOTION_HIGH_SPEED'}:raise ValueError('mode diff coverage drift')
 if c['lensDifferences']['physicalOutputConfigurationMethodCount']!=12 or c['lensDifferences']['physicalIdRequestBuilderMethodCount']!=12:raise ValueError('lens diff drift')
 mini=c['minimalPublicCamera2Equivalent']
 if len(mini['steps'])!=8 or 'not stock feature parity' not in mini['scope'] or 'ProxySession hidden API' not in mini['excluded']:raise ValueError('public equivalent boundary drift')
 limits=' '.join(c['limitations'])
 for p in ['not a runtime trace','not evidence of public physical-camera authorization','Firmware HAL']:
  if p not in limits:raise ValueError('evidence boundary lost')
 for p in ['docs/research/NOTHING_CAMERA_CAMERA2_SETUP.md','tools/validate-nothing-camera-camera2-setup.py']:
  if not (root/p).is_file():raise ValueError('missing companion')
 return True
def main():validate(load());print('validated Camera2 setup: 357 direct operations across 252 methods');return 0
if __name__=='__main__':raise SystemExit(main())
