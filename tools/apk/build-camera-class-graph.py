#!/usr/bin/env python3
"""Aggregate DEX routing reports into bounded package/class dependency graphs."""
from __future__ import annotations
import argparse, collections, hashlib, json, pathlib, re
from typing import Any

ROLE_PATTERNS = [
    ("FACTORY", re.compile(r"(?:Factory|BuilderFactory)$")),
    ("REPOSITORY", re.compile(r"Repository$")),
    ("CONTROLLER", re.compile(r"(?:Controller|Coordinator)$")),
    ("MANAGER", re.compile(r"Manager$")),
    ("CONTEXT", re.compile(r"Context(?:\$.*)?$")),
    ("USE_CASE", re.compile(r"UseCase|ImageCapture|VideoCapture|Preview")),
    ("PROVIDER", re.compile(r"Provider$")),
    ("ADAPTER", re.compile(r"Adapter$")),
    ("INTERFACE", re.compile(r"(?:Interface|Callback|Listener)(?:\$.*)?$")),
    ("NATIVE_BRIDGE", re.compile(r"(?:Native|Jni|JNI|Algo|Util)(?:\$.*)?$")),
]
CAMERA_EXTERNAL_PREFIXES = (
    "Landroid/hardware/camera2/", "Landroidx/camera/", "Landroid/media/ImageReader;",
    "Landroid/view/Surface;", "Ljava/lang/System;"
)
FIRST_PARTY_PREFIXES = ("Lcom/nothing/", "Lcom/mediatek/")
OBFUSCATED_SEGMENT = re.compile(r"^[a-zA-Z]{1,2}$")

def class_name(desc: str) -> str:
    return desc[1:-1].replace('/', '.') if desc.startswith('L') and desc.endswith(';') else desc

def package_name(name: str) -> str:
    base = name.split('$', 1)[0]
    return base.rsplit('.', 1)[0] if '.' in base else ""

def simple_name(name: str) -> str:
    return name.rsplit('.', 1)[-1]

def classify_role(name: str) -> str:
    simple = simple_name(name)
    for role, pattern in ROLE_PATTERNS:
        if pattern.search(simple): return role
    return "CLASS"

def obfuscation(name: str) -> str:
    parts = package_name(name).split('.')
    simple = simple_name(name).split('$', 1)[0]
    if parts and sum(bool(OBFUSCATED_SEGMENT.fullmatch(p)) for p in parts) >= max(1, len(parts)//2):
        return "LIKELY_OBFUSCATED_PACKAGE"
    if len(simple) <= 2 and simple not in {"UI", "AF", "AE", "AWB"}:
        return "LIKELY_OBFUSCATED_CLASS"
    return "READABLE"

def load_reports(paths: list[pathlib.Path]) -> list[dict[str, Any]]:
    reports=[]
    for path in paths:
        value=json.loads(path.read_text(encoding='utf-8'))
        if value.get('schemaVersion') != 1: raise ValueError(f"unsupported report: {path}")
        reports.append(value)
    return reports

def build_graph(reports: list[dict[str, Any]], top_classes: int=350, top_edges: int=1000, top_methods: int=300) -> dict[str, Any]:
    methods=[]; dex_files=[]; parse_errors=[]
    defined=matched=synthetic=0
    signal_counts=collections.Counter()
    application_open=[]; caller_paths=[]
    class_info: dict[str, dict[str, Any]]={}
    edge_counts=collections.Counter()
    edge_methods: dict[tuple[str,str], set[str]]=collections.defaultdict(set)
    for report in reports:
        defined += report.get('definedMethodCount',0); matched += report.get('matchedMethodCount',0)
        synthetic += report.get('syntheticCallbackEdgeCount',0)
        signal_counts.update(report.get('signalCounts',{}))
        dex_files.extend(report.get('dexFiles',[])); parse_errors.extend(report.get('parseErrors',[]))
        application_open.extend(report.get('applicationCameraOpenCallSites',[]))
        caller_paths.extend(report.get('cameraOpenCallerPaths',[]))
        for record in report.get('routeCandidateMethods',[]):
            method=record['method']; owner=class_name(method['classDescriptor']); pkg=package_name(owner)
            info=class_info.setdefault(owner, {'name':owner,'package':pkg,'role':classify_role(owner),
                'obfuscation':obfuscation(owner),'dexFiles':set(),'methodCount':0,'maxScore':0,
                'signals':collections.Counter(),'incomingWeight':0,'outgoingWeight':0})
            info['dexFiles'].add(record.get('dex')); info['methodCount']+=1
            info['maxScore']=max(info['maxScore'],record.get('score',0)); info['signals'].update(record.get('signalIds',[]))
            compact_invokes=[]
            for invoked in record.get('invokes',[]):
                target_desc=invoked.get('classDescriptor','')
                if not (target_desc.startswith(FIRST_PARTY_PREFIXES) or target_desc.startswith(CAMERA_EXTERNAL_PREFIXES)):
                    continue
                target=class_name(target_desc)
                if target == owner: continue
                edge_counts[(owner,target)] += 1
                edge_methods[(owner,target)].add(method['key'])
                compact_invokes.append(invoked['key'])
                class_info.setdefault(target, {'name':target,'package':package_name(target),
                    'role':classify_role(target),'obfuscation':obfuscation(target),'dexFiles':set(),
                    'methodCount':0,'maxScore':0,'signals':collections.Counter(),'incomingWeight':0,'outgoingWeight':0})
            methods.append({'dex':record.get('dex'),'method':method['key'],'owner':owner,'package':pkg,
                'score':record.get('score',0),'bridgeBonus':record.get('bridgeBonus',0),
                'signalIds':record.get('signalIds',[]),'strings':record.get('strings',[])[:12],
                'invokes':compact_invokes[:30]})
    for (source,target),weight in edge_counts.items():
        class_info[source]['outgoingWeight'] += weight; class_info[target]['incomingWeight'] += weight
    for info in class_info.values():
        info['centralityScore']=info['incomingWeight']+info['outgoingWeight']+info['methodCount']*3+info['maxScore']
        info['dexFiles']=sorted(x for x in info['dexFiles'] if x)
        info['signals']=dict(sorted(info['signals'].items()))
    all_ranked=sorted(class_info.values(),key=lambda x:(-x['centralityScore'],-x['maxScore'],x['name']))
    first_party=[x for x in all_ranked if x['name'].startswith(('com.nothing.','com.mediatek.'))]
    boundaries=[x for x in all_ranked if not x['name'].startswith(('com.nothing.','com.mediatek.'))]
    first_limit=max(1,int(top_classes*0.82))
    ranked_classes=(first_party[:first_limit]+boundaries[:top_classes-first_limit])[:top_classes]
    included={x['name'] for x in ranked_classes}
    edges=[]
    for (source,target),weight in edge_counts.most_common():
        if source not in included or target not in included: continue
        edge_type='FRAMEWORK_BOUNDARY' if target.startswith(('android.','androidx.')) else ('NATIVE_BOUNDARY' if target=='java.lang.System' else 'DIRECT_INVOKE')
        edges.append({'source':source,'target':target,'weight':weight,'type':edge_type,
            'evidenceMethods':sorted(edge_methods[(source,target)])[:8],'confidence':'STATIC_DIRECT_REFERENCE'})
        if len(edges)>=top_edges: break
    package_edges=collections.Counter()
    for edge in edges:
        sp=package_name(edge['source']); tp=package_name(edge['target'])
        if sp and tp and sp != tp: package_edges[(sp,tp)] += edge['weight']
    packages=collections.defaultdict(lambda:{'classCount':0,'candidateMethodCount':0,'maxClassCentrality':0,'roles':collections.Counter()})
    for node in ranked_classes:
        p=packages[node['package']]; p['classCount']+=1; p['candidateMethodCount']+=node['methodCount']; p['maxClassCentrality']=max(p['maxClassCentrality'],node['centralityScore']); p['roles'][node['role']]+=1
    package_nodes=[{'name':name,**{k:v for k,v in info.items() if k!='roles'},'roles':dict(info['roles'])} for name,info in packages.items()]
    package_nodes.sort(key=lambda x:(-x['candidateMethodCount'],-x['classCount'],x['name']))
    package_edge_records=[{'source':s,'target':t,'weight':w,'confidence':'STATIC_DIRECT_REFERENCE'} for (s,t),w in package_edges.most_common(300)]
    methods.sort(key=lambda x:(not x['owner'].startswith(('com.nothing.','com.mediatek.')),-x['score'],-x['bridgeBonus'],x['method']))
    root_methods=[]
    for call in application_open:
        method=call.get('method',call)
        root_methods.append({'kind':'APPLICATION_CAMERA_OPEN','value':method,'classification':'VERIFIED_STATIC_CALL_SITE'})
    seen=set()
    for path in sorted(caller_paths,key=lambda p:(p.get('depth',99),-p.get('score',0))):
        key=tuple(path.get('methods',[]))
        if key in seen: continue
        seen.add(key); root_methods.append({'kind':'CAMERA_OPEN_CALLER_PATH','value':list(key),'depth':path.get('depth'),
            'classification':'STATIC_DIRECT_OR_SYNTHETIC_PATH','signalIds':path.get('signalIds',[])})
        if len(root_methods)>=40: break
    summary={
        'dexFileCount':len(dex_files),'definedMethodCount':defined,'matchedMethodCount':matched,
        'candidateMethodCount':len(methods),'classNodeCount':len(ranked_classes),'classEdgeCount':len(edges),
        'packageNodeCount':len(package_nodes),'packageEdgeCount':len(package_edge_records),
        'syntheticCallbackEdgeCount':synthetic,'applicationCameraOpenCallSiteCount':len(application_open),
        'parseErrorCount':len(parse_errors)}
    return {'schemaVersion':1,'issue':28,'referenceVersion':'2026.08.04-1',
        'evidenceClassification':'STATIC_REFERENCE_ONLY','summary':summary,
        'dexFiles':sorted(dex_files,key=lambda x:x['name']),'parseErrors':parse_errors,
        'signalCounts':dict(sorted(signal_counts.items())),
        'classGraph':{'nodes':ranked_classes,'edges':edges},
        'packageGraph':{'nodes':package_nodes,'edges':package_edge_records},
        'routeCandidateMethods':methods[:top_methods],'cameraRoots':root_methods,
        'uncertainty':{
            'directEdges':'DEX invoke instructions; static presence does not prove runtime execution.',
            'syntheticCallbackEdges':synthetic,
            'syntheticBoundary':'Synthetic executor/callback edges are counted but not emitted as direct class edges.',
            'obfuscation':'Heuristic only; readable Nothing namespaces do not constitute an official mapping.',
            'runtimeBoundary':'Route-specific arguments, object identities, reflection, Binder, JNI and native control flow require dynamic evidence.'}}

def markdown(graph: dict[str,Any]) -> str:
    s=graph['summary']; nodes=graph['classGraph']['nodes']
    lines=['# Nothing Camera package and class dependency graph','',
        f"**Reference:** `{graph['referenceVersion']}`  ", '**Issue:** CAM-022 / #28  ',
        '**Evidence:** static DEX references only','', '## Scope','',
        f"The graph covers {s['definedMethodCount']:,} defined methods across {s['dexFileCount']} DEX files. "
        f"It retains {s['candidateMethodCount']:,} camera-routing candidates and bounds the committed graph to "
        f"{s['classNodeCount']} class nodes and {s['classEdgeCount']} weighted direct-reference edges.",'',
        '## Highest-centrality camera classes','',
        '| Class | Role | Candidate methods | Max score | In | Out | Signals |','|---|---|---:|---:|---:|---:|---|']
    for node in nodes[:30]:
        signals=', '.join(node['signals'])
        lines.append(f"| `{node['name']}` | `{node['role']}` | {node['methodCount']} | {node['maxScore']} | {node['incomingWeight']} | {node['outgoingWeight']} | {signals} |")
    lines += ['', '## Camera open spine','']
    for root in graph['cameraRoots'][:15]: lines.append(f"- `{root['kind']}`: `{root['value']}`")
    lines += ['', '## Package graph','',
        '| Package | Classes | Candidate methods | Roles |','|---|---:|---:|---|']
    for p in graph['packageGraph']['nodes'][:25]: lines.append(f"| `{p['name']}` | {p['classCount']} | {p['candidateMethodCount']} | {', '.join(f'{k}:{v}' for k,v in p['roles'].items())} |")
    lines += ['', '## Evidence boundary','',
        '- Class edges are resolved DEX invoke references. They do not prove execution on Galaga.',
        '- Callback/executor links that cannot be resolved as direct invokes remain synthetic and separately counted.',
        '- Obfuscation labels are conservative heuristics, not recovered symbol mappings.',
        '- Reflection, Binder, JNI and native-library call graphs remain incomplete until matching runtime/native evidence is captured.', '']
    return '\n'.join(lines)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('reports',nargs='+',type=pathlib.Path)
    ap.add_argument('--json',type=pathlib.Path); ap.add_argument('--markdown',type=pathlib.Path); ap.add_argument('--output-dir',type=pathlib.Path)
    ap.add_argument('--top-classes',type=int,default=350); ap.add_argument('--top-edges',type=int,default=1000); ap.add_argument('--top-methods',type=int,default=300)
    a=ap.parse_args(); graph=build_graph(load_reports(a.reports),a.top_classes,a.top_edges,a.top_methods)
    if a.json: a.json.parent.mkdir(parents=True,exist_ok=True); a.json.write_text(json.dumps(graph,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if a.markdown: a.markdown.parent.mkdir(parents=True,exist_ok=True); a.markdown.write_text(markdown(graph),encoding='utf-8')
    if a.output_dir:
        out=a.output_dir; out.mkdir(parents=True,exist_ok=True)
        index={k:v for k,v in graph.items() if k not in {'classGraph','packageGraph','routeCandidateMethods'}}
        index['parts']={'classNodes':'class-nodes.v1.json','classEdges':'class-edges.v1.json','packageGraph':'packages.v1.json','methods':'route-methods.v1.json'}
        (out/'index.v1.json').write_text(json.dumps(index,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
        (out/'class-nodes.v1.json').write_text(json.dumps({'schemaVersion':1,'nodes':graph['classGraph']['nodes']},separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
        (out/'class-edges.v1.json').write_text(json.dumps({'schemaVersion':1,'edges':graph['classGraph']['edges']},separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
        (out/'packages.v1.json').write_text(json.dumps({'schemaVersion':1,**graph['packageGraph']},separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
        (out/'route-methods.v1.json').write_text(json.dumps({'schemaVersion':1,'methods':graph['routeCandidateMethods']},separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
    if not a.json and not a.markdown and not a.output_dir: print(json.dumps(graph,indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
