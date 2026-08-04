from __future__ import annotations
import copy,importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];P=ROOT/'tools/validate-nothing-camera-camera2-setup.py';s=importlib.util.spec_from_file_location('v',P);M=importlib.util.module_from_spec(s);s.loader.exec_module(M)
class Tests(unittest.TestCase):
 def setUp(self):self.d=M.load(ROOT)
 def test_valid(self):self.assertTrue(M.validate(self.d,ROOT))
 def test_operation_loss(self):
  d=copy.deepcopy(self.d);d[2].pop()
  with self.assertRaisesRegex(ValueError,'operation coverage'):M.validate(d,ROOT)
 def test_order_drift(self):
  d=copy.deepcopy(self.d);d[1]['orderedSetup'][2],d[1]['orderedSetup'][3]=d[1]['orderedSetup'][3],d[1]['orderedSetup'][2]
  with self.assertRaisesRegex(ValueError,'ordering'):M.validate(d,ROOT)
 def test_template_drift(self):
  d=copy.deepcopy(self.d);d[1]['templates']['record']=1
  with self.assertRaisesRegex(ValueError,'template'):M.validate(d,ROOT)
 def test_lens_overclaim_guard(self):
  d=copy.deepcopy(self.d);d[1]['lensDifferences']['physicalOutputConfigurationMethodCount']=13
  with self.assertRaisesRegex(ValueError,'lens diff'):M.validate(d,ROOT)
 def test_public_equivalent_boundary(self):
  d=copy.deepcopy(self.d);d[1]['minimalPublicCamera2Equivalent']['scope']='stock feature parity'
  with self.assertRaisesRegex(ValueError,'public equivalent boundary'):M.validate(d,ROOT)
if __name__=='__main__':unittest.main()
