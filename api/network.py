"""POST {q} -> an answer from the investor's network. Also {op: company|person|contact|notices|views, ...}.
No model calls: the question is resolved against the registry and answered by finn/network."""
from http.server import BaseHTTPRequestHandler
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finn.webapi import JSONHandler, BadRequest, NotFound, Limiter, KB
from finn.network import Network, ask
from finn.network.views import views

_base = None
_nets, _rebuilt = {}, {}     # per answer set, in this warm instance: one possible pair today, so three states at most
MAX_Q, MAX_DECISIONS, KEEP = 300, 200, 8


def _load():
    global _base
    _base = _base or Network.load()
    return _base


def _said(decisions):
    """The investor's answers to "Is it the same person?" ("yes, that is the Jigar Shah I know"). They live on the
    phone and come with the request; they are never stored or logged here. Only an answer to a question the engine
    itself asked is kept, and that is settled before any work: a made-up key can't make the server build a network."""
    if not isinstance(decisions or {}, dict):
        raise BadRequest("decisions must be an object")
    said = {str(k)[:120]: v for k, v in list((decisions or {}).items())[:MAX_DECISIONS] if v in ("same", "different")}
    asks = _load().asks
    return tuple(sorted((k, v) for k, v in said.items() if k in asks))


def _net(decisions):
    """The network as built from the files, with the investor's answers applied when there are any to apply."""
    key = _said(decisions)
    if not key:
        return _load()
    if key not in _nets:
        if len(_nets) >= KEEP:
            _nets.clear()
        _nets[key] = Network.load(decisions=dict(key))
    return _nets[key]


def _views(answers):
    """What network.json holds, rebuilt from the investor's answers. With none to apply, only the build: the phone
    already has the file, and nothing is rebuilt to say so. The build is the file's, written by the pipeline into the
    data this function is bundled with, so the phone can tell a current rebuild from one made for an older deploy."""
    build = _load().build
    key = _said(answers)
    if not key:
        return {"build": build}
    if key not in _rebuilt:
        if len(_rebuilt) >= KEEP:
            _rebuilt.clear()
        _rebuilt[key] = {**views(_net(dict(key))), "build": build, "answers": dict(key)}
    return _rebuilt[key]


def run(body):
    op = body.get("op") or "ask"
    if op == "views":
        return _views(body.get("answers"))
    net = _net(body.get("decisions"))
    symbols = [o.symbol for o in net.reg.orgs.values() if o.symbol and o.symbol in net.companies]
    if op == "ask":
        return ask.answer(net, str(body.get("q", ""))[:MAX_Q], symbols)
    if op == "company":
        return net.company(str(body.get("symbol", ""))[:20], str(body.get("name", ""))[:80], str(body.get("sector", ""))[:80])
    if op == "person":
        p = net.by_id.get(str(body.get("id", "")))
        if p is None or p.kind != "filing":
            raise NotFound("no such person")
        return ask._diligence(net, p)
    if op == "contact":
        c = net.by_id.get(str(body.get("id", "")))
        if c is None or c.kind != "contact":
            raise NotFound("no such contact")
        return ask._contact(net, c, symbols)
    if op == "notices":
        return {"notices": net.notices(symbols)}
    raise BadRequest("unknown op")


class handler(JSONHandler, BaseHTTPRequestHandler):
    run = staticmethod(run)
    max_body = 64 * KB   # a question and the investor's identity answers
    limit = Limiter(120, 600)   # a person asks a few questions a minute; a loop that rebuilds views is stopped
