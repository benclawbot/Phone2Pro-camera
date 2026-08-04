from __future__ import annotations
import copy,importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]; P=ROOT/'tools/validate-nothing-camera-launch-surface.py'; s=importlib.util.spec_from_file_location('v',P); M=importlib.util.module_from_spec(s); s.loader.exec_module(M)
class Tests(unittest.TestCase):
 def setUp(self):self.d=M.load(ROOT)
 def test_valid(self):self.assertTrue(M.validate(self.d,ROOT))
 def test_parameter_loss(self):
  d=copy.deepcopy(self.d);d[2].pop()
  with self.assertRaisesRegex(ValueError,'parameter coverage'):M.validate(d,ROOT)
 def test_shortcut_export_overclaim(self):
  d=copy.deepcopy(self.d);next(x for x in d[1]['components'] if x['name'].endswith('CameraShortCutActivity'))['exported']=True
  with self.assertRaisesRegex(ValueError,'shortcut export'):M.validate(d,ROOT)
 def test_focal_consumer_loss(self):
  d=copy.deepcopy(self.d);d[1]['normalizers']['android.intent.extras.CAMERA_PREFIX_FOCALLENGTH_VALUE']['consumer']='camera id'
  with self.assertRaisesRegex(ValueError,'focal consumer'):M.validate(d,ROOT)
 def test_fallback_overclaim(self):
  d=copy.deepcopy(self.d);d[1]['observedComparison']['conclusion']='External route selected internal endpoints.'
  with self.assertRaisesRegex(ValueError,'fallback conclusion'):M.validate(d,ROOT)
 def test_state_store_drift(self):
  d=copy.deepcopy(self.d);d[1]['stateRestoration']['presetStore']['orderKey']='other'
  with self.assertRaisesRegex(ValueError,'state-store'):M.validate(d,ROOT)
if __name__=='__main__':unittest.main()
