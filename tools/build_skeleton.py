#!/usr/bin/env python3
"""Generate edit-operation JSON files that turn the 2025 annual-report .hwp
into the final-year (5th year, 2026) skeleton with [DATA:<id>] placeholders.

usage: build_skeleton.py BASE.hwp BASE.txt INSPECT.json OUTDIR
  BASE.txt     = extract_text.js --format text BASE.hwp
  INSPECT.json = extract_text.js --inspect --with-cell-text BASE.hwp
Writes OUTDIR/ops_structure.json, OUTDIR/ops_text.json, OUTDIR/placeholders.json
"""
import json, os, subprocess, sys, tempfile

_, base, txt, insp, out = sys.argv[:5]
EDIT = os.environ["HWP_EDIT_MJS"]  # path to easy-hwp scripts/edit.mjs
STAGE1 = sys.argv[5] if len(sys.argv) > 5 else base  # file the text ops will run on
_probe_cache = {}
lines = [l.strip() for l in open(txt, encoding="utf-8").read().split("\n")]
tables = json.load(open(insp, encoding="utf-8"))["tables"]

structure, text, ph = [], [], []

def P(pid, hint):
    ph.append({"id": pid, "hint": hint})
    return f"[DATA:{pid}]"

def n_paras(t, r, c, n_lines):
    """Number of real paragraphs in a cell (extracted text cannot tell a paragraph
    break from a forced line break), found by probing STAGE1 with cell_para=k."""
    key = (t, r, c)
    if key in _probe_cache:
        return _probe_cache[key]
    tb = tables[t]
    n = 1
    for k in range(n_lines - 1, 0, -1):
        op = [{"type": "set_cell_text", "section": tb["sec"], "para": tb["para"], "control": tb["ctrl"],
               "row": r, "col": c, "text": "x", "cell_para": k}]
        with tempfile.TemporaryDirectory() as d:
            json.dump(op, open(f"{d}/o.json", "w"))
            res = subprocess.run(["node", EDIT, STAGE1, f"{d}/out.hwp", f"{d}/o.json"],
                                 capture_output=True, text=True)
        if '"status":"success"' in res.stdout:
            n = k + 1
            break
    _probe_cache[key] = n
    return n

def cell(t, r, c, s):
    """Write s into a cell one paragraph per line; blank any leftover paragraphs
    of the original cell (set_cell_text only touches one paragraph) and drop them."""
    tb = tables[t]
    orig = next(x for x in tb["cells"] if x["row"] == r and x["col"] == c)["text"]
    n = n_paras(t, r, c, len(orig.split("\n"))) if "\n" in orig else 1
    new_lines = s.split("\n")
    if n == 1 and len(new_lines) > 1:  # single paragraph: keep forced line breaks
        new_lines = [s]
    for k in range(max(n, len(new_lines))):
        op = {"type": "set_cell_text", "section": tb["sec"], "para": tb["para"],
              "control": tb["ctrl"], "row": r, "col": c,
              "text": new_lines[k] if k < len(new_lines) else ""}
        if k:
            op["cell_para"] = k
        text.append(op)
    text[-1]["collapse"] = True

def drop_rows(t, rows):
    tb = tables[t]
    for r in sorted(rows, reverse=True):
        structure.append({"type": "delete_table_row", "section": tb["sec"],
                          "para": tb["para"], "control": tb["ctrl"], "row": r})

def body(old_prefix, new):
    q = [l for l in lines if l.startswith(old_prefix)]
    assert q, old_prefix
    text.append({"type": "replace_text", "query": q[0], "replacement": new})

# ---- 요약문 (table 1)
cell(1, 9, 6, "5년차(최종): 2026. 01. 01 - 2026. 12. 31 (1년 0개월)")
cell(1, 12, 6, P("summary.budget.year", "2026년도 총 연구개발비(천원) 및 정부지원/기관부담 내역"))
cell(1, 22, 9, "실증로 대비 자기장 구조에서 구축한 데이터베이스를 활용한 대안개념 디버터 형상 도출\n"
     "차세대 토카막 장치에 적용 가능한 통합된 대안개념 디버터 형상의 설계방향 제시 및 기반 데이터 구축\n"
     "실험 및 전산모사를 통한 KSTAR 텅스텐 디버터 환경의 경계 플라즈마 특성 통합 분석")
cell(1, 23, 9, P("summary.year.content", "당해연도(2026) 수행 내용 요약 (3-5 세부수행 실적의 요약)"))
cell(1, 25, 5, P("summary.result", "연구개발성과 요약 (핵심 결과 2~4문장)"))
cell(1, 26, 5, P("summary.utilization", "성과 활용계획 및 기대효과"))

# ---- 2. 수행 과정 (table 3): 5차년도 추진내용
cell(3, 0, 0, "5차년도 (최종)(2단계 2차년도)")
cell(3, 3, 0, "KSTAR 텅스텐 디버터 환경 대상 실험과 전산모사 간 비교 분석")
cell(3, 6, 0, "실증로 대비 자기장 구조에서의 대안개념 디버터 형상 분석")
cell(3, 9, 0, "차세대 토카막 장치에의 대안개념 디버터 형상 설계 기반 데이터 구축 및 설계방향 제시")

# ---- 3-1 정성적 성과 (table 4) and 첨부1 (table 52)
goals = ["실증로 대비 자기장 구조에서 구축한 데이터베이스를 활용한 대안개념 디버터 형상 도출",
         "전산해석 수행을 바탕으로 차세대 토카막 장치에 적용 가능한 통합된 대안개념 디버터 형상의 설계방향 제시 및 기반 데이터 구축",
         "실험 및 전산모사를 통한 KSTAR 텅스텐 디버터 환경의 경계 플라즈마 특성 통합 분석"]
for t, tag in ((4, "3-1"), (52, "att1")):
    cell(t, 1, 3, "5차년도\n(최종)(2단계 2차년도)\n")
    for i, g in enumerate(goals, start=1):
        cell(t, i, 4, g)
        cell(t, i, 5, P(f"{tag}.row{i}.summary", f"목표{i} 실적요약"))
        cell(t, i, 6, P(f"{tag}.row{i}.pct", f"목표{i} 달성도(%)"))
        cell(t, i, 7, P(f"{tag}.row{i}.evidence", f"목표{i} 관련증빙(논문/학회/보고서 n건)"))

# ---- 3-3 세부 정량적 성과: 논문 / 학회 / 국제협력 / 포상 표 (2025 데이터 제거)
for r in range(1, 11):
    cell(5, 1, r, P(f"3-3.paper.col{r}", "논문 표 1행: 열 순서는 표 머리말 기준"))
text.append({"_note": "extra papers: add rows with insert_table_row at execution time"})
drop_rows(6, range(2, 16))
for c in range(1, 7):
    cell(6, 1, c, P(f"3-3.conf.col{c}", "학술회의 표 1행"))
drop_rows(35, [2])
for c in range(1, 7):
    cell(35, 1, c, P(f"3-3.intl.col{c}", "국제화 협력성과 표 1행"))
drop_rows(37, [2, 3])
for c in range(1, 7):
    cell(37, 1, c, P(f"3-3.award.col{c}", "포상 및 수상 표 1행"))
stars = [l for l in lines if l.startswith("*") and ("Nucl" in l or "Nat" in l)]
for i, s in enumerate(stars):
    text.append({"type": "replace_text", "query": s,
                 "replacement": ("* " + P("3-3.paper.pending", "투고중/투고예정 논문 목록(저자, 제목, 저널, 상태)")) if i == 0 else ""})

# ---- 3-5 세부수행 실적 (lines of the 2025 body between '3-5)' and '3-6)')
start = max(i for i, l in enumerate(lines) if l.startswith("3-5) 세부수행 실적"))
end = next(i for i, l in enumerate(lines) if i > start and l.startswith("3-6) 연구개발비"))
region = lines[start + 1:end]
new = {
    0: "가. 실증로 대비 자기장 구조에서 구축한 데이터베이스를 활용한 대안개념 디버터 형상 도출",
    1: "" + P("3-5.A.1.title", "소제목"),
    2: "   " + P("3-5.A.1.body", "목적/계산조건/결과/그림 인용 (그림 번호는 3-5 전체 통일)"),
    3: "" + P("3-5.A.2.title", "소제목(해당 시)"),
    4: "   " + P("3-5.A.2.body", "본문"),
    9: "나. 전산해석 수행을 바탕으로 차세대 토카막 장치에 적용 가능한 통합된 대안개념 디버터 형상의 설계방향 제시 및 기반 데이터 구축",
    10: "" + P("3-5.B.1.title", "소제목"),
    12: "   " + P("3-5.B.1.body", "본문"),
    13: "" + P("3-5.B.2.title", "소제목(해당 시)"),
    14: "   " + P("3-5.B.2.body", "본문"),
    22: "다. 실험 및 전산모사를 통한 KSTAR 텅스텐 디버터 환경의 경계 플라즈마 특성 통합 분석",
    23: "" + P("3-5.C.1.title", "소제목"),
    24: "   " + P("3-5.C.1.body", "본문 (실험 vs SOLPS-ITER 비교)"),
    25: "" + P("3-5.C.2.title", "소제목(해당 시)"),
    26: "   " + P("3-5.C.2.body", "본문"),
    37: "라. " + P("3-5.D.title", "기타 수행 실적(진단계 개선·불순물 수송 등, 해당 시 작성)"),
    38: "" + P("3-5.D.1.title", "소제목"),
    39: "   " + P("3-5.D.1.body", "본문"),
}
import re
seen = set()
for i, l in enumerate(region):
    if not l or l in seen:
        continue
    seen.add(l)
    if "()" in l or re.search(r"\S  \S", l):
        pieces = [x.strip() for x in re.split(r"\(\)|\s{2,}", l) if len(x.strip()) > 1]
        for k, piece in enumerate(pieces):
            text.append({"type": "replace_text", "query": piece, "replacement": new.get(i, "") if k == 0 else ""})
    else:
        text.append({"type": "replace_text", "query": l, "replacement": new.get(i, "")})

# ---- 첨부1 증빙 목록 (tables 53..55), 첨부2 주요성과 (56..59)
for t, n in ((53, 1), (54, 2), (55, 3)):
    cell(t, 1, 1, P(f"att1.evidence{n}", f"목표{n} 관련증빙 명칭 목록"))
cell(56, 0, 2, " 계속과제 주요성과 (2026년 기준. 1.1 ∼ 12.31) : 중요도 순 작성 요망")
for t, n in ((57, 1), (58, 2), (59, 3)):
    cell(t, 1, 0, "\U000f02fb(목표) \n○ " + P(f"att2.{n}.goal", "성과 목표"))
    cell(t, 2, 0, "\U000f02fb(주요성과) \n○ " + P(f"att2.{n}.result", "주요성과 (-로 세부 설명)"))
    cell(t, 3, 0, "\U000f02fb(활용방안 및 기대효과)\n○ " + P(f"att2.{n}.impact", "활용방안/기대효과"))

# ---- 3-6 연구비 연도 헤더 (3~5차년도 = 2024~2026)
for c, y in ((7, "2024"), (8, "2025"), (9, "2026")):
    cell(39, 1, c, y)

json.dump(structure, open(f"{out}/ops_structure.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
text = [o for o in text if "_note" not in o]
json.dump(text, open(f"{out}/ops_text.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(ph, open(f"{out}/placeholders.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(structure), "structure ops,", len(text), "text ops,", len(ph), "placeholders")
