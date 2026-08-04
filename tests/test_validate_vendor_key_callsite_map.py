from __future__ import annotations
import copy,importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'tools/validate-vendor-key-callsite-map.py';S=importlib.util.spec_from_file_location('v',P);assert S and S.loader;M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
class Tests(unittest.TestCase):
 def setUp(self):self.v=M.load(ROOT)
 def test_valid(self):M.validate(self.v,ROOT)
 def test_coverage_loss(self):
  v=copy.deepcopy(self.v);v[1]['noExactStaticReferenceKeys'].pop()
  with self.assertRaisesRegex(ValueError,'coverage partition'):M.validate(v,ROOT)
 def test_false_reference(self):
  v=copy.deepcopy(self.v);v[1]['referencedKeys'].append(v[1]['noExactStaticReferenceKeys'].pop())
  with self.assertRaisesRegex(ValueError,'coverage partition'):M.validate(v,ROOT)
 def test_field_drift(self):
  v=copy.deepcopy(self.v);v[2]['keys'][0]['declaredKey']['field']='bad'
  with self.assertRaisesRegex(ValueError,'field binding'):M.validate(v,ROOT)
 def test_runtime_overclaim(self):
  v=copy.deepcopy(self.v);v[0]['status']='RUNTIME_COMPLETE'
  with self.assertRaisesRegex(ValueError,'identity/status'):M.validate(v,ROOT)
 def test_role_loss(self):
  v=copy.deepcopy(self.v);r=next(x for x in v[2]['keys'] if x['name']=='com.mediatek.control.capture.flipmode');r['stockCallSites']=[s for s in r['stockCallSites'] if s['role']!='RESULT_READER'];r['evidenceEventCount']=len(r['stockCallSites']);r['uniqueMethodCount']=len({s['method'] for s in r['stockCallSites']})
  with self.assertRaisesRegex(ValueError,'flip roles'):M.validate(v,ROOT)
if __name__=='__main__':unittest.main()
