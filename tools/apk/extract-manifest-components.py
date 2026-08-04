#!/usr/bin/env python3
"""Extract a complete component/permission map from Android binary manifests."""
from __future__ import annotations
import argparse, hashlib, json, struct, zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RES_STRING_POOL_TYPE=0x0001; RES_XML_TYPE=0x0003; RES_XML_START_NAMESPACE_TYPE=0x0100
RES_XML_START_ELEMENT_TYPE=0x0102; RES_XML_END_ELEMENT_TYPE=0x0103
UTF8_FLAG=0x100; NO_INDEX=0xFFFFFFFF; TYPE_STRING=0x03; TYPE_INT_DEC=0x10; TYPE_INT_HEX=0x11; TYPE_INT_BOOLEAN=0x12; TYPE_REFERENCE=0x01
COMPONENT_TYPES={"activity","activity-alias","service","receiver","provider"}
ANDROID_URI="http://schemas.android.com/apk/res/android"

class BinaryXmlError(ValueError): pass

def u16(b:bytes,o:int)->int:
    if o<0 or o+2>len(b): raise BinaryXmlError(f"u16 outside document at {o}")
    return struct.unpack_from('<H',b,o)[0]
def u32(b:bytes,o:int)->int:
    if o<0 or o+4>len(b): raise BinaryXmlError(f"u32 outside document at {o}")
    return struct.unpack_from('<I',b,o)[0]
def read_len8(b:bytes,o:int,limit:int)->tuple[int,int]:
    if o>=limit: raise BinaryXmlError('truncated UTF-8 length')
    first=b[o]
    if first&0x80:
        if o+1>=limit: raise BinaryXmlError('truncated UTF-8 length')
        return ((first&0x7f)<<8)|b[o+1],2
    return first,1
def read_len16(b:bytes,o:int,limit:int)->tuple[int,int]:
    if o+2>limit: raise BinaryXmlError('truncated UTF-16 length')
    first=u16(b,o)
    if first&0x8000:
        if o+4>limit: raise BinaryXmlError('truncated UTF-16 length')
        return ((first&0x7fff)<<16)|u16(b,o+2),4
    return first,2

class StringPool:
    def __init__(self,b:bytes,o:int,hs:int,size:int):
        if hs<28: raise BinaryXmlError('string pool header too small')
        self.b=b; self.end=o+size; count=u32(b,o+8); flags=u32(b,o+16); start=u32(b,o+20)
        self.utf8=bool(flags&UTF8_FLAG); offsets_start=o+hs
        self.offsets=[u32(b,offsets_start+i*4) for i in range(count)]; self.base=o+start
    def get(self,index:int)->str|None:
        if index==NO_INDEX:return None
        if index<0 or index>=len(self.offsets): raise BinaryXmlError(f'bad string index {index}')
        p=self.base+self.offsets[index]
        if self.utf8:
            _,n=read_len8(self.b,p,self.end); p+=n
            length,n=read_len8(self.b,p,self.end); p+=n
            if p+length>self.end: raise BinaryXmlError('UTF-8 string exceeds pool')
            return self.b[p:p+length].decode('utf-8','replace')
        length,n=read_len16(self.b,p,self.end); p+=n
        if p+length*2>self.end: raise BinaryXmlError('UTF-16 string exceeds pool')
        return self.b[p:p+length*2].decode('utf-16le','replace')

@dataclass
class Node:
    name:str; attributes:dict[str,Any]=field(default_factory=dict); children:list['Node']=field(default_factory=list); line:int=0

class Parser:
    def __init__(self,b:bytes):
        self.b=b; self.pool:StringPool|None=None; self.ns={ANDROID_URI:'android'}
    def string(self,i:int)->str|None:
        if not self.pool: raise BinaryXmlError('string pool not loaded')
        return self.pool.get(i)
    def qname(self,ns_i:int,name_i:int)->str:
        name=self.string(name_i) or '' ; uri=self.string(ns_i)
        return f"{self.ns[uri]}:{name}" if uri in self.ns and self.ns[uri] else name
    def value(self,typ:int,data:int,raw_i:int)->Any:
        raw=self.string(raw_i)
        if raw is not None:return raw
        if typ==TYPE_STRING:return self.string(data)
        if typ==TYPE_INT_BOOLEAN:return bool(data)
        if typ==TYPE_INT_DEC:return data if data<0x80000000 else data-0x100000000
        if typ==TYPE_INT_HEX:return f"0x{data:08x}"
        if typ==TYPE_REFERENCE:return f"@0x{data:08x}"
        return f"0x{data:08x}"
    def parse(self)->Node:
        b=self.b
        if len(b)<8 or u16(b,0)!=RES_XML_TYPE: raise BinaryXmlError('not Android binary XML')
        total=min(u32(b,4),len(b)); o=u16(b,2); stack:list[Node]=[]; root=None
        while o+8<=total:
            typ=u16(b,o); hs=u16(b,o+2); size=u32(b,o+4)
            if size<8 or o+size>total: raise BinaryXmlError(f'invalid chunk at {o}')
            if typ==RES_STRING_POOL_TYPE:self.pool=StringPool(b,o,hs,size)
            elif typ==RES_XML_START_NAMESPACE_TYPE:
                prefix=self.string(u32(b,o+16)) or ''; uri=self.string(u32(b,o+20)) or ''
                if uri:self.ns[uri]=prefix
            elif typ==RES_XML_START_ELEMENT_TYPE:
                line=u32(b,o+8); ns_i=u32(b,o+16); name_i=u32(b,o+20)
                attr_start=u16(b,o+24); attr_size=u16(b,o+26); attr_count=u16(b,o+28)
                attrs={}; a0=o+16+attr_start
                for i in range(attr_count):
                    p=a0+i*attr_size
                    key=self.qname(u32(b,p),u32(b,p+4)); attrs[key]=self.value(b[p+15],u32(b,p+16),u32(b,p+8))
                node=Node(self.qname(ns_i,name_i),attrs,[],line)
                if stack:stack[-1].children.append(node)
                else:root=node
                stack.append(node)
            elif typ==RES_XML_END_ELEMENT_TYPE:
                if not stack: raise BinaryXmlError('unbalanced end element')
                stack.pop()
            o+=size
        if root is None: raise BinaryXmlError('manifest has no root element')
        return root

def read_input(path:Path)->tuple[bytes,str,bytes|None]:
    raw=path.read_bytes()
    if path.suffix.lower()=='.apk' or raw[:2]==b'PK':
        with zipfile.ZipFile(path) as z: return z.read('AndroidManifest.xml'),'apk',raw
    return raw,'manifest',None

def attr(n:Node,name:str,default=None):return n.attributes.get(f'android:{name}',n.attributes.get(name,default))
def children(n:Node,name:str):return [c for c in n.children if c.name==name]
def filters(n:Node)->list[dict[str,Any]]:
    out=[]
    for f in children(n,'intent-filter'):
        out.append({'label':attr(f,'label'),'priority':attr(f,'priority'),
                    'actions':[attr(x,'name') for x in children(f,'action')],
                    'categories':[attr(x,'name') for x in children(f,'category')],
                    'data':[x.attributes for x in children(f,'data')]})
    return out

def metadata(n:Node)->list[dict[str,Any]]:
    return [{'name':attr(x,'name'),'value':attr(x,'value'),'resource':attr(x,'resource')} for x in children(n,'meta-data')]

def family(name:str)->str:
    if name.startswith(('com.nothing.camera','com.nothing.common','com.nothing.algolib','com.nothing.cardclient')):return 'NOTHING_FIRST_PARTY'
    if name.startswith(('androidx.','com.google.')):return 'BUNDLED_LIBRARY'
    return 'OTHER'

def effective_exported(kind:str,explicit:Any,has_filters:bool,target:int)->tuple[bool,str]:
    if isinstance(explicit,bool):return explicit,'EXPLICIT'
    if kind=='provider':return (target<17),'PLATFORM_DEFAULT'
    return has_filters,'PLATFORM_DEFAULT'

def build_report(path:Path)->dict[str,Any]:
    manifest,source_kind,apk_bytes=read_input(path); root=Parser(manifest).parse()
    app=next((c for c in root.children if c.name=='application'),None)
    if app is None: raise BinaryXmlError('missing application')
    target=int(attr(next(c for c in root.children if c.name=='uses-sdk'),'targetSdkVersion'))
    components=[]
    for n in app.children:
        if n.name not in COMPONENT_TYPES:continue
        name=str(attr(n,'name')); fs=filters(n); explicit=attr(n,'exported')
        exported,source=effective_exported(n.name,explicit,bool(fs),target)
        components.append({'type':n.name,'name':name,'family':family(name),'enabled':attr(n,'enabled',True),
            'exported':exported,'exportedSource':source,'explicitExported':explicit,'permission':attr(n,'permission'),
            'readPermission':attr(n,'readPermission'),'writePermission':attr(n,'writePermission'),'process':attr(n,'process'),
            'authorities':attr(n,'authorities'),'directBootAware':attr(n,'directBootAware',False),
            'foregroundServiceType':attr(n,'foregroundServiceType'),'intentFilters':fs,'metadata':metadata(n),'line':n.line})
    permissions=[attr(n,'name') for n in root.children if n.name=='uses-permission']
    declared=[{'name':attr(n,'name'),'protectionLevel':attr(n,'protectionLevel')} for n in root.children if n.name=='permission']
    queries=next((n for n in root.children if n.name=='queries'),None)
    query_packages=[attr(n,'name') for n in queries.children if n.name=='package'] if queries else []
    native=[attr(n,'name') for n in app.children if n.name=='uses-native-library']
    libraries=[attr(n,'name') for n in app.children if n.name=='uses-library']
    return {'schemaVersion':1,'issue':27,'source':{'inputKind':source_kind,'fileName':path.name,
        'apkSha256':hashlib.sha256(apk_bytes).hexdigest() if apk_bytes else None,
        'manifestSha256':hashlib.sha256(manifest).hexdigest()},
        'package':{'name':root.attributes.get('package'),'versionCode':attr(root,'versionCode'),'versionName':attr(root,'versionName'),
        'minSdk':attr(next(c for c in root.children if c.name=='uses-sdk'),'minSdkVersion'),'targetSdk':target,
        'applicationClass':attr(app,'name'),'backupAgent':attr(app,'backupAgent')},
        'requestedPermissions':permissions,'declaredPermissions':declared,'queryPackages':query_packages,
        'nativeLibraries':native,'optionalLibraries':libraries,'components':components,
        'summary':{'requestedPermissionCount':len(permissions),'componentCount':len(components),
        'activityCount':sum(c['type']=='activity' for c in components),'serviceCount':sum(c['type']=='service' for c in components),
        'receiverCount':sum(c['type']=='receiver' for c in components),'providerCount':sum(c['type']=='provider' for c in components),
        'exportedCount':sum(c['exported'] for c in components),'intentFilterCount':sum(len(c['intentFilters']) for c in components),
        'nativeLibraryCount':len(native)}}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('input',type=Path); ap.add_argument('--json',type=Path)
    args=ap.parse_args(); report=build_report(args.input); text=json.dumps(report,indent=2,ensure_ascii=False)+"\n"
    if args.json: args.json.parent.mkdir(parents=True,exist_ok=True); args.json.write_text(text,encoding='utf-8')
    else: print(text,end='')
    return 0
if __name__=='__main__':raise SystemExit(main())
