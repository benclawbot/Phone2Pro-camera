#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, json, pathlib, zlib

def decode(path: pathlib.Path):
    return json.loads(zlib.decompress(base64.b64decode(path.read_text().strip())).decode('utf-8'))
def main():
    p=argparse.ArgumentParser(); p.add_argument('input',type=pathlib.Path,nargs='?',default=pathlib.Path('data/apk/nothing-camera-jni/inventory.v1.json.zlib.b64')); p.add_argument('--output',type=pathlib.Path)
    a=p.parse_args(); obj=decode(a.input); text=json.dumps(obj,indent=2,ensure_ascii=False)+'\n'
    if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(text)
    else: print(text,end='')
if __name__=='__main__': main()
