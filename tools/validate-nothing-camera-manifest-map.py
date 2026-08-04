#!/usr/bin/env python3
"""Validate the derived Nothing Camera manifest/component reference."""
from __future__ import annotations
import json, pathlib
from typing import Any

PATH=pathlib.Path('data/apk/nothing-camera-manifest/index.v1.json')
EXPECTED_SUMMARY={'requestedPermissionCount':33,'componentCount':46,'activityCount':14,'serviceCount':13,'receiverCount':12,'providerCount':7,'exportedCount':21,'intentFilterCount':34,'nativeLibraryCount':74}
EXPECTED_APK='f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea'
EXPECTED_MANIFEST='dd1666377a40051c3f1f5dd60f27646b2043a12efd691ec40447fa6973840eaf'
EXPECTED_CERT='2c4e1f8eb95d96f760336f03b92bc3858111e987c59703f9873c8dc7faa4119d'
REQUIRED_ACTIONS={
 'android.intent.action.MAIN','com.nothing.camera.WIDGET_CAMERA','android.media.action.IMAGE_CAPTURE',
 'android.media.action.VIDEO_CAPTURE','android.media.action.STILL_IMAGE_CAMERA','android.media.action.VIDEO_CAMERA',
 'android.media.action.STILL_IMAGE_CAMERA_SECURE','android.media.action.IMAGE_CAPTURE_SECURE',
 'android.media.action.SHORTCUT_CAMERA_SECURE','android.media.action.SHORTCUT_CAMERA'}
REQUIRED_COMPONENTS={
 'com.nothing.camera.activity.CameraActivity','com.nothing.camera.activity.WidgetCameraActivity',
 'com.nothing.camera.activity.VoiceCameraActivity','com.nothing.camera.activity.SecureCameraActivity',
 'com.nothing.camera.activity.CameraShortCutActivity','com.nothing.camera.pipeline.ExtensionsInterfaceProxyImplService',
 'com.nothing.algolib.cameraufs.UFSService','com.nothing.camera.provider.SpecialTypeProvider'}

def load_reference(root:pathlib.Path=pathlib.Path('.'))->dict[str,Any]:
 index=json.loads((root/PATH).read_text(encoding='utf-8'))
 base=(root/PATH).parent
 components=[]
 for kind,file_name in index['componentFiles'].items():
  part=json.loads((base/file_name).read_text(encoding='utf-8'))
  if part.get('type')!=kind: raise ValueError('component part type mismatch')
  components.extend(part.get('components',[]))
 libraries=json.loads((base/index['libraryFile']).read_text(encoding='utf-8'))
 index['components']=components
 index['nativeLibraries']=libraries.get('nativeLibraries',[])
 index['optionalLibraries']=libraries.get('optionalLibraries',[])
 return index

def validate_reference(d:dict[str,Any],root:pathlib.Path=pathlib.Path('.'))->None:
 if d.get('schemaVersion')!=1 or d.get('issue')!=27: raise ValueError('schema/issue mismatch')
 if d.get('referenceVersion')!='2026.08.04-1': raise ValueError('reference version drift')
 src=d.get('source',{})
 if src.get('apkSha256')!=EXPECTED_APK or src.get('manifestSha256')!=EXPECTED_MANIFEST: raise ValueError('source hash drift')
 cert=src.get('certificate',{})
 if cert.get('sha256')!=EXPECTED_CERT or cert.get('classification')!='VERIFIED': raise ValueError('certificate identity drift')
 pkg=d.get('package',{})
 if (pkg.get('name'),pkg.get('versionName'),pkg.get('targetSdk'))!=('com.nothing.camera','16.1.01.93.20',36): raise ValueError('package identity drift')
 if d.get('summary')!=EXPECTED_SUMMARY: raise ValueError('summary count drift')
 perms=d.get('requestedPermissions',[])
 if len(perms)!=len(set(perms)): raise ValueError('duplicate requested permission')
 for required in ('android.permission.CAMERA','android.permission.SYSTEM_CAMERA','android.permission.WRITE_SECURE_SETTINGS'):
  if required not in perms: raise ValueError(f'missing privileged permission {required}')
 comps=d.get('components',[])
 names=[c.get('name') for c in comps]
 if len(names)!=len(set(names)): raise ValueError('duplicate component')
 if not REQUIRED_COMPONENTS.issubset(set(names)): raise ValueError('required camera component missing')
 counts={'componentCount':len(comps),'activityCount':sum(c['type']=='activity' for c in comps),'serviceCount':sum(c['type']=='service' for c in comps),'receiverCount':sum(c['type']=='receiver' for c in comps),'providerCount':sum(c['type']=='provider' for c in comps),'exportedCount':sum(c['exported'] is True for c in comps),'intentFilterCount':sum(len(c['intentFilters']) for c in comps)}
 for key,value in counts.items():
  if value!=EXPECTED_SUMMARY[key]: raise ValueError(f'{key} mismatch')
 actions={a for c in comps for f in c['intentFilters'] for a in f['actions']}
 if not REQUIRED_ACTIONS.issubset(actions): raise ValueError('camera launch action missing')
 shortcut=next(c for c in comps if c['name']=='com.nothing.camera.activity.CameraShortCutActivity')
 if shortcut['exported'] is not False or shortcut['exportedSource']!='EXPLICIT': raise ValueError('shortcut export boundary drift')
 for c in comps:
  if c['exportedSource'] not in {'EXPLICIT','PLATFORM_DEFAULT'}: raise ValueError('invalid exported source')
  if not isinstance(c['exported'],bool): raise ValueError('non-boolean effective export state')
 native=d.get('nativeLibraries',[])
 if len(native)!=74 or len(native)!=len(set(native)): raise ValueError('native library inventory drift')
 assessment=d.get('permissionAssessment',{})
 if 'android.permission.SYSTEM_CAMERA' not in assessment.get('platformOrSpecialAccessCandidates',[]): raise ValueError('SYSTEM_CAMERA classification lost')
 if 'Installed grants' not in assessment.get('boundary',''): raise ValueError('runtime evidence boundary lost')
 scope=d.get('scope',{})
 if scope.get('splitStatus')!='UNKNOWN_TRACKED_BY_CAM_020': raise ValueError('split boundary drift')
 doc=root/'docs/research/NOTHING_CAMERA_MANIFEST_MAP.md'
 tool=root/'tools/apk/extract-manifest-components.py'
 if not doc.is_file() or not tool.is_file(): raise ValueError('documentation or extraction tool missing')
 for file_name in list(d.get('componentFiles',{}).values())+[d.get('libraryFile')]:
  if not file_name or not (root/PATH).parent.joinpath(file_name).is_file(): raise ValueError('multipart reference file missing')

def main()->int:
 root=pathlib.Path(__file__).resolve().parents[1]
 validate_reference(load_reference(root),root)
 print('Nothing Camera manifest map is valid')
 return 0
if __name__=='__main__':raise SystemExit(main())
