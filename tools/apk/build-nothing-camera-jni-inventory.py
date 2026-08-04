#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, hashlib, json, os, re, struct, subprocess, sys, tempfile, zipfile
from pathlib import Path
from typing import Any

DEX_TOOL = Path(__file__).resolve().parent
from importlib.util import spec_from_file_location, module_from_spec
_spec=spec_from_file_location('dexidx', DEX_TOOL/'build-dex-routing-index.py'); assert _spec and _spec.loader
mod=module_from_spec(_spec); _spec.loader.exec_module(mod)
DexReader = mod.DexReader
ACC_NATIVE = mod.ACC_NATIVE

ACC_STATIC = 0x0008
ACC_PUBLIC = 0x0001
ACC_PRIVATE = 0x0002
ACC_PROTECTED = 0x0004

HANDLE_RE = re.compile(r'(?:native|handle|pointer|\bptr\b|context|engine|instance|session)', re.I)
CALLBACK_RE = re.compile(r'(?:callback|^on[A-Z]|notify|postEvent|eventFromNative|nativeEvent)', re.I)
ROUTING_RE = re.compile(r'(?:camera|lens|zoom|sat|multi.?cam|sensor|physical|seamless|remosaic|isp|raw|hdr|night|bokeh|portrait|denoise|super.?resolution|stabili|eis|ois)', re.I)
PROCESSING_RE = re.compile(r'(?:image|capture|process|algo|hdr|night|bokeh|portrait|beauty|denoise|refiner|panorama|super|raw|yuv|watermark|scanner|scene)', re.I)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def dex_class_to_java(desc: str) -> str:
    if desc.startswith('L') and desc.endswith(';'):
        return desc[1:-1].replace('/', '.')
    return desc

def access_names(flags: int) -> list[str]:
    out=[]
    for bit,name in [(ACC_PUBLIC,'public'),(ACC_PRIVATE,'private'),(ACC_PROTECTED,'protected'),(ACC_STATIC,'static'),(ACC_NATIVE,'native')]:
        if flags & bit: out.append(name)
    return out

def jni_encode(value: str) -> str:
    out=[]
    for ch in value:
        if ch.isalnum(): out.append(ch)
        elif ch == '/': out.append('_')
        elif ch == '_': out.append('_1')
        elif ch == ';': out.append('_2')
        elif ch == '[': out.append('_3')
        else: out.append('_0%04x' % ord(ch))
    return ''.join(out)

def descriptor_args(desc: str) -> str:
    return desc[1:desc.index(')')]

def jni_symbols(class_desc: str, name: str, desc: str) -> tuple[str,str]:
    cls=class_desc[1:-1]
    short='Java_'+jni_encode(cls)+'_'+jni_encode(name)
    long=short+'__'+jni_encode(descriptor_args(desc))
    return short,long

def priority_for(text: str) -> str:
    if ROUTING_RE.search(text): return 'HIGH_CAMERA_ROUTING_OR_ISP'
    if PROCESSING_RE.search(text): return 'MEDIUM_IMAGE_PROCESSING'
    return 'GENERAL_NATIVE_DEPENDENCY'

def package_of(java_class: str) -> str:
    return java_class.rsplit('.',1)[0] if '.' in java_class else ''

def field_defs(reader: Any) -> list[dict[str,Any]]:
    size=reader.u32(0x50); off=reader.u32(0x54)
    fields=[]
    for i in range(size):
        p=off+i*8
        class_idx=reader.u16(p); type_idx=reader.u16(p+2); name_idx=reader.u32(p+4)
        fields.append({'index':i,'classDescriptor':reader.types[class_idx], 'typeDescriptor':reader.types[type_idx], 'name':reader.strings[name_idx]})
    return fields

def defined_fields(reader: Any, refs: list[dict[str,Any]]) -> list[dict[str,Any]]:
    out=[]
    for class_number in range(reader.class_defs_size):
        class_offset=reader.class_defs_off+class_number*32
        class_data_offset=reader.u32(class_offset+24)
        if not class_data_offset: continue
        static_size,c=reader.uleb128(class_data_offset)
        instance_size,c=reader.uleb128(c)
        _,c=reader.uleb128(c); _,c=reader.uleb128(c)
        for kind,count in [('static',static_size),('instance',instance_size)]:
            idx=0
            for _ in range(count):
                diff,c=reader.uleb128(c); flags,c=reader.uleb128(c); idx+=diff
                if 0 <= idx < len(refs):
                    f=dict(refs[idx]); f.update({'dex':reader.name,'kind':kind,'accessFlags':flags,'access':access_names(flags)})
                    out.append(f)
    return out

def run(cmd: list[str]) -> str:
    p=subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return p.stdout

def parse_elf(path: Path, zip_name: str, data: bytes) -> dict[str,Any]:
    hdr=run(['readelf','-hW',str(path)])
    dyn=run(['readelf','-dW',str(path)])
    syms=run(['readelf','-Ws',str(path)])
    notes=run(['readelf','-nW',str(path)])
    machine=None; elf_class=None
    for line in hdr.splitlines():
        if 'Class:' in line: elf_class=line.split(':',1)[1].strip()
        if 'Machine:' in line: machine=line.split(':',1)[1].strip()
    soname=None; needed=[]
    for line in dyn.splitlines():
        m=re.search(r'\(SONAME\).*\[(.*?)\]',line)
        if m: soname=m.group(1)
        m=re.search(r'\(NEEDED\).*\[(.*?)\]',line)
        if m: needed.append(m.group(1))
    build_id=None
    m=re.search(r'Build ID:\s*([0-9a-fA-F]+)',notes)
    if m: build_id=m.group(1).lower()
    exports=[]; imports=[]
    for line in syms.splitlines():
        m=re.match(r'\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+)$',line)
        if not m: continue
        value,size,typ,bind,vis,ndx,name=m.groups(); name=name.strip().split('@',1)[0]
        if not name: continue
        rec={'name':name,'value':'0x'+value.lower(),'size':int(size),'type':typ,'bind':bind,'visibility':vis}
        if ndx == 'UND': imports.append(rec)
        elif bind in {'GLOBAL','WEAK'}: exports.append(rec)
    exported_jni=[x for x in exports if x['name'].startswith('Java_')]
    has_jni_onload=any(x['name']=='JNI_OnLoad' for x in exports)
    imports_register=any('RegisterNatives' in x['name'] for x in imports)
    return {
        'path':zip_name,'fileName':Path(zip_name).name,'sizeBytes':len(data),'sha256':sha256(data),
        'elfClass':elf_class,'machine':machine,'buildId':build_id,'soname':soname,'needed':sorted(set(needed)),
        'exportCount':len(exports),'importCount':len(imports),'exportedJniSymbolCount':len(exported_jni),
        'hasJniOnLoad':has_jni_onload,'importsRegisterNatives':imports_register,
        'registrationStatus':('DYNAMIC_REGISTRATION_CANDIDATE' if has_jni_onload or imports_register else 'NO_STATIC_DYNAMIC_REGISTRATION_MARKER'),
        'exports':exports,'imports':imports,
    }

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('apk',type=Path); ap.add_argument('out',type=Path)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    apk_bytes=a.apk.read_bytes(); apk_hash=sha256(apk_bytes)
    methods=[]; load_sites=[]; all_fields=[]; parse_errors=[]; dex_summaries=[]
    with zipfile.ZipFile(a.apk) as z:
        dex_names=sorted(n for n in z.namelist() if re.fullmatch(r'classes(?:\d+)?\.dex',n))
        for dn in dex_names:
            data=z.read(dn)
            try:
                r=DexReader(data,dn)
                refs=field_defs(r); all_fields.extend(defined_fields(r,refs))
                defined_count=0; native_count=0
                for dm in r.defined_methods():
                    defined_count+=1
                    strings=[r.strings[i] for i in dm.string_indexes]
                    invokes=[r.methods[i] for i in dm.invoked_method_indexes]
                    if dm.access_flags & ACC_NATIVE:
                        native_count+=1
                        java_class=dex_class_to_java(dm.ref.class_descriptor)
                        short,long=jni_symbols(dm.ref.class_descriptor,dm.ref.name,dm.ref.descriptor)
                        text=' '.join([java_class,dm.ref.name,dm.ref.descriptor])
                        methods.append({
                            'dex':dn,'classDescriptor':dm.ref.class_descriptor,'javaClass':java_class,'package':package_of(java_class),
                            'name':dm.ref.name,'descriptor':dm.ref.descriptor,'methodKey':dm.ref.key,'accessFlags':dm.access_flags,
                            'access':access_names(dm.access_flags),'jniShortSymbol':short,'jniLongSymbol':long,
                            'priority':priority_for(text),'exactLibraryMatches':[], 'ownershipStatus':'UNRESOLVED_OR_DYNAMIC_REGISTRATION',
                        })
                    ll=[x for x in invokes if x.class_descriptor=='Ljava/lang/System;' and x.name=='loadLibrary']
                    if ll:
                        plausible=[]
                        for s in strings:
                            if len(s)<=160 and re.fullmatch(r'[A-Za-z0-9_.+\-]+',s): plausible.append(s)
                        load_sites.append({'dex':dn,'method':dm.ref.key,'javaClass':dex_class_to_java(dm.ref.class_descriptor),
                                           'literalCandidates':sorted(set(plausible)), 'invokeCount':len(ll),
                                           'resolutionStatus':'CANDIDATE_LITERALS_FROM_METHOD'})
                dex_summaries.append({'name':dn,'sizeBytes':len(data),'sha256':sha256(data),'definedMethodCount':defined_count,'nativeMethodCount':native_count})
            except Exception as e:
                parse_errors.append({'dex':dn,'error':f'{type(e).__name__}: {e}'})
        lib_infos=[]
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            for info in sorted((i for i in z.infolist() if i.filename.startswith('lib/arm64-v8a/') and i.filename.endswith('.so')), key=lambda x:x.filename):
                data=z.read(info.filename); p=td/Path(info.filename).name; p.write_bytes(data)
                lib_infos.append(parse_elf(p,info.filename,data))
    by_load={}
    for lib in lib_infos:
        fn=lib['fileName']; stem=fn[3:-3] if fn.startswith('lib') and fn.endswith('.so') else Path(fn).stem
        by_load[stem]=lib['path']
    for site in load_sites:
        matches=[]
        for s in site['literalCandidates']:
            if s in by_load: matches.append({'literal':s,'packagedLibrary':by_load[s]})
        site['packagedMatches']=matches
        site['resolutionStatus']='PACKAGED_LIBRARY_MATCH' if matches else 'NO_EXACT_PACKAGED_LIBRARY_LITERAL_MATCH'
    export_map=collections.defaultdict(list)
    for lib in lib_infos:
        for ex in lib.pop('exports'):
            if ex['name'].startswith('Java_'):
                export_map[ex['name']].append({'library':lib['path'],'symbol':ex['name'],'offset':ex['value'],'size':ex['size']})
        imports=lib.pop('imports')
        lib['registrationImports']=[x for x in imports if 'RegisterNatives' in x['name'] or x['name'] in {'dlopen','dlsym'}]
    overload_counts=collections.Counter((m['classDescriptor'],m['name']) for m in methods)
    exact_count=0
    for m in methods:
        hits=[]
        hits.extend(export_map.get(m['jniLongSymbol'],[]))
        if overload_counts[(m['classDescriptor'],m['name'])] == 1:
            hits.extend(export_map.get(m['jniShortSymbol'],[]))
        seen=set(); dh=[]
        for h in hits:
            k=(h['library'],h['symbol'],h['offset'])
            if k not in seen: seen.add(k); dh.append(h)
        m['exactLibraryMatches']=dh
        if dh:
            exact_count+=1; m['ownershipStatus']='EXACT_EXPORTED_JNI_SYMBOL_MATCH'
    native_classes={m['classDescriptor'] for m in methods}
    handles=[]
    for f in all_fields:
        cls=f['classDescriptor']; java=dex_class_to_java(cls)
        if cls in native_classes and HANDLE_RE.search(f['name']):
            handles.append({**f,'javaClass':java,'priority':priority_for(java+' '+f['name']),
                            'classification':'CANDIDATE_NATIVE_HANDLE_FIELD'})
    callbacks=[]
    with zipfile.ZipFile(a.apk) as z:
        for dn in sorted(n for n in z.namelist() if re.fullmatch(r'classes(?:\d+)?\.dex',n)):
            try:
                r=DexReader(z.read(dn),dn)
                for dm in r.defined_methods():
                    if dm.ref.class_descriptor in native_classes and not (dm.access_flags & ACC_NATIVE) and CALLBACK_RE.search(dm.ref.name):
                        callbacks.append({'dex':dn,'javaClass':dex_class_to_java(dm.ref.class_descriptor),'methodKey':dm.ref.key,
                                          'access':access_names(dm.access_flags),'classification':'CANDIDATE_JAVA_CALLBACK_SURFACE',
                                          'priority':priority_for(dm.ref.key)})
            except Exception: pass
    class_counts=collections.Counter(m['javaClass'] for m in methods)
    priority_counts=collections.Counter(m['priority'] for m in methods)
    dynamic_libs=[l['path'] for l in lib_infos if l['registrationStatus']=='DYNAMIC_REGISTRATION_CANDIDATE']
    summary={
        'dexFileCount':len(dex_summaries),'nativeMethodCount':len(methods),'nativeOwningClassCount':len(class_counts),
        'loadSiteCount':len(load_sites),'packagedArm64LibraryCount':len(lib_infos),
        'exportedJniSymbolCount':sum(l['exportedJniSymbolCount'] for l in lib_infos),
        'exactExportMatchedMethodCount':exact_count,'unresolvedNativeMethodCount':len(methods)-exact_count,
        'dynamicRegistrationCandidateLibraryCount':len(dynamic_libs),'candidateNativeHandleFieldCount':len(handles),
        'candidateCallbackSurfaceCount':len(callbacks),'parseErrorCount':len(parse_errors),
    }
    index={
        'schemaVersion':1,'issue':36,'referenceVersion':'2026.08.04-1','status':'STATIC_APK_JNI_AND_LIBRARY_INVENTORY',
        'apk':{'fileName':a.apk.name,'versionName':'16.1.01.93.20','sha256':apk_hash,'sizeBytes':len(apk_bytes)},
        'buildScope':'nothing-galaga-eea-android16-2606151653-f88325f3','summary':summary,
        'dexFiles':dex_summaries,'priorityCounts':dict(sorted(priority_counts.items())),
        'parts':{'nativeMethods':[f'native-methods-{i:02d}.v1.json' for i in range(1,(len(methods)+99)//100+1)],
                 'loadSites':'load-sites.v1.json','libraries':'libraries.v1.json','handlesCallbacks':'handles-callbacks.v1.json'},
        'firmwareIssueLinks':{'libraryInventoryIssue':48,'symbolRecoveryIssue':49,'nativeHookIssue':41},
        'evidenceRules':[
            'EXACT_EXPORTED_JNI_SYMBOL_MATCH links a Java declaration to a packaged APK library export and records its ELF virtual-address offset.',
            'UNRESOLVED_OR_DYNAMIC_REGISTRATION does not mean unimplemented; RegisterNatives, JNI_OnLoad, reflection, generated bindings, stripped exports or firmware libraries may own the method.',
            'System.loadLibrary literal candidates are method-local static strings; only exact packaged-library stem matches are promoted.',
            'Candidate native handles and callbacks are naming-based hook targets, not proof of native ownership or runtime use.',
            'APK libraries are app-bundled processing dependencies; firmware HAL/ISP libraries remain outside this APK-only issue and are linked to issues #48 and #49.'
        ],
        'parseErrors':parse_errors,
    }
    (a.out/'index.v1.json').write_text(json.dumps(index,indent=2,ensure_ascii=False)+'\n')
    for i in range(0,len(methods),100):
        part={'schemaVersion':1,'issue':36,'part':i//100+1,'nativeMethods':methods[i:i+100]}
        (a.out/f'native-methods-{i//100+1:02d}.v1.json').write_text(json.dumps(part,separators=(',',':'),ensure_ascii=False)+'\n')
    (a.out/'load-sites.v1.json').write_text(json.dumps({'schemaVersion':1,'issue':36,'loadSites':load_sites},separators=(',',':'),ensure_ascii=False)+'\n')
    (a.out/'libraries.v1.json').write_text(json.dumps({'schemaVersion':1,'issue':36,'libraries':lib_infos},separators=(',',':'),ensure_ascii=False)+'\n')
    (a.out/'handles-callbacks.v1.json').write_text(json.dumps({'schemaVersion':1,'issue':36,'candidateNativeHandleFields':handles,'candidateCallbackSurfaces':callbacks},separators=(',',':'),ensure_ascii=False)+'\n')
    print(json.dumps(summary,indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
