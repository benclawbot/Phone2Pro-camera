from __future__ import annotations
import copy, importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=ROOT/'tools'/'validate-nothing-camera-jni-inventory.py'
SPEC=importlib.util.spec_from_file_location('validator',PATH); assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(M)
class Tests(unittest.TestCase):
    def setUp(self): self.data=M.load(ROOT)
    def test_valid(self): self.assertTrue(M.validate(self.data,ROOT))
    def test_apk_hash(self):
        d=copy.deepcopy(self.data); d[0]['apk']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'APK hash'): M.validate(d,ROOT)
    def test_integrity(self):
        d=copy.deepcopy(self.data); d[0]['encoding']['decodedSha256']='0'*64
        with self.assertRaisesRegex(ValueError,'integrity'): M.validate(d,ROOT)
    def test_native_count(self):
        d=copy.deepcopy(self.data); d[1]['nativeMethods'].pop()
        with self.assertRaisesRegex(ValueError,'native method count'): M.validate(d,ROOT)
    def test_library_count(self):
        d=copy.deepcopy(self.data); d[1]['libraries'].pop()
        with self.assertRaisesRegex(ValueError,'library count'): M.validate(d,ROOT)
    def test_parse_errors(self):
        d=copy.deepcopy(self.data); d[0]['parseErrors']=[{'dex':'x','error':'bad'}]; d[0]['summary']['parseErrorCount']=1
        with self.assertRaises(ValueError): M.validate(d,ROOT)
if __name__=='__main__': unittest.main()
