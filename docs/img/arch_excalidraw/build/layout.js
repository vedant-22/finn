// FINN architecture as an Excalidraw scene. Every position is on a 20px grid.
const INK = "#333333", GREY = "#5E5D63", DASH = "#6A6970", ACCENT = "#005DA3", PAPER = "#FFFFFF";

const BOX = {
  archive: ["Filings and share prices",
    "Everything companies file with the stock exchange (NSE), plus each day's prices. Fetched by hand for now. I keep a year.",
    "pipeline/archive.py, pipeline/ingest.py"],
  reaction: ["The price study",
    "Looks back over a year: after a filing FINN would alert you to, did the stock move? It tests the alert rules. It never changes what the app shows you.",
    "evals/run_reaction.py"],
  events: ["Events",
    "One event per filing, saved once. A new version only if a key detail changes.",
    "pipeline/ingest.py · SQLite"],
  steps: ["Read and checked",
    "Rules sort most filings on their own. An AI model reads the rest once I give it a key. Code then checks what it read.",
    "finn/ingest/steps.py"],
  facts: ["Facts",
    "What FINN keeps from each filing: how urgent it is, how big it is next to the company's revenue, what results it reports, and who it names.",
    "finn/ingest/store.py"],
  answering: ["Answering a question",
    "Searches a company's own calls with investors and quotes what it finds. An AI model sees your question only if it can't train on it, and never with your name or holdings. FINN doesn't keep it. The app has no screen for this yet.",
    "finn/answer"],
  snapshot: ["The app's snapshot, 28 Oct",
    "A copy of prices and filings I built by hand from NSE and screener.in. The app shows it, and can fetch one company live when you ask. The plan is to build it from the Facts instead.",
    "pipeline/, api/"],
  overlay: ["What you hold and who you know",
    "Code matches your shares and contacts to the public facts, with no model. In this demo, both are invented.",
    "finn/network"],
  phone: ["Your phone",
    "Shows what changed in what you hold, and any company's page. You get the public facts everyone gets, plus your own data, never anyone else's.",
    "web/ on Vercel"],
};

export function LAYOUT({ wrap, width, FF, opts = {} }) {
  const G = 20;
  const snap = (v, m = G) => Math.ceil(v / m) * m;
  const S = { title: 28, head: 20, body: 16, path: 14 };
  const LH = 1.25;
  const L = { x: 40, w: 480 }, R = { x: 680, w: 360 };
  const Lc = L.x + L.w / 2, Rc = R.x + R.w / 2, gapC = (L.x + L.w + R.x) / 2;
  const sk = [], checks = [];

  const text = (id, x, y, t, o = {}) => {
    sk.push({ type: "text", id, x, y, text: t, fontSize: o.size || S.body, fontFamily: o.ff || FF.hand,
      strokeColor: o.color || INK, textAlign: o.align || "left", verticalAlign: "top", lineHeight: LH,
      roughness: 1, groupIds: o.group ? [o.group] : [] });
    return id;
  };
  const centred = (id, cx, y, t, o = {}) => text(id, cx - width(t, o.size || S.body, o.ff || FF.hand) / 2, y, t, o);
  const rect = (id, x, y, w, h, o = {}) => sk.push({ type: "rectangle", id, x, y, width: w, height: h,
    strokeColor: o.dashed ? DASH : INK, backgroundColor: o.dashed ? "transparent" : PAPER, fillStyle: "solid",
    strokeWidth: o.dashed ? 1.5 : 1, strokeStyle: o.dashed ? "dashed" : "solid", roughness: 1,
    roundness: { type: 3 }, groupIds: o.group ? [o.group] : [] });
  const arrow = (id, x1, y1, x2, y2, o = {}) => sk.push({ type: "arrow", id, x: x1, y: y1,
    points: [[0, 0], [x2 - x1, y2 - y1]], strokeColor: INK, strokeWidth: 1.5,
    strokeStyle: o.dashed ? "dashed" : "solid", roughness: 1, startArrowhead: null, endArrowhead: "arrow",
    from: o.from, to: o.to });

  const lines = (key, w) => wrap(BOX[key][1], S.body, FF.hand, w - 2 * G);
  const natural = (key, w) => 120 + G * lines(key, w).length;
  const box = (key, x0, y0, w, h, dy = 0) => {
    const g = key + "-g", [head, body, path] = BOX[key], ls = lines(key, w);
    rect(key, x0, y0, w, h, { group: g });
    const x = x0, y = y0 + dy;
    checks.push([text(key + "-h", x + G, y + G, head, { size: S.head, group: g }), key]);
    checks.push([text(key + "-b", x + G, y + 3 * G, ls.join("\n"), { group: g }), key]);
    checks.push([text(key + "-p", x + G, y + 3 * G + G * ls.length + G, path, { size: S.path, ff: FF.mono, color: GREY, group: g }), key]);
  };

  // header
  text("title", 40, 40, "How data moves through FINN, and what stays private", { size: S.title });
  text("caption", 40, 100, "Solid lines run today. Dashed lines I've designed but not built yet.", { color: GREY });
  rect("key-solid", 40, 140, 40, 20);
  text("key-solid-t", 100, 140, "runs in this repo today", { color: GREY });
  rect("key-dashed", 340, 140, 40, 20, { dashed: true });
  text("key-dashed-t", 400, 140, "designed, not built yet", { color: GREY });
  text("public-h", 40, 220, "Public: what companies file, read once for everyone", { size: S.head });

  // row 1: archive | price study
  const y1 = 280, h1 = snap(Math.max(natural("archive", L.w), natural("reaction", R.w)), 2 * G);
  box("archive", L.x, y1, L.w, h1);
  box("reaction", R.x, y1, R.w, h1);
  arrow("a-archive-reaction", L.x + L.w, y1 + h1 / 2, R.x, y1 + h1 / 2, { from: "archive", to: "reaction" });

  // rows 2-3: events, read and checked | answering
  const y2 = y1 + h1 + 3 * G;
  const hE = natural("events", L.w);
  let hS = natural("steps", L.w);
  if ((hE + 3 * G + hS) % (2 * G)) hS += G;
  const yA = y2, hA = natural("answering", R.w);
  if (y2 + hE + 3 * G + hS < yA + hA) hS = yA + hA - (y2 + hE + 3 * G);
  const y3 = y2 + hE + 3 * G;
  box("events", L.x, y2, L.w, hE);
  box("steps", L.x, y3, L.w, hS);
  const yAend = y3 + hS;
  box("answering", R.x, yA, R.w, yAend - yA, Math.floor((yAend - yA - hA) / 2 / G) * G);
  arrow("a-archive-events", Lc, y1 + h1, Lc, y2, { from: "archive", to: "events" });
  arrow("a-events-steps", Lc, y2 + hE, Lc, y3, { from: "events", to: "steps" });
  const yQ = (yA + yAend) / 2;
  text("question-t", L.x + L.w + 4 * G, yQ - 50, "your\nquestion");
  arrow("a-question", L.x + L.w + 4 * G, yQ, R.x, yQ, { to: "answering" });

  // row 4: facts | snapshot
  const y4 = yAend + 3 * G, h4 = snap(Math.max(natural("facts", L.w), natural("snapshot", R.w)), 2 * G);
  box("facts", L.x, y4, L.w, h4);
  box("snapshot", R.x, y4, R.w, h4);
  arrow("a-steps-facts", Lc, yAend, Lc, y4, { from: "steps", to: "facts" });
  arrow("a-facts-snapshot", L.x + L.w, y4 + h4 / 2, R.x, y4 + h4 / 2, { dashed: true, from: "facts", to: "snapshot" });
  centred("designed-t", gapC, y4 + h4 / 2 - 30, "designed", { color: GREY });

  // the line
  const yL = y4 + h4 + 3 * G;
  sk.push({ type: "line", id: "private-line", x: 40, y: yL, points: [[0, 0], [L.w, 0]], strokeColor: ACCENT,
    strokeWidth: 2, roughness: 1, strokeStyle: "solid" });
  text("private-line-t", 40, yL + G, "Below this line is your side.\nOnly code touches it,\nnever a model.", { color: ACCENT });

  // private side
  const P = yL + 5 * G;
  const desc = wrap("A locked space of its own in the cloud, not built yet. The matching code already runs, on made-up demo data.", S.body, FF.hand, Lc - 20 - (L.x + G));
  const yO = P + 3 * G + G * desc.length + G;
  const hO = natural("overlay", L.w - 2 * G);
  rect("private", L.x, P, L.w, yO + hO + G - P, { dashed: true });
  text("private-h", L.x + G, P + G, "Your private side", { size: S.head });
  text("private-b", L.x + G, P + 3 * G, desc.join("\n"), { color: GREY });
  text("copy-t", Lc + G, P - 3 * G, "one read-only copy\nof public facts");
  box("overlay", L.x + G, yO, L.w - 2 * G, hO);
  arrow("a-facts-overlay", Lc, y4 + h4, Lc, yO, { dashed: true, from: "facts", to: "overlay" });

  // phone, outside both sides: its own full-width row
  const yPB = yO + hO + G;               // private box bottom
  const yPh = yPB + 7 * G;
  const W = R.x + R.w - L.x;
  text("outside-h", L.x, yPh - 3 * G, "Outside both sides", { size: S.head });
  box("phone", L.x, yPh, W, natural("phone", W));
  arrow("a-snapshot-phone", Rc, y4 + h4, Rc, yPh, { from: "snapshot", to: "phone" });
  text("public-facts-t", Rc + G, snap((y4 + h4 + yPh) / 2) - G, "public facts");
  arrow("a-overlay-phone", Lc, yO + hO, Lc, yPh, { dashed: true, from: "overlay", to: "phone" });
  text("yours-t", Lc + G, yPB + G, "only what's yours");

  // footer
  const yF = yPh + natural("phone", W) + 3 * G;
  const foot = wrap("For production I'd use Google Cloud (ADR 5, not deployed). Events and facts would go in Cloud SQL, with reading and answering on Cloud Run and Vertex AI. Your private side would be locked so nothing in it can send data out. Your phone reads it only when signed in.", S.body, FF.hand, 1000);
  text("footer", 40, yF, foot.join("\n"), { color: GREY });

  return { skeleton: sk, checks };
}
