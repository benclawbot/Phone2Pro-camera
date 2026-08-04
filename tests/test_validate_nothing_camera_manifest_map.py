from __future__ import annotations
import copy, importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/'tools'/'validate-nothing-camera-manifest-map.py'
SPEC=importlib.util.spec_from_file_location('manifest_validator',PATH); assert SPEC and SPEC.loader
MODULE=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MODULE)

class ManifestMapTests(unittest.TestCase):
 def setUp(self): self.value=MODULE.load_reference(ROOT)
 def test_reference_validates(self): MODULE.validate_reference(self.value,ROOT)
 def test_missing_system_camera_is_rejected(self):
  v=copy.deepcopy(self.value); v['requestedPermissions'].remove('android.permission.SYSTEM_CAMERA')
  with self.assertRaisesRegex(ValueError,'missing privileged permission'): MODULE.validate_reference(v,ROOT)
 def test_exported_drift_is_rejected(self):
  v=copy.deepcopy(self.value); next(c for c in v['components'] if c['name']=='com.nothing.camera.activity.CameraShortCutActivity')['exported']=True
  with self.assertRaisesRegex(ValueError,'exportedCount mismatch|shortcut export boundary'): MODULE.validate_reference(v,ROOT)
 def test_route_action_loss_is_rejected(self):
  v=copy.deepcopy(self.value)
  for c in v['components']:
   for f in c['intentFilters']: f['actions']=[a for a in f['actions'] if a!='android.media.action.IMAGE_CAPTURE_SECURE']
  with self.assertRaisesRegex(ValueError,'camera launch action'): MODULE.validate_reference(v,ROOT)
 def test_source_hash_drift_is_rejected(self):
  v=copy.deepcopy(self.value); v['source']['manifestSha256']='0'*64
  with self.assertRaisesRegex(ValueError,'source hash drift'): MODULE.validate_reference(v,ROOT)
 def test_split_unknown_boundary_is_required(self):
  v=copy.deepcopy(self.value); v['scope']['splitStatus']='COMPLETE'
  with self.assertRaisesRegex(ValueError,'split boundary drift'): MODULE.validate_reference(v,ROOT)
if __name__=='__main__':unittest.main()
