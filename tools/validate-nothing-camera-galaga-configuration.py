#!/usr/bin/env python3
from __future__ import annotations
import csv, json, pathlib
EXPECTED_TYPES={'float':5,'boolean':103,'string':12,'integer':102,'range_or_list':1}
REQUIRED_VALUES={
 'FEATURE_CAMERA_DEFAULT_SUPPORT_SAT':'true',
 'FEATURE_CAMERA_VIDEO_SUPPORT_SAT':'true',
 'FEATURE_CAMERA_4K_60FPS_SAT_SUPPORT':'false',
 'FEATURE_CAMERA_VIDEO_SAT_ONLY_1080P30FPS_SUPPORT':'true',
 'FEATURE_CAMERA_MAX_ZOOM':'20',
 'FEATURE_SHOW_NIGHT_MAX_ZOOM':'4.0',
 'FEATURE_BOKEH_DEFAULT_ZOOM':'2',
 'FEATURE_FOCALLENGTH_BACK_DEFAULT_THRESHOLD':'24mm',
 'FEATURE_WIDE_LEN_FOCAL_LENGTH_35MM_FILM':'15mm',
 'FEATURE_CAMERA_SUPER_RESOLUTION':'true',
 'FEATURE_CAMERA_SUPER_RESOLUTION_RAW':'false',
}

def load(root):
 base=root/'data'/'apk'/'nothing-camera-galaga-config'
 idx=json.loads((base/'index.v1.json').read_text())
 with (base/idx['parts']['entries']).open(newline='') as f: entries=list(csv.DictReader(f,delimiter='\t'))
 assets=json.loads((base/idx['parts']['assets']).read_text())
 routes=json.loads((base/idx['parts']['routes']).read_text())
 return idx,entries,assets,routes

def validate(value,root):
 idx,entries,assets,routes=value
 if (idx.get('schemaVersion'),idx.get('issue'),idx.get('referenceVersion'))!=(1,29,'2026.08.04-1'): raise ValueError('identity drift')
 if idx.get('status')!='COMPLETE_STATIC_GALAGA_APP_CONFIGURATION': raise ValueError('status drift')
 if idx['apk']['sha256']!='f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea': raise ValueError('APK hash drift')
 s=idx['summary']
 if len(entries)!=223 or s['configMapEntryCount']!=223: raise ValueError('ConfigMap entry count drift')
 keys=[x['key'] for x in entries]
 if len(set(keys))!=223: raise ValueError('duplicate ConfigMap key')
 types={}
 for x in entries: types[x['valueType']]=types.get(x['valueType'],0)+1
 if types!=EXPECTED_TYPES or s['valueTypeCounts']!=EXPECTED_TYPES: raise ValueError('value type count drift')
 by_key={x['key']:x for x in entries}
 for key,expected in REQUIRED_VALUES.items():
  if by_key.get(key,{}).get('value')!=expected: raise ValueError(f'required Galaga value drift: {key}')
 if any(int(x['literalReferenceMethodCount'])<1 for x in entries): raise ValueError('unlinked ConfigMap entry')
 if len(assets['assets'])!=2 or sum(len(x['features']) for x in assets['assets'])!=23: raise ValueError('bundled asset inventory drift')
 if s['bundledConfigAssetCount']!=2 or s['bundledConfigAssetFeatureCount']!=23: raise ValueError('asset summary drift')
 if routes.get('status')!='STATIC_STOCK_APK_CONFIGURATION' or routes['configMap']['entryCount']!=223: raise ValueError('route status drift')
 selector=routes['selectionAndFallback']['productSelector']
 if selector['property']!='ro.product.device' or selector['galagaClass']!='com.nothing.common.utils.config.ConfigMapGalaga': raise ValueError('Galaga selector drift')
 if len(routes['selectionAndFallback']['systemProperties'])!=8: raise ValueError('system property selector drift')
 back=[(x['zoomRatio'],x['equivalentFocalLengthMm']) for x in routes['focalConfig']['back']['points']]
 front=[(x['zoomRatio'],x['equivalentFocalLengthMm']) for x in routes['focalConfig']['front']['points']]
 if back!=[(.6,15),(1.0,24),(2.0,50),(3.0,70),(4.0,100),(5.0,120),(6.0,140),(10.0,240),(30.0,700)]: raise ValueError('back focal map drift')
 if front!=[(1.0,22),(1.2,27)]: raise ValueError('front focal map drift')
 modes={x['mode']:x for x in routes['simpleZoomRoutes']}
 if set(modes)!={'MANUAL','NIGHT','BOKEH','SLOW_MOTION','THIRD_PARTY'}: raise ValueError('simple zoom mode drift')
 if [(x['range'],x['cameraId']) for x in modes['MANUAL']['regions']]!=[('[0.6,1)',2),('[1,2)',0),('[2,10]',3)]: raise ValueError('manual camera route drift')
 if modes['NIGHT']['regions']!=[{'range':'[0.6,10]','cameraId':4}]: raise ValueError('night camera route drift')
 if modes['BOKEH']['regions']!=[{'range':'[1,4]','cameraId':5}]: raise ValueError('bokeh camera route drift')
 if {x['mode'] for x in routes['conditionedZoomBuilders']}!={'PHOTO','VIDEO','TIME_LAPSE'}: raise ValueError('conditioned builder drift')
 if len(routes['directConsumers'])!=17 or s['directConsumerMethodCount']!=17: raise ValueError('direct consumer count drift')
 sensor=routes['sensorScenarioBoundary']
 if sensor['exactStringOrMethodMatchCount']!=0 or sensor['status']!='UNKNOWN_BEYOND_APK_STATIC_SURFACE': raise ValueError('sensor scenario overclaim')
 limits=' '.join(routes['limitations'])
 for phrase in ['do not prove runtime selection','Firmware overlays','sensor-scenario']:
  if phrase not in limits: raise ValueError('evidence boundary lost')
 if idx['firmwareIssueLinks']!={'packageAndSplitInventory':26,'firmwareLibraryInventory':48,'firmwareSymbolRecovery':49}: raise ValueError('firmware issue links drift')
 for p in ['docs/research/NOTHING_CAMERA_GALAGA_CONFIGURATION.md','tools/validate-nothing-camera-galaga-configuration.py']:
  if not (root/p).is_file(): raise ValueError('missing companion')
 return True

def main():
 root=pathlib.Path(__file__).resolve().parents[1]
 validate(load(root),root)
 print('validated Nothing Camera Galaga configuration: 223 entries, 5 simple routes, 11 focal points')
if __name__=='__main__': main()
