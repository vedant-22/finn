"""POST {src, calls} -> the assembled ledger: grades, questions, for and against."""
from _common import make_handler
from finn import llm, research

def run(body):
    src, calls = body["src"], body["calls"]
    llm.METER[:] = []
    good = [c for c in calls if not c.get("error")]
    calls = good[:research.N_CALLS] if len(good) >= 2 else calls[:research.N_CALLS]
    graded = research.grade(src, calls)
    return research.assemble(src, calls, graded)

handler = make_handler(run)
