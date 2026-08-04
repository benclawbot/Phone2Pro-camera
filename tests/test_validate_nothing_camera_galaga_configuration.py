from __future__ import annotations
import copy, importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/'tools'/'validate-nothing-camera-galaga-configuration.py'
spec=importlib.util.spec_from_file_location('validator',P)
assert spec and spec.loader
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

class Tests(unittest.TestCase):
 def setUp(self): self.data=M.load(ROOT)
 def test_valid(self): self.assertTrue(M.validate(self.data,ROOT))
 def test_entry_loss(self):
  d=copy.deepcopy(self.data); d[1].pop()
  with self.assertRaisesRegex(ValueError,'entry count'): M.validate(d,ROOT)
 def test_value_drift(self):
  d=copy.deepcopy(self.data)
  next(x for x in d[1] if x['key']=='FEATURE_CAMERA_DEFAULT_SUPPORT_SAT')['value']='false'
  with self.assertRaisesRegex(ValueError,'required Galaga value'): M.validate(d,ROOT)
 def test_manual_route_drift(self):
  d=copy.deepcopy(self.data); d[3]['simpleZoomRoutes'][0]['regions'][0]['cameraId']=0
  with self.assertRaisesRegex(ValueError,'manual camera route'): M.validate(d,ROOT)
 def test_focal_drift(self):
  d=copy.deepcopy(self.data); d[3]['focalConfig']['back']['points'][3]['equivalentFocalLengthMm']=75
  with self.assertRaisesRegex(ValueError,'back focal map'): M.validate(d,ROOT)
 def test_sensor_runtime_overclaim(self):
  d=copy.deepcopy(self.data); d[3]['sensorScenarioBoundary']['status']='VERIFIED'
  with self.assertRaisesRegex(ValueError,'sensor scenario overclaim'): M.validate(d,ROOT)

if __name__=='__main__': unittest.main()
