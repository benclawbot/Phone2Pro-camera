#!/usr/bin/env python3
"""Aggregate normalized DEX routing reports into bounded package/class graphs."""
from __future__ import annotations
import argparse, collections, json, pathlib, re
from typing import Any

ROLE_PATTERNS=[
 ("FACTORY",re.compile(r"(?:Factory|BuilderFactory)$")),("REPOSITORY",re.compile(r"Repository$")),
 ("CONTROLLER",re.compile(r"(?:Controller|Coordinator)$")),("MANAGER",re.compile(r"Manager$")),
 ("CONTEXT",re.compile(r"Context(?:\$.*)?$")),("USE_CASE",re.compile(r"UseCase|ImageCapture|VideoCapture|Preview")),
 ("PROVIDER",re.compile(r"Provider$")),("ADAPTER",re.compile(r"Adapter$")),
 ("INTERFACE",re.compile(r"(?:Interface|Callback|Listener)(?:\$.*)?$")),
 ("NATIVE_BRIDGE",re.compile(r"(?:Native|Jni|JNI|Algo|Util)(?:\$.*)?$")),]
CAMERA_EXTERNAL_PREFIXES=("Landroid/hardware/camera2/","Landroidx/camera/","Landroid/media/ImageReader;","Landroid/view/Surface;","Ljava/lang/System;")
FIRST_PARTY_PREFIXES=("Lcom/nothing/","Lcom/mediatek/")
OBFUSCATED_SEGMENT=re.compile(r"^[a-zA-Z]{1,2}$")
REQUIRED_CLASS_ROOTS={
 "com.nothing.camera.activity.CameraActivity","com.nothing.common.setting.SettingContext",
 "com.nothing.common.setting.LaunchIntentParser","com.nothing.common.setting.CameraDeviceInfoManager",
 "com.nothing.cameracore.context.module.CameraContext","com.nothing.cameracore.context.module.CameraContext$3",
 "com.nothing.cameracore.context.module.usecase.DualYuvImageCapture","com.nothing.camera.mode.PhotoMode",
 "com.nothing.camera.mode.NcfBokehMode"}

def class_name(desc:str)->str:return desc[1:-1].replace('/','.') if desc.startswith('L') and desc.endswith(';') else desc
def package_name(name:str)->str:
 base=name.split('$',1)[0]; return base.rsplit('.',1)[0] if '.' in base else ''
def simple_name(name:str)->str:return name.rsplit('.',1)[-1]
def classify_role(name:str)->str:
 for role,pattern in ROLE_PATTERNS:
  if pattern.search(simple_name(name)):return role
 return 'CLASS'
def obfuscation(name:str)->str:
 parts=package_name(name).split('.'); simple=simple_name(name).split('$',1)[0]
 if parts and sum(bool(OBFUSCATED_SEGMENT.fullmatch(p)) for p in parts)>=max(1,len(parts)//2):return 'LIKELY_OBFUSCATED_PACKAGE'
 if len(simple)<=2 and simple not in {'UI','AF','AE','AWB'}:return 'LIKELY_OBFUSCATED_CLASS'
 return 'READABLE'
def load_reports(paths:list[pathlib.Path])->list[dict[str,Any]]:
 reports=[]
 for path in paths:
  value=json.loads(path.read_text(encoding='utf-8'))
  if value.get('schemaVersion')!=1:raise ValueError(f'unsupported report: {path}')
  reports.append(value)
 return reports

def build_graph(reports:list[dict[str,Any]],top_classes:int=350,top_edges:int=1000,top_methods:int=300)->dict[str,Any]:
 methods=[]; dex_files=[]; parse_errors=[]; defined=matched=synthetic=0
 signal_counts=collections.Counter(); application_open=[]; caller_paths=[]
 class_info:dict[str,dict[str,Any]]={}; edge_counts=collections.Counter(); edge_methods=collections.defaultdict(set)
 for report in reports:
  defined+=report.get('definedMethodCount',0); matched+=report.get('matchedMethodCount',0); synthetic+=report.get('syntheticCallbackEdgeCount',0)
  signal_counts.update(report.get('signalCounts',{})); dex_files.extend(report.get('dexFiles',[])); parse_errors.extend(report.get('parseErrors',[]))
  application_open.extend(report.get('applicationCameraOpenCallSites',[])); caller_paths.extend(report.get('cameraOpenCallerPaths',[]))
  for record in report.get('routeCandidateMethods',[]):
   method=record['method']; owner=class_name(method['classDescriptor']); pkg=package_name(owner)
   info=class_info.setdefault(owner,{'name':owner,'package':pkg,'role':classify_role(owner),'obfuscation':obfuscation(owner),'dexFiles':set(),'methodCount':0,'maxScore':0,'signals':collections.Counter(),'incomingWeight':0,'outgoingWeight':0})
   info['dexFiles'].add(record.get('dex')); info['methodCount']+=1; info['maxScore']=max(info['maxScore'],record.get('score',0)); info['signals'].update(record.get('signalIds',[]))
   compact=[]
   for invoked in record.get('invokes',[]):
    target_desc=invoked.get('classDescriptor','')
    if not (target_desc.startswith(FIRST_PARTY_PREFIXES) or target_desc.startswith(CAMERA_EXTERNAL_PREFIXES)):continue
    target=class_name(target_desc)
    if target==owner:continue
    edge_counts[(owner,target)]+=1; edge_methods[(owner,target)].add(method['key']); compact.append(invoked['key'])
    class_info.setdefault(target,{'name':target,'package':package_name(target),'role':classify_role(target),'obfuscation':obfuscation(target),'dexFiles':set(),'methodCount':0,'maxScore':0,'signals':collections.Counter(),'incomingWeight':0,'outgoingWeight':0})
   methods.append({'dex':record.get('dex'),'method':method['key'],'owner':owner,'package':pkg,'score':record.get('score',0),'bridgeBonus':record.get('bridgeBonus',0),'signalIds':record.get('signalIds',[]),'strings':record.get('strings',[])[:12],'invokes':compact[:30]})
 for (source,target),weight in edge_counts.items():class_info[source]['outgoingWeight']+=weight; class_info[target]['incomingWeight']+=weight
 for info in class_info.values():
  info['centralityScore']=info['incomingWeight']+info['outgoingWeight']+info['methodCount']*3+info['maxScore']; info['dexFiles']=sorted(x for x in info['dexFiles'] if x); info['signals']=dict(sorted(info['signals'].items()))
 ranked=sorted(class_info.values(),key=lambda x:(-x['centralityScore'],-x['maxScore'],x['name']))
 first=[x for x in ranked if x['name'].startswith(('com.nothing.','com.mediatek.'))]; boundaries=[x for x in ranked if not x['name'].startswith(('com.nothing.','com.mediatek.'))]
 first_limit=max(1,int(top_classes*.82)); nodes=(first[:first_limit]+boundaries[:top_classes-first_limit])[:top_classes]
 names={x['name'] for x in nodes}; forced=[class_info[n] for n in sorted(REQUIRED_CLASS_ROOTS-names) if n in class_info]
 if forced:
  removable=[i for i in range(len(nodes)-1,-1,-1) if nodes[i]['name'] not in REQUIRED_CLASS_ROOTS]
  for item,index in zip(forced,removable):nodes[index]=item
  nodes.sort(key=lambda x:(-x['centralityScore'],-x['maxScore'],x['name']))
 included={x['name'] for x in nodes}; edges=[]
 for (source,target),weight in edge_counts.most_common():
  if source not in included or target not in included:continue
  edge_type='FRAMEWORK_BOUNDARY' if target.startswith(('android.','androidx.')) else ('NATIVE_BOUNDARY' if target=='java.lang.System' else 'DIRECT_INVOKE')
  edges.append({'source':source,'target':target,'weight':weight,'type':edge_type,'evidenceMethods':sorted(edge_methods[(source,target)])[:8],'confidence':'STATIC_DIRECT_REFERENCE'})
  if len(edges)>=top_edges:break
 package_edges=collections.Counter()
 for edge in edges:
  sp=package_name(edge['source']); tp=package_name(edge['target'])
  if sp and tp and sp!=tp:package_edges[(sp,tp)]+=edge['weight']
 packages=collections.defaultdict(lambda:{'classCount':0,'candidateMethodCount':0,'maxClassCentrality':0,'roles':collections.Counter()})
 for node in nodes:
  p=packages[node['package']]; p['classCount']+=1; p['candidateMethodCount']+=node['methodCount']; p['maxClassCentrality']=max(p['maxClassCentrality'],node['centralityScore']); p['roles'][node['role']]+=1
 package_nodes=[{'name':name,**{k:v for k,v in info.items() if k!='roles'},'roles':dict(info['roles'])} for name,info in packages.items()]
 package_nodes.sort(key=lambda x:(-x['candidateMethodCount'],-x['classCount'],x['name']))
 package_edge_records=[{'source':s,'target':t,'weight':w,'confidence':'STATIC_DIRECT_REFERENCE'} for (s,t),w in package_edges.most_common(300)]
 methods.sort(key=lambda x:(not x['owner'].startswith(('com.nothing.','com.mediatek.')),-x['score'],-x['bridgeBonus'],x['method']))
 roots=[{'kind':'APPLICATION_CAMERA_OPEN','value':call.get('method',call),'classification':'VERIFIED_STATIC_CALL_SITE'} for call in application_open]; seen=set()
 for path in sorted(caller_paths,key=lambda p:(p.get('depth',99),-p.get('score',0))):
  key=tuple(path.get('methods',[]))
  if key in seen:continue
  seen.add(key); roots.append({'kind':'CAMERA_OPEN_CALLER_PATH','value':list(key),'depth':path.get('depth'),'classification':'STATIC_DIRECT_OR_SYNTHETIC_PATH','signalIds':path.get('signalIds',[])})
  if len(roots)>=40:break
 summary={'dexFileCount':len(dex_files),'definedMethodCount':defined,'matchedMethodCount':matched,'candidateMethodCount':len(methods),'classNodeCount':len(nodes),'classEdgeCount':len(edges),'packageNodeCount':len(package_nodes),'packageEdgeCount':len(package_edge_records),'syntheticCallbackEdgeCount':synthetic,'applicationCameraOpenCallSiteCount':len(application_open),'parseErrorCount':len(parse_errors)}
 return {'schemaVersion':1,'issue':28,'referenceVersion':'2026.08.04-1','evidenceClassification':'STATIC_REFERENCE_ONLY','summary':summary,'dexFiles':sorted(dex_files,key=lambda x:x['name']),'parseErrors':parse_errors,'signalCounts':dict(sorted(signal_counts.items())),'classGraph':{'nodes':nodes,'edges':edges},'packageGraph':{'nodes':package_nodes,'edges':package_edge_records},'routeCandidateMethods':methods[:top_methods],'cameraRoots':roots,'uncertainty':{'directEdges':'DEX invoke instructions; static presence does not prove runtime execution.','syntheticCallbackEdges':synthetic,'syntheticBoundary':'Synthetic executor/callback edges are counted but not emitted as direct class edges.','obfuscation':'Heuristic only; readable Nothing namespaces do not constitute an official mapping.','runtimeBoundary':'Route-specific arguments, object identities, reflection, Binder, JNI and native control flow require dynamic evidence.'}}

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument('reports',nargs='+',type=pathlib.Path); ap.add_argument('--json',type=pathlib.Path); ap.add_argument('--output-dir',type=pathlib.Path); ap.add_argument('--top-classes',type=int,default=350); ap.add_argument('--top-edges',type=int,default=1000); ap.add_argument('--top-methods',type=int,default=300)
 a=ap.parse_args(); graph=build_graph(load_reports(a.reports),a.top_classes,a.top_edges,a.top_methods)
 if a.json:a.json.parent.mkdir(parents=True,exist_ok=True); a.json.write_text(json.dumps(graph,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 if a.output_dir:
  out=a.output_dir; out.mkdir(parents=True,exist_ok=True); index={k:v for k,v in graph.items() if k not in {'classGraph','packageGraph','routeCandidateMethods'}}; index['parts']={'classNodes':'class-nodes.v1.json','classEdges':'class-edges.v1.json','packageGraph':'packages.v1.json','methods':'route-methods.v1.json'}
  (out/'index.v1.json').write_text(json.dumps(index,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8'); (out/'class-nodes.v1.json').write_text(json.dumps({'schemaVersion':1,'nodes':graph['classGraph']['nodes']},separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8'); (out/'class-edges.v1.json').write_text(json.dumps({'schemaVersion':1,'edges':graph['classGraph']['edges']},separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8'); (out/'packages.v1.json').write_text(json.dumps({'schemaVersion':1,**graph['packageGraph']},separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8'); (out/'route-methods.v1.json').write_text(json.dumps({'schemaVersion':1,'methods':graph['routeCandidateMethods']},separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
 if not a.json and not a.output_dir:print(json.dumps(graph,indent=2))
 return 0
if __name__=='__main__':raise SystemExit(main())
