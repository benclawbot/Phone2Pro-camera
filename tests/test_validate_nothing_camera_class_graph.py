from __future__ import annotations
import copy, importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/'tools'/'validate-nothing-camera-class-graph.py'
SPEC=importlib.util.spec_from_file_location('graph_validator',PATH); assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)
class GraphValidationTests(unittest.TestCase):
 def setUp(self): self.value=M.load(ROOT)
 def test_valid(self): M.validate(self.value,ROOT)
 def test_missing_camera_context_rejected(self):
  v=copy.deepcopy(self.value); v['classGraph']['nodes']=[n for n in v['classGraph']['nodes'] if n['name']!='com.nothing.cameracore.context.module.CameraContext']
  with self.assertRaisesRegex(ValueError,'required class root'): M.validate(v,ROOT)
 def test_parse_error_rejected(self):
  v=copy.deepcopy(self.value); v['parseErrors']=['bad dex']
  with self.assertRaisesRegex(ValueError,'parse errors'): M.validate(v,ROOT)
 def test_runtime_overclaim_rejected(self):
  v=copy.deepcopy(self.value); v['evidenceClassification']='RUNTIME_VERIFIED'
  with self.assertRaisesRegex(ValueError,'evidence boundary'): M.validate(v,ROOT)
 def test_dangling_edge_rejected(self):
  v=copy.deepcopy(self.value); v['classGraph']['edges'][0]['target']='missing.Type'
  with self.assertRaisesRegex(ValueError,'dangling'): M.validate(v,ROOT)
if __name__=='__main__': unittest.main()
