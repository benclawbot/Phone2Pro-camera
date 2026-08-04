#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, pathlib, zlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'data'/'apk'/'nothing-camera-jni'

def load(root: pathlib.Path=ROOT):
    base=root/'data'/'apk'/'nothing-camera-jni'
    index=json.loads((base/'index.v1.json').read_text())
    raw=zlib.decompress(base64.b64decode((base/index['parts']['compressedInventory']).read_text().strip()))
    return index,json.loads(raw),raw

def validate(data, root: pathlib.Path=ROOT):
    index,obj,raw=data; s=index['summary']; oi=obj['index']
    if index.get('issue')!=36 or index.get('status')!='STATIC_APK_JNI_AND_LIBRARY_INVENTORY': raise ValueError('issue/status drift')
    if index['apk']['sha256']!='f78368e303033d49c5564b1287f51ef2bf5dde53db4687a08bfb20aa64a8eeea': raise ValueError('APK hash drift')
    enc=index['encoding']
    if hashlib.sha256(raw).hexdigest()!=enc['decodedSha256'] or len(raw)!=enc['decodedSizeBytes']: raise ValueError('decoded inventory integrity drift')
    if oi['summary']!=s: raise ValueError('embedded summary drift')
    methods=obj['nativeMethods']; loads=obj['loadSites']; libs=obj['libraries']; handles=obj['candidateNativeHandleFields']; callbacks=obj['candidateCallbackSurfaces']
    if len(methods)!=794 or s['nativeMethodCount']!=len(methods): raise ValueError('native method count drift')
    if len({m['javaClass'] for m in methods})!=90 or s['nativeOwningClassCount']!=90: raise ValueError('native class count drift')
    if len(loads)!=69 or s['loadSiteCount']!=69: raise ValueError('load site count drift')
    if len(libs)!=77 or s['packagedArm64LibraryCount']!=77: raise ValueError('library count drift')
    if sum(x['exportedJniSymbolCount'] for x in libs)!=524 or s['exportedJniSymbolCount']!=524: raise ValueError('JNI export count drift')
    exact=sum(bool(m['exactLibraryMatches']) for m in methods)
    if exact!=s['exactExportMatchedMethodCount'] or exact<450: raise ValueError('exact ownership count drift')
    if s['unresolvedNativeMethodCount']!=len(methods)-exact: raise ValueError('unresolved count drift')
    if len(handles)!=s['candidateNativeHandleFieldCount'] or len(callbacks)!=s['candidateCallbackSurfaceCount']: raise ValueError('hook candidate count drift')
    if s['parseErrorCount'] or index.get('parseErrors') or oi.get('parseErrors'): raise ValueError('DEX parse errors present')
    if not any(m['priority']=='HIGH_CAMERA_ROUTING_OR_ISP' for m in methods): raise ValueError('missing routing/ISP priority')
    if not any(l['registrationStatus']=='DYNAMIC_REGISTRATION_CANDIDATE' for l in libs): raise ValueError('missing dynamic registration candidates')
    for m in methods:
        if m['ownershipStatus']=='EXACT_EXPORTED_JNI_SYMBOL_MATCH' and not m['exactLibraryMatches']: raise ValueError('exact ownership without symbol evidence')
        for hit in m['exactLibraryMatches']:
            if not hit['offset'].startswith('0x') or not hit['symbol'].startswith('Java_'): raise ValueError('bad JNI symbol linkage')
    packaged={l['path'] for l in libs}
    for site in loads:
        for match in site['packagedMatches']:
            if match['packagedLibrary'] not in packaged: raise ValueError('load-site library not packaged')
    if index['firmwareIssueLinks']!={'libraryInventoryIssue':48,'symbolRecoveryIssue':49,'nativeHookIssue':41}: raise ValueError('firmware issue links drift')
    return True

def main():
    validate(load()); print('validated Nothing Camera JNI inventory: 794 methods, 69 load sites, 77 libraries')
if __name__=='__main__': main()
