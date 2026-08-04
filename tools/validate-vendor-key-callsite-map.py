#!/usr/bin/env python3
"""Validate the complete Nothing Camera vendor-key static call-site map."""
from __future__ import annotations
import importlib.util,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
EXPECTED={'com.mediatek.configure.setting.initrequest','com.mediatek.control.capture.flipmode','com.mediatek.control.capture.zsl.mode','com.mediatek.hdrfeature.hdrMode','com.mediatek.streamingfeature.hfpsMode','com.nothing.camera.eis.supereismode'}
FIELDS={'com.mediatek.configure.setting.initrequest':'mQuickPreviewKey','com.mediatek.control.capture.flipmode':'sMTKFlipKey','com.mediatek.control.capture.zsl.mode':'mKeyZslMode','com.mediatek.hdrfeature.hdrMode':'MTK_ENABLE_SHDR','com.mediatek.streamingfeature.hfpsMode':'MTK_STREAMING_FEATURE_HFPS_MODE','com.nothing.camera.eis.supereismode':'NT_SUPER_EIS_ENABLE'}
SUMMARY={'inventoryKeyCount':162,'staticReferencedKeyCount':6,'noExactStaticReferenceCount':156,'resolvedStaticFieldKeyCount':6,'callSiteEvidenceEventCount':35,'uniqueReferencedMethodCount':18,'parseErrorCount':0}

def load(root=ROOT):
 index=json.loads((root/'data/vendor-tags/callsites/index.v1.json').read_text());coverage=json.loads((root/'data/vendor-tags/callsites'/index['parts']['coverage']).read_text());referenced=json.loads((root/index['parts']['referencedEvidence']).read_text());return index,coverage,referenced

def all_inventory(inv):
 out=set()
 for entry in inv['families'].values():
  for direction,names in entry.items():
   if direction not in {'rearOnly','frontOnly'} and isinstance(names,list):out.update(x for x in names if isinstance(x,str))
 return out

def builder(root):
 path=root/'tools/apk/build-vendor-key-callsite-map.py';spec=importlib.util.spec_from_file_location('vk_builder',path);assert spec and spec.loader;m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def validate(value,root=ROOT):
 index,cov,ref=value
 if (index.get('schemaVersion'),index.get('issue'),index.get('referenceVersion'))!=(1,35,'2026.08.04-1') or index.get('status')!='COMPLETE_EXACT_STATIC_REFERENCE_MAP':raise ValueError('identity/status drift')
 if index.get('summary')!=SUMMARY:raise ValueError('summary drift')
 inventory=json.loads((root/'data/vendor-tags/inventory.json').read_text());names=all_inventory(inventory);rset=set(cov['referencedKeys']);uset=set(cov['noExactStaticReferenceKeys'])
 if len(names)!=162 or rset!=EXPECTED or rset&uset or rset|uset!=names:raise ValueError('coverage partition drift')
 if cov.get('directionSource')!='data/vendor-tags/inventory.json' or cov.get('candidateValueSource')!='data/vendor-tags/advertised-values.json':raise ValueError('source link drift')
 records={x['name']:x for x in ref['keys']}
 if set(records)!=EXPECTED:raise ValueError('referenced record drift')
 for name,record in records.items():
  if FIELDS[name] not in record.get('declaredKey',{}).get('field',''):raise ValueError(f'field binding drift: {name}')
  sites=record.get('stockCallSites',[])
  if len(sites)!=record['evidenceEventCount'] or len({s['method'] for s in sites})!=record['uniqueMethodCount']:raise ValueError('call-site count drift')
 roles={n:{s['role'] for s in r['stockCallSites']} for n,r in records.items()}
 if not {'REQUEST_WRITER','RESULT_READER'}<=roles['com.mediatek.control.capture.flipmode']:raise ValueError('flip roles incomplete')
 if 'SESSION_KEY_LOOKUP_ASSIGNMENT' not in roles['com.mediatek.control.capture.zsl.mode']:raise ValueError('ZSL lookup missing')
 if 'FIELD_CONSUMER_OR_ACCESSOR' not in roles['com.mediatek.configure.setting.initrequest']:raise ValueError('quick preview consumer missing')
 for n in {'com.mediatek.hdrfeature.hdrMode','com.mediatek.streamingfeature.hfpsMode','com.nothing.camera.eis.supereismode'}:
  if 'REQUEST_WRITER' not in roles[n]:raise ValueError(f'writer missing: {n}')
 scan=json.loads((root/'research/apk/vendor-key-callsite-scan.v1.json').read_text())
 if scan['summary']['parseErrorCount'] or len(scan['dexFiles'])!=7 or any(len(x['sha256'])!=64 for x in scan['dexFiles']):raise ValueError('DEX provenance incomplete')
 limitations=' '.join(index['limitations'])
 if 'does not prove runtime non-use' not in limitations or 'JNI/native' not in limitations:raise ValueError('evidence caveat lost')
 rebuilt=builder(root).build(inventory,scan,ref)
 if rebuilt!=(index,cov):raise ValueError('generated output drift')
 for p in ['docs/research/VENDOR_KEY_CALLSITE_MAP.md','tools/apk/build-vendor-key-callsite-map.py']:
  if not (root/p).is_file():raise ValueError('missing companion')

def main():validate(load());print('Vendor-key call-site map is valid');return 0
if __name__=='__main__':raise SystemExit(main())
