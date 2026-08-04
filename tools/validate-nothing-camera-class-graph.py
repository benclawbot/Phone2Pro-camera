#!/usr/bin/env python3
"""Validate the bounded Nothing Camera package/class dependency graph."""
from __future__ import annotations
import json, pathlib
from typing import Any

BASE=pathlib.Path('data/apk/nothing-camera-class-graph')
EXPECTED={
 'dexFileCount':7,'definedMethodCount':320221,'matchedMethodCount':1806,
 'candidateMethodCount':679,'classNodeCount':80,'classEdgeCount':70,
 'packageNodeCount':36,'packageEdgeCount':24,'syntheticCallbackEdgeCount':15274,
 'applicationCameraOpenCallSiteCount':1,'parseErrorCount':0}
REQUIRED_CLASSES={
 'com.nothing.camera.activity.CameraActivity',
 'com.nothing.common.setting.SettingContext',
 'com.nothing.common.setting.LaunchIntentParser',
 'com.nothing.common.setting.CameraDeviceInfoManager',
 'com.nothing.cameracore.context.module.CameraContext',
 'com.nothing.cameracore.context.module.CameraContext$3',
 'com.nothing.cameracore.context.module.usecase.DualYuvImageCapture',
 'com.nothing.camera.mode.PhotoMode',
 'com.nothing.camera.mode.NcfBokehMode'}
REQUIRED_SIGNALS={'camera-open','camera-open-dispatch','camera-id-constant','expert-ui','jni-native','physical-output','sat-multicam','session-construction','vendor-routing-key'}

def load(root:pathlib.Path=pathlib.Path('.'))->dict[str,Any]:
 base=root/BASE; index=json.loads((base/'index.v1.json').read_text())
 parts=index['parts']
 nodes=json.loads((base/parts['classNodes']).read_text())['nodes']
 edges=json.loads((base/parts['classEdges']).read_text())['edges']
 packages=json.loads((base/parts['packageGraph']).read_text())
 methods=json.loads((base/parts['methods']).read_text())['methods']
 index['classGraph']={'nodes':nodes,'edges':edges}
 index['packageGraph']={'nodes':packages['nodes'],'edges':packages['edges']}
 index['routeCandidateMethods']=methods
 return index

def validate(d:dict[str,Any],root:pathlib.Path=pathlib.Path('.'))->None:
 if (d.get('schemaVersion'),d.get('issue'),d.get('referenceVersion'))!=(1,28,'2026.08.04-1'): raise ValueError('identity drift')
 if d.get('evidenceClassification')!='STATIC_REFERENCE_ONLY': raise ValueError('evidence boundary drift')
 if d.get('summary')!=EXPECTED: raise ValueError('summary drift')
 if d.get('parseErrors'): raise ValueError('DEX parse errors present')
 dex=d.get('dexFiles',[])
 if [x.get('name') for x in dex]!=['classes.dex','classes2.dex','classes3.dex','classes4.dex','classes5.dex','classes6.dex','classes7.dex']: raise ValueError('DEX inventory drift')
 if any(len(x.get('sha256',''))!=64 for x in dex): raise ValueError('DEX hash missing')
 nodes=d['classGraph']['nodes']; edges=d['classGraph']['edges']; methods=d['routeCandidateMethods']
 names=[n['name'] for n in nodes]
 if len(names)!=len(set(names)) or not REQUIRED_CLASSES.issubset(names): raise ValueError('required class root missing')
 if len(nodes)!=EXPECTED['classNodeCount'] or len(edges)!=EXPECTED['classEdgeCount'] or len(methods)!=20: raise ValueError('bounded graph size drift')
 if not REQUIRED_SIGNALS.issubset(d.get('signalCounts',{})): raise ValueError('routing signal missing')
 if not any(r.get('kind')=='APPLICATION_CAMERA_OPEN' and 'CameraContext$3' in str(r.get('value')) for r in d.get('cameraRoots',[])): raise ValueError('application camera-open root missing')
 if not any('CameraContext;->openCamera' in ' '.join(r.get('value',[])) for r in d.get('cameraRoots',[]) if isinstance(r.get('value'),list)): raise ValueError('CameraContext open spine missing')
 for edge in edges:
  if edge.get('confidence')!='STATIC_DIRECT_REFERENCE': raise ValueError('edge confidence drift')
  if edge.get('source') not in names or edge.get('target') not in names: raise ValueError('dangling class edge')
 roles={n['role'] for n in nodes}
 for required in {'CONTEXT','MANAGER','USE_CASE','NATIVE_BRIDGE'}:
  if required not in roles: raise ValueError(f'role missing: {required}')
 uncertainty=d.get('uncertainty',{})
 if uncertainty.get('syntheticCallbackEdges')!=15274 or 'does not prove runtime execution' not in uncertainty.get('directEdges',''): raise ValueError('uncertainty boundary drift')
 for path in ['tools/apk/build-camera-class-graph.py','docs/research/NOTHING_CAMERA_CLASS_GRAPH.md']:
  if not (root/path).is_file(): raise ValueError(f'missing companion: {path}')

def main()->int:
 root=pathlib.Path(__file__).resolve().parents[1]; validate(load(root),root)
 print('Nothing Camera class graph is valid'); return 0
if __name__=='__main__': raise SystemExit(main())
