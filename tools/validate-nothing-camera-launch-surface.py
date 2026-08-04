#!/usr/bin/env python3
from __future__ import annotations
import csv,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
SUMMARY={'launchComponentCount':14,'exportedLaunchComponentCount':12,'manifestActionCount':14,'staticShortcutCount':3,'literalParameterCallSiteCount':126,'uniqueLiteralParameterCount':58,'normalizedParameterCount':58,'widgetParameterCount':37,'observedExternalFallbackCaseCount':3,'parseErrorCount':0}
REQUIRED_ACTIONS={'android.intent.action.MAIN','com.nothing.camera.WIDGET_CAMERA','android.media.action.IMAGE_CAPTURE','android.media.action.VIDEO_CAPTURE','android.media.action.STILL_IMAGE_CAMERA','android.media.action.VIDEO_CAMERA','android.media.action.STILL_IMAGE_CAMERA_SECURE','android.media.action.IMAGE_CAPTURE_SECURE','android.media.action.SHORTCUT_CAMERA_SECURE','android.media.action.SHORTCUT_CAMERA','android.bluetooth.headset.action.OPEN_CAMERA','android.bluetooth.headset.action.OPEN_CAMERA_SECURE','com.google.camera.action.LOCATION_SETTINGS','android.nothing.action.APPCARD_UPDATE'}
REQUIRED_KEYS={'android.intent.extras.CAMERA_FACING','android.intent.extras.CAMERA_SUB_MODE','android.intent.extras.CAMERA_MAIN_MODE','android.intent.extras.CAMERA_PREFIX_FOCALLENGTH_VALUE','android.intent.extras.CAMERA_PREFIX_FLAG_WIDGET','android.intent.extras.CAMERA_PREFIX_MAIN_MODE','android.intent.extras.CAMERA_PREFIX_SUB_MODE','com.nothing.camera.WIDGET_CAMERA','com.nothing.camera.IS_FROM_WIDGET','com.google.assistant.extra.USE_FRONT_CAMERA','com.google.assistant.extra.CAMERA_MODE','android.intent.extra.videoQuality','android.intent.extra.durationLimit','android.intent.extra.sizeLimit','android.intent.extra.quickCapture','output','widget_id'}
def load(root=ROOT):
 b=root/'data/apk/nothing-camera-launch-surface'; i=json.loads((b/'index.v1.json').read_text()); parts=i['parts']
 r=json.loads((b/parts['core']).read_text()); r['normalizers']={}
 for name in parts['normalizers']: r['normalizers'].update(json.loads((b/name).read_text()))
 r.update(json.loads((b/parts['state']).read_text())); p=[]
 for name in parts['parameters']:
  with (b/name).open() as f: p.extend(csv.DictReader(f,delimiter='\t'))
 return i,r,p
def validate(v,root=ROOT):
 i,r,p=v
 if (i.get('schemaVersion'),i.get('issue'),i.get('referenceVersion'))!=(1,33,'2026.08.04-1') or i.get('status')!='COMPLETE_STATIC_LAUNCH_AND_STATE_MAP':raise ValueError('identity/status drift')
 if i.get('summary')!=SUMMARY:raise ValueError('summary drift')
 if i['apk']['sha256']!='f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea':raise ValueError('APK hash drift')
 if r.get('status')!='COMPLETE_STATIC_LAUNCH_AND_STATE_MAP':raise ValueError('route status drift')
 comps=r['components']; actions={a for c in comps for f in c['intentFilters'] for a in f['actions']}
 byname={c['name']:c for c in comps}
 if byname['com.nothing.camera.activity.CameraShortCutActivity']['exported'] is not False:raise ValueError('shortcut export restriction lost')
 if byname['com.nothing.camera.preset.importdata.ScanActivity']['exported'] is not None:raise ValueError('scan activity platform-default drift')
 if len(comps)!=14 or sum(c.get('exported') is True for c in comps)!=12 or actions!=REQUIRED_ACTIONS:raise ValueError('component/action drift')
 sc=r['shortcutsResource']['shortcuts']
 expected=[('backvideo',{'android.intent.extras.CAMERA_FACING':1,'android.intent.extras.CAMERA_SUB_MODE':'video'}),('portraitcamera',{'android.intent.extras.CAMERA_FACING':0,'android.intent.extras.CAMERA_SUB_MODE':'bokeh'}),('selfiephoto',{'android.intent.extras.CAMERA_FACING':1})]
 if [(x['shortcutId'],x['extras']) for x in sc]!=expected:raise ValueError('static shortcut drift')
 if any(x['target']['class']!='com.nothing.camera.activity.CameraShortCutActivity' or x['target']['action']!='android.media.action.SHORTCUT_CAMERA' for x in sc):raise ValueError('shortcut target drift')
 keys={x['key'] for x in p}; norms=set(r['normalizers'])
 if len(p)!=126 or len(keys)!=58 or keys!=norms or not REQUIRED_KEYS<=keys:raise ValueError('parameter coverage drift')
 if len([k for k in keys if k.startswith('android.intent.extras.CAMERA_PREFIX_')])!=37:raise ValueError('widget parameter coverage drift')
 focal=r['normalizers']['android.intent.extras.CAMERA_PREFIX_FOCALLENGTH_VALUE']
 if 'ModuleContext.onNewIntent' not in focal['consumer'] or 'focal-to-zoom lookup' not in focal['normalization']:raise ValueError('focal consumer drift')
 state=r['stateRestoration']
 if state['widgetPreferences']['namespacePattern']!='PRESET_SHORT_WIDGET_<widgetId>' or state['presetStore']['orderKey']!='camera_preset_list' or state['backupRestore']['widgetGate'].find('camera_restore_in_progress')<0:raise ValueError('state-store drift')
 obs=r['observedComparison']
 if obs['externalWidgetFocalLaunches']['inputs']!=['15mm','24mm','50mm'] or obs['internalExpertControls']['staticEndpoints']!=[2,0,3]:raise ValueError('external/internal comparison drift')
 if 'did not reproduce internal Expert endpoint selection' not in obs['conclusion']:raise ValueError('fallback conclusion drift')
 limits=' '.join(r['limitations'])
 for phrase in ['not successful camera authorization','explicitly non-exported','not a direct camera-ID command','audited build']:
  if phrase not in limits:raise ValueError('evidence boundary lost')
 for q in ['docs/research/NOTHING_CAMERA_LAUNCH_SURFACE.md','tools/validate-nothing-camera-launch-surface.py']:
  if not (root/q).is_file():raise ValueError('missing companion')
 return True
def main():validate(load());print('validated Nothing Camera launch surface: 14 components, 3 shortcuts, 58 parameters');return 0
if __name__=='__main__':raise SystemExit(main())
