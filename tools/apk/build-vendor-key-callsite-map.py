#!/usr/bin/env python3
"""Build complete static call-site coverage for every inventoried vendor key."""
from __future__ import annotations
import argparse,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]

def inventory_keys(inv):
 out=set()
 for entry in inv['families'].values():
  for direction,names in entry.items():
   if direction not in {'rearOnly','frontOnly'} and isinstance(names,list):out.update(x for x in names if isinstance(x,str))
 return out

def build(inv,scan,referenced):
 all_keys=inventory_keys(inv);ref_names={x['name'] for x in referenced['keys']}
 if not ref_names<=all_keys:raise ValueError('referenced key outside inventory')
 coverage={'schemaVersion':1,'issue':35,'referenceVersion':'2026.08.04-1','directionSource':'data/vendor-tags/inventory.json','candidateValueSource':'data/vendor-tags/advertised-values.json','referencedEvidence':'research/apk/vendor-key-callsite-referenced.v1.json','referencedKeys':sorted(ref_names),'noExactStaticReferenceKeys':sorted(all_keys-ref_names),'interpretation':'Every inventory key is covered. Referenced keys link to complete static evidence; all others have zero exact DEX literal/resolved-field references and retain reflection, dynamic-name, JNI/native, firmware and split-APK caveats.'}
 methods={s['method'] for r in referenced['keys'] for s in r['stockCallSites']}
 summary={'inventoryKeyCount':len(all_keys),'staticReferencedKeyCount':len(ref_names),'noExactStaticReferenceCount':len(all_keys-ref_names),'resolvedStaticFieldKeyCount':sum(bool(x.get('declaredKey')) for x in referenced['keys']),'callSiteEvidenceEventCount':sum(x['evidenceEventCount'] for x in referenced['keys']),'uniqueReferencedMethodCount':len(methods),'parseErrorCount':scan['summary']['parseErrorCount']}
 index={'schemaVersion':1,'issue':35,'referenceVersion':'2026.08.04-1','status':'COMPLETE_EXACT_STATIC_REFERENCE_MAP','apk':scan['apk'],'buildContext':scan['buildContext'],'summary':summary,'sourceFiles':{'inventory':'data/vendor-tags/inventory.json','advertisedValues':'data/vendor-tags/advertised-values.json','scanEvidence':'research/apk/vendor-key-callsite-scan.v1.json','referencedEvidence':'research/apk/vendor-key-callsite-referenced.v1.json'},'parts':{'coverage':'coverage.v1.json','referencedEvidence':'research/apk/vendor-key-callsite-referenced.v1.json'},'analysisMethod':scan['scan'],'limitations':scan['limitations']}
 return index,coverage

def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',type=pathlib.Path,default=ROOT/'data/vendor-tags/inventory.json');p.add_argument('--scan',type=pathlib.Path,default=ROOT/'research/apk/vendor-key-callsite-scan.v1.json');p.add_argument('--referenced-evidence',type=pathlib.Path,default=ROOT/'research/apk/vendor-key-callsite-referenced.v1.json');p.add_argument('--output-dir',type=pathlib.Path,default=ROOT/'data/vendor-tags/callsites');a=p.parse_args()
 index,coverage=build(json.loads(a.inventory.read_text()),json.loads(a.scan.read_text()),json.loads(a.referenced_evidence.read_text()));a.output_dir.mkdir(parents=True,exist_ok=True);(a.output_dir/'index.v1.json').write_text(json.dumps(index,indent=2)+'\n');(a.output_dir/'coverage.v1.json').write_text(json.dumps(coverage,indent=2)+'\n');print(json.dumps(index['summary'],indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
