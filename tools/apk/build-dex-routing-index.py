#!/usr/bin/env python3
"""Build a method-level camera-routing index directly from Android DEX bytecode.

This is a decompiler-independent companion to ``build-routing-index.py``. It
parses the DEX tables and code items needed to recover method identities,
``const-string`` references and invoke targets. It intentionally does not
attempt to reconstruct proprietary source code.

Findings remain static evidence only: a referenced API, key or value does not
prove that a path executes on a target build or that it causes optical routing.
"""
from __future__ import annotations
import argparse
import collections
import dataclasses
import hashlib
import json
import re
import struct
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterator, Sequence
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from dex_bytecode import DefinedMethod, DexFormatError, DexReader, MethodRef, decode_code_references, instruction_width
ACC_NATIVE = 256
MAX_METHOD_STRINGS = 80
MAX_METHOD_INVOKES = 120
MAX_CANDIDATES = 200
MAX_CALLER_PATHS = 200

@dataclasses.dataclass(frozen=True)
class Signal:
    id: str
    label: str
    weight: int
SIGNALS = {signal.id: signal for signal in (Signal('camera-open', 'Camera open call site', 24), Signal('camera-open-dispatch', 'Application camera-open dispatch', 14), Signal('camera-enumeration', 'Camera ID enumeration/characteristics', 8), Signal('session-construction', 'Capture session construction', 12), Signal('session-parameters', 'Session parameter assignment', 16), Signal('physical-output', 'Physical camera output selection', 20), Signal('capture-request', 'Capture request construction/submission', 7), Signal('vendor-routing-key', 'MediaTek/Nothing routing metadata', 20), Signal('sat-multicam', 'SAT/multicamera terminology', 13), Signal('expert-ui', 'Expert/manual optical route terminology', 10), Signal('camera-id-constant', 'Candidate system camera ID literal', 6), Signal('camerax-routing', 'CameraX routing boundary', 7), Signal('jni-native', 'JNI/native boundary', 11))}
ROUTING_VENDOR_RE = re.compile('(?:com\\.mediatek\\.(?:configure\\.setting|cameraflex|multicamfeature|insensorzoomfeature|seamlessfeature|streamingfeature)|com\\.nothing\\.camera\\.|nothing\\.camera\\.)', re.IGNORECASE)
SAT_RE = re.compile('(?:\\bsat\\b|multi.?cam|camera.?flex|logical.?camera|physical.?camera|seamless|sensorScenario|forceSensorMode|pipDevices)', re.IGNORECASE)
EXPERT_RE = re.compile('(?:\\bexpert\\b|\\bmanual(?:mode)?\\b|0[._]?6\\s*[x×]|\\b15\\s*mm\\b|\\b24\\s*mm\\b|\\b50\\s*mm\\b|telephoto|ultra.?wide)', re.IGNORECASE)

def is_analysis_text(value: str) -> bool:
    return len(value) <= 512 and '\x00' not in value

def classify_method(method: DefinedMethod, reader: DexReader) -> dict[str, Any]:
    strings = [reader.strings[index] for index in method.string_indexes[:MAX_METHOD_STRINGS]]
    invokes = [reader.methods[index] for index in method.invoked_method_indexes[:MAX_METHOD_INVOKES]]
    signal_ids: set[str] = set()
    evidence: dict[str, list[str]] = collections.defaultdict(list)
    if method.ref.name == 'openCamera' and method.ref.class_descriptor != 'Landroid/hardware/camera2/CameraManager;':
        signal_ids.add('camera-open-dispatch')
        evidence['camera-open-dispatch'].append(method.ref.key)
    for target in invokes:
        key = target.key
        class_name = target.class_descriptor
        name = target.name
        if class_name == 'Landroid/hardware/camera2/CameraManager;' and name == 'openCamera':
            signal_ids.add('camera-open')
            evidence['camera-open'].append(key)
        if class_name == 'Landroid/hardware/camera2/CameraManager;' and name in {'getCameraIdList', 'getCameraCharacteristics', 'getConcurrentCameraIds'}:
            signal_ids.add('camera-enumeration')
            evidence['camera-enumeration'].append(key)
        if name in {'createCaptureSession', 'createCaptureSessionByOutputConfigurations'} or (class_name == 'Landroid/hardware/camera2/params/SessionConfiguration;' and name == '<init>'):
            signal_ids.add('session-construction')
            evidence['session-construction'].append(key)
        if class_name == 'Landroid/hardware/camera2/params/SessionConfiguration;' and name == 'setSessionParameters':
            signal_ids.add('session-parameters')
            evidence['session-parameters'].append(key)
        if class_name == 'Landroid/hardware/camera2/params/OutputConfiguration;' and name == 'setPhysicalCameraId':
            signal_ids.add('physical-output')
            evidence['physical-output'].append(key)
        if class_name.startswith('Landroid/hardware/camera2/') and name in {'createCaptureRequest', 'capture', 'captureBurst', 'setRepeatingRequest', 'setRepeatingBurst'}:
            signal_ids.add('capture-request')
            evidence['capture-request'].append(key)
        if 'Landroidx/camera/' in class_name and any((token in class_name or token in name for token in ('CameraSelector', 'Camera2', 'CameraInfo', 'CameraControl'))):
            signal_ids.add('camerax-routing')
            evidence['camerax-routing'].append(key)
        if class_name == 'Ljava/lang/System;' and name == 'loadLibrary':
            signal_ids.add('jni-native')
            evidence['jni-native'].append(key)
    if method.access_flags & ACC_NATIVE:
        signal_ids.add('jni-native')
        evidence['jni-native'].append('native method')
    for value in strings:
        if is_analysis_text(value) and ROUTING_VENDOR_RE.search(value):
            signal_ids.add('vendor-routing-key')
            evidence['vendor-routing-key'].append(value)
        if is_analysis_text(value) and SAT_RE.search(value):
            signal_ids.add('sat-multicam')
            evidence['sat-multicam'].append(value)
        if is_analysis_text(value) and EXPERT_RE.search(value):
            signal_ids.add('expert-ui')
            evidence['expert-ui'].append(value)
        if value in {'2', '3', '4', '5'}:
            signal_ids.add('camera-id-constant')
            evidence['camera-id-constant'].append(value)
    bridge_bonus = 0
    bridge_pairs = (('camera-open', 'expert-ui', 18), ('camera-open-dispatch', 'expert-ui', 14), ('camera-open', 'vendor-routing-key', 24), ('camera-open', 'sat-multicam', 20), ('session-construction', 'vendor-routing-key', 18), ('session-parameters', 'vendor-routing-key', 24), ('physical-output', 'expert-ui', 18), ('physical-output', 'sat-multicam', 20), ('camera-open', 'camera-id-constant', 10), ('jni-native', 'vendor-routing-key', 15))
    for left, right, bonus in bridge_pairs:
        if left in signal_ids and right in signal_ids:
            bridge_bonus += bonus
    score = sum((SIGNALS[signal_id].weight for signal_id in signal_ids)) + bridge_bonus
    return {'dex': method.dex_name, 'methodIndex': method.method_index, 'method': method.ref.to_json(), 'accessFlags': method.access_flags, 'codeOffset': method.code_offset, 'signalIds': sorted(signal_ids), 'score': score, 'bridgeBonus': bridge_bonus, 'evidence': {key: list(dict.fromkeys(values))[:20] for key, values in sorted(evidence.items())}, 'strings': strings, 'invokes': [target.to_json() for target in invokes]}

def iter_dex_inputs(paths: Sequence[Path]) -> Iterator[tuple[str, bytes, Path]]:
    for path in paths:
        if path.is_dir():
            for dex in sorted(path.rglob('*.dex')):
                yield (dex.name, dex.read_bytes(), path)
            continue
        if path.suffix.lower() == '.dex':
            yield (path.name, path.read_bytes(), path)
            continue
        if path.suffix.lower() in {'.apk', '.zip'}:
            with zipfile.ZipFile(path) as archive:
                dex_names = sorted((name for name in archive.namelist() if re.fullmatch('(?:.*/)?classes(?:\\d+)?\\.dex', name)))
                for dex_name in dex_names:
                    yield (f'{path.name}!/{dex_name}', archive.read(dex_name), path)
            continue
        raise ValueError(f'unsupported input: {path}')

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while (chunk := stream.read(1024 * 1024)):
            digest.update(chunk)
    return digest.hexdigest()

def input_metadata(paths: Sequence[Path]) -> list[dict[str, Any]]:
    result = []
    for path in paths:
        if path.is_file():
            result.append({'path': str(path.resolve()), 'sizeBytes': path.stat().st_size, 'sha256': sha256_file(path)})
        else:
            result.append({'path': str(path.resolve()), 'directory': True})
    return result

def build_caller_paths(analyzed: dict[str, dict[str, Any]], reverse_calls: dict[str, set[str]], open_callers: list[str], max_depth: int) -> list[dict[str, Any]]:
    paths: list[dict[str, Any]] = []
    seen_paths: set[tuple[str, ...]] = set()
    for open_caller in open_callers:
        queue: collections.deque[tuple[str, tuple[str, ...]]] = collections.deque([(open_caller, (open_caller,))])
        while queue and len(paths) < MAX_CALLER_PATHS:
            current, reverse_path = queue.popleft()
            depth = len(reverse_path) - 1
            forward_path = tuple(reversed(reverse_path))
            if forward_path not in seen_paths:
                seen_paths.add(forward_path)
                path_signals = sorted({signal for method_key in forward_path for signal in analyzed.get(method_key, {}).get('signalIds', [])})
                if depth > 0 or len(path_signals) > 1:
                    score = sum((analyzed.get(key, {}).get('score', 0) for key in forward_path))
                    paths.append({'depth': depth, 'score': score, 'signalIds': path_signals, 'methods': list(forward_path)})
            if depth >= max_depth:
                continue
            for caller in sorted(reverse_calls.get(current, ())):
                if caller not in reverse_path:
                    queue.append((caller, reverse_path + (caller,)))
    paths.sort(key=lambda item: (-item['score'], item['depth'], item['methods']))
    return paths[:MAX_CALLER_PATHS]

def is_relevant_call_target(ref: MethodRef) -> bool:
    return ref.class_descriptor.startswith(('Lcom/nothing/', 'Landroid/hardware/camera2/', 'Landroidx/camera/'))

def build_report(paths: Sequence[Path], max_caller_depth: int=4) -> dict[str, Any]:
    analyzed_by_key: dict[str, dict[str, Any]] = {}
    candidate_by_key: dict[str, dict[str, Any]] = {}
    reverse_calls: dict[str, set[str]] = collections.defaultdict(set)
    constructor_callers: dict[str, set[str]] = collections.defaultdict(set)
    callback_methods: dict[str, set[str]] = collections.defaultdict(set)
    dex_summaries: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    total_defined_methods = 0
    for dex_name, data, _source_path in iter_dex_inputs(paths):
        try:
            reader = DexReader(data, dex_name)
            defined_count = 0
            for method in reader.defined_methods():
                defined_count += 1
                analysis = classify_method(method, reader)
                key = method.ref.key
                storage_key = key
                if storage_key in analyzed_by_key:
                    storage_key = f'{key} [{dex_name}]'
                    analysis['method']['key'] = storage_key
                analyzed_by_key[storage_key] = {'signalIds': analysis['signalIds'], 'score': analysis['score']}
                if analysis['signalIds']:
                    candidate_by_key[storage_key] = analysis
                if method.ref.name in {'execute', 'run', 'accept', 'invoke', 'call'}:
                    callback_methods[method.ref.class_descriptor].add(storage_key)
                for target_index in method.invoked_method_indexes:
                    target = reader.methods[target_index]
                    if target.name == '<init>':
                        constructor_callers[target.class_descriptor].add(storage_key)
                    if is_relevant_call_target(target):
                        reverse_calls[target.key].add(storage_key)
            total_defined_methods += defined_count
        except (DexFormatError, struct.error, IndexError) as exc:
            parse_errors.append(str(exc))
            continue
        dex_summaries.append({'name': dex_name, 'sizeBytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'stringCount': len(reader.strings), 'methodReferenceCount': len(reader.methods), 'definedMethodCount': defined_count})
    synthetic_callback_edge_count = 0
    for class_descriptor, callback_keys in callback_methods.items():
        callers = constructor_callers.get(class_descriptor, set())
        for callback_key in callback_keys:
            before = len(reverse_calls[callback_key])
            reverse_calls[callback_key].update(callers)
            synthetic_callback_edge_count += len(reverse_calls[callback_key]) - before
    candidates = list(candidate_by_key.values())
    candidates.sort(key=lambda item: (-item['score'], item['method']['classDescriptor'], item['method']['name'], item['method']['descriptor']))
    open_callers = [item['method']['key'] for item in candidates if 'camera-open' in item['signalIds']]
    application_open_sites = [item for item in candidates if 'camera-open' in item['signalIds'] and item['method']['classDescriptor'].startswith('Lcom/nothing/')]
    caller_paths = build_caller_paths(analyzed_by_key, reverse_calls, open_callers, max_caller_depth)
    signal_counts: collections.Counter[str] = collections.Counter()
    for item in candidates:
        signal_counts.update(item['signalIds'])
    return {'schemaVersion': 1, 'evidenceClassification': 'STATIC_REFERENCE_ONLY', 'inputs': input_metadata(paths), 'dexFiles': dex_summaries, 'parseErrors': parse_errors, 'definedMethodCount': total_defined_methods, 'matchedMethodCount': len(candidates), 'signalCounts': dict(sorted(signal_counts.items())), 'syntheticCallbackEdgeCount': synthetic_callback_edge_count, 'cameraOpenCallSiteCount': len(open_callers), 'applicationCameraOpenCallSiteCount': len(application_open_sites), 'applicationCameraOpenCallSites': application_open_sites, 'cameraOpenCallSites': [item for item in candidates if 'camera-open' in item['signalIds']], 'cameraOpenCallerPaths': caller_paths, 'routeCandidateMethods': candidates[:MAX_CANDIDATES]}

def render_markdown(report: dict[str, Any]) -> str:
    lines = ['# DEX Camera Routing Index', '', 'Evidence classification: **STATIC_REFERENCE_ONLY**.', '', 'A method reference or literal proves only that bytecode contains the symbol. It does not prove execution, privilege, route selection or optical output.', '', '## Summary', '', f"- DEX files parsed: {len(report['dexFiles'])}", f"- Defined methods: {report['definedMethodCount']}", f"- Matched methods: {report['matchedMethodCount']}", f"- CameraManager.openCamera call sites: {report['cameraOpenCallSiteCount']}", f"- Nothing application call sites: {report['applicationCameraOpenCallSiteCount']}"]
    if report['parseErrors']:
        lines.extend(['', '## Parse errors', ''])
        lines.extend((f'- `{error}`' for error in report['parseErrors']))
    lines.extend(['', '## Signal counts', ''])
    for signal_id, count in report['signalCounts'].items():
        lines.append(f'- `{signal_id}`: {count}')
    lines.extend(['', '## Camera open call sites', ''])
    if not report['cameraOpenCallSites']:
        lines.append('No direct `CameraManager.openCamera` invocation was recovered.')
    for item in report['cameraOpenCallSites']:
        method = item['method']
        lines.extend([f"### `{method['key']}`", '', f"- DEX: `{item['dex']}`", f"- Signals: {', '.join((f'`{value}`' for value in item['signalIds']))}", f"- Score: {item['score']}", ''])
    lines.extend(['## Highest-ranked caller paths', ''])
    for path in report['cameraOpenCallerPaths'][:30]:
        lines.append(f"- score {path['score']}, depth {path['depth']}, signals " + ', '.join((f'`{value}`' for value in path['signalIds'])))
        for method in path['methods']:
            lines.append(f'  - `{method}`')
    lines.extend(['', '## Highest-ranked route candidates', ''])
    for item in report['routeCandidateMethods'][:80]:
        method = item['method']
        lines.append(f"- **{item['score']}** `{method['key']}` — " + ', '.join((f'`{value}`' for value in item['signalIds'])))
    lines.append('')
    return '\n'.join(lines)

def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path, help='APK, ZIP, DEX or directory')
    parser.add_argument('--json', type=Path, help='write the JSON report')
    parser.add_argument('--markdown', type=Path, help='write the Markdown report')
    parser.add_argument('--max-caller-depth', type=int, default=4, help='maximum reverse call-graph depth (default: 4)')
    return parser.parse_args(argv)

def main(argv: Sequence[str] | None=None) -> int:
    args = parse_args(argv or sys.argv[1:])
    for path in args.inputs:
        if not path.exists():
            print(f'input not found: {path}', file=sys.stderr)
            return 2
    if not 0 <= args.max_caller_depth <= 12:
        print('--max-caller-depth must be between 0 and 12', file=sys.stderr)
        return 2
    try:
        report = build_report(args.inputs, args.max_caller_depth)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f'DEX routing index failed: {exc}', file=sys.stderr)
        return 1
    json_text = json.dumps(report, indent=2, sort_keys=False) + '\n'
    markdown_text = render_markdown(report)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json_text, encoding='utf-8')
    else:
        print(json_text, end='')
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown_text, encoding='utf-8')
    return 1 if report['parseErrors'] and not report['dexFiles'] else 0
if __name__ == '__main__':
    raise SystemExit(main())
