#!/usr/bin/env python3
"""Read-only audit of TalkMoves sources; never changes original data or labels.

Run: python research/student_simulation/audit.py
Requires openpyxl. Row references are original Excel row numbers, header = 1.
Automatic flags are review candidates, NOT corrected labels or exclusion decisions.
"""
import collections
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'audit_output'
OUT.mkdir(exist_ok=True)
import openpyxl

def serial(x):
    return x.isoformat() if hasattr(x, 'isoformat') else str(x)

def present(x):
    return x is not None and str(x).strip() != ''

def tagcode(x):
    m = re.match(r'^\s*(\d+)(?:\s*[-–.]|\s*$)', str(x))
    return int(m.group(1)) if m else None

def read_rows(path):
    w = openpyxl.load_workbook(path, read_only=True, data_only=True)
    s = w.active
    it = s.iter_rows(values_only=True)
    headers = next(it)
    keys = {str(h).strip().lower(): i for i, h in enumerate(headers) if h is not None}
    # One Subset 2 file has 'S' as its speaker-column header. Preserve and flag it.
    if 'speaker' not in keys and 's' in keys and 'sentence' in keys and keys['s'] == keys['sentence'] - 1:
        keys['speaker'] = keys['s']
    required = ['turn', 'speaker', 'sentence', 'teacher tag', 'student tag']
    if any(k not in keys for k in required):
        w.close()
        raise ValueError(f'Missing columns: {keys}')
    rows = []
    for rowno, row in enumerate(it, 2):
        def get(k):
            i = keys[k]
            return row[i] if i < len(row) else None
        vals = {k: get(k) for k in required}
        if not any(present(v) for v in vals.values()):
            continue
        rows.append({'row': rowno, **vals})
    w.close()
    return headers, rows

stats = collections.Counter()
teacher_labels, student_labels, speakers, headers_count = (collections.Counter() for _ in range(4))
flags, inventory, errors = [], [], []
duplicate_map = collections.defaultdict(list)
allrows = {}
visual = re.compile(r'\b(point(?:ing)?|shad(?:ed|ing)|diagram|picture|this one|that one|right here|over here|on the board)\b', re.I)
noise = re.compile(r'\b(inaudible|unintelligible|crosstalk|cross talk|overlapping|silence)\b', re.I)
generic = re.compile(r'^(s\d*|ss\d*|students?|class|all|group|unknown|unidentified|multiple students)$', re.I)
teacher = re.compile(r'^(t\d*|teacher\d*)$', re.I)
other = re.compile(r'(record|video|voice|speaker|observer|research|^o$)', re.I)

for subset in ['Subset 1', 'Subset 2']:
    files = sorted((ROOT / 'data' / subset).glob('*.xlsx'))
    for path in files:
        rel = str(path.relative_to(ROOT))
        try:
            h, rows = read_rows(path)
        except Exception as e:
            errors.append({'file': rel, 'error': str(e)})
            continue
        headers_count[json.dumps(h, default=serial)] += 1
        allrows[rel] = rows
        local = collections.Counter()
        prev = None
        groups = 0
        for r in rows:
            t, s = present(r['teacher tag']), present(r['student tag'])
            sp = str(r['speaker']).strip() if present(r['speaker']) else ''
            sentence = str(r['sentence']) if present(r['sentence']) else ''
            codes = []
            if t: teacher_labels[str(r['teacher tag'])] += 1
            if s: student_labels[str(r['student tag'])] += 1
            speakers[sp] += 1
            if not sentence.strip(): codes.append('missing_sentence')
            if present(r['sentence']) and not isinstance(r['sentence'], str): codes.append('nontext_sentence')
            if not sp: codes.append('missing_speaker')
            if not present(r['turn']): codes.append('missing_turn')
            if t and s: codes.append('both_label_columns')
            if not t and not s: codes.append('neither_label_column')
            if t and tagcode(r['teacher tag']) not in {1,2,3,4,5,7,8,9}: codes.append('unexpected_teacher_code')
            if s and tagcode(r['student tag']) not in {1,2,3,4,5}: codes.append('unexpected_student_code')
            if s and generic.fullmatch(sp): codes.append('student_identity_generic')
            if other.search(sp): codes.append('possible_nonclassroom_speaker')
            if teacher.fullmatch(sp) and s: codes.append('teacher_alias_with_student_tag')
            if visual.search(sentence): codes.append('possible_visual_dependency')
            if noise.search(sentence): codes.append('transcription_gap_marker')
            key = (r['turn'], r['speaker'])
            if prev is None or key != (prev['turn'], prev['speaker']): groups += 1
            if prev is not None:
                a,b=prev['turn'],r['turn']
                if isinstance(a,(int,float)) and isinstance(b,(int,float)) and b<a: codes.append('turn_number_decreases')
                if r['row'] > prev['row']+1: codes.append('blank_row_gap')
                if r['turn']==prev['turn'] and r['speaker'] != prev['speaker']: codes.append('same_turn_multiple_speakers')
            for code in codes:
                local[code]+=1
                flags.append({'file':rel,'excel_row':r['row'],'flag':code,'speaker':r['speaker'],'turn':r['turn'],'sentence':r['sentence'],'teacher_tag_original':r['teacher tag'],'student_tag_original':r['student tag'],'status':'unreviewed'})
            prev=r
        digest=hashlib.sha256(json.dumps([[r[k] for k in ['turn','speaker','sentence','teacher tag','student tag']] for r in rows],ensure_ascii=False,default=serial).encode()).hexdigest()
        duplicate_map[digest].append(rel)
        inventory.append({'file':rel,'rows':len(rows),'consecutive_turn_speaker_groups':groups,'core_sha256':digest,'flags':dict(local)})
        stats.update(local)
    print(f'{subset}: {len(files)} files read',flush=True)

mirrors=[]
for rel,rows in allrows.items():
    p=Path(rel)
    folder='Subset1_WithDialogActs' if p.parent.name=='Subset 1' else 'Subset2_WithDialogActs'
    mirror=ROOT/'data'/folder/(p.name+'_with_dialog_acts.xlsx')
    if not mirror.exists():
        matches=[q for q in mirror.parent.glob('*.xlsx') if q.name.casefold()==mirror.name.casefold()]
        if len(matches)==1:
            mirror=matches[0]
        else:
            mirrors.append({'source':rel,'status':'missing_augmentation'});continue
    try:
        _,mr=read_rows(mirror)
        core=lambda rr:[[r[k] for k in ['turn','speaker','sentence','teacher tag','student tag']] for r in rr]
        same=core(rows)==core(mr)
        mirrors.append({'source':rel,'augmented':str(mirror.relative_to(ROOT)),'status':'core_identical' if same else 'core_differs','source_rows':len(rows),'augmented_rows':len(mr)})
    except Exception as e:
        mirrors.append({'source':rel,'status':'read_error','error':str(e)})
print('Augmented counterparts compared',flush=True)

tsvs={}
pairsets={}
for p in sorted((ROOT/'data').glob('*.tsv')):
    with p.open(newline='',encoding='utf-8') as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    pairs=[(r.get('text_a',''),r.get('text_b','')) for r in rows]
    pairsets[p.stem]=set(pairs)
    tsvs[p.name]={'rows':len(rows),'columns':list(rows[0]) if rows else [],'unique_text_pairs':len(set(pairs))}
overlap={role:len(pairsets['train_'+role]&pairsets['test_'+role]) for role in ['student','teacher']}
summary={
 'upstream':'https://github.com/SumnerLab/TalkMoves',
 'upstream_commit':subprocess.check_output(['git','-C',str(ROOT),'log','-1','--format=%H','--','data','code','Coding Manual.pdf'],text=True).strip(),
 'scope':'All original lesson workbooks in Subset 1 and Subset 2; augmented core comparison; existing TSV inventory. Flags are heuristic review candidates.',
 'raw_files':len(inventory),'raw_sentence_records':sum(x['rows'] for x in inventory),
 'consecutive_turn_speaker_groups':sum(x['consecutive_turn_speaker_groups'] for x in inventory),
 'flag_counts':dict(stats),'teacher_original_labels':dict(teacher_labels),'student_original_labels':dict(student_labels),
 'speaker_counts':dict(speakers),'header_patterns':dict(headers_count),'read_errors':errors,
 'exact_core_duplicate_file_groups':[v for v in duplicate_map.values() if len(v)>1],
 'augmentation_comparison':dict(collections.Counter(x['status'] for x in mirrors)),
 'tsv_inventory':tsvs,'train_test_identical_text_pair_overlap':overlap,
 'caveats':['Sentence records are not independent students or complete responses.','Heuristic visual flags do not establish missing information.','Both label columns can be legitimate context annotations; do not auto-delete.','Text-pair overlap does not establish lesson-level leakage.','Speaker pseudonyms do not establish identity across lessons.']}
for name,obj in [('summary.json',summary),('inventory.json',inventory),('augmentation_comparison.json',mirrors)]:
    (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=serial)+'\n')
with (OUT/'review_candidates.jsonl').open('w') as f:
    for r in flags:f.write(json.dumps(r,ensure_ascii=False,default=serial)+'\n')
print(json.dumps({k:summary[k] for k in ['raw_files','raw_sentence_records','consecutive_turn_speaker_groups','flag_counts','augmentation_comparison','read_errors','train_test_identical_text_pair_overlap']},ensure_ascii=False,indent=2))
