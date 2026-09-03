/* Browser/Node port of app/retriever.py + app/guardrails.py + app/assistant.py.
 *
 * Kept deliberately literal so it stays checkable against the Python original:
 * tools/parity_check.py runs both over the same questions and diffs the replies.
 * Load a corpus with MFFaq.create(corpus) -> { ask(question) }.
 */
(function (root) {
  "use strict";

  /* ---------------------------------------------------------------- tokens */

  var STOPWORDS = new Set([
    "a", "an", "the", "is", "are", "was", "were", "of", "for", "to", "in", "on",
    "at", "by", "and", "or", "it", "its", "this", "that", "what", "whats", "which",
    "how", "do", "does", "did", "i", "me", "my", "you", "your", "can", "will",
    "be", "have", "has", "there", "any", "much", "many", "please", "tell", "about",
    "fund", "scheme", "groww", "mutual", "funds"
  ]);

  function stem(word) {
    var suffixes = ["ies", "es", "s"];
    for (var i = 0; i < suffixes.length; i++) {
      if (word.length > 4 && word.endsWith(suffixes[i])) {
        return word.slice(0, word.length - suffixes[i].length);
      }
    }
    return word;
  }

  function tokenize(text, keepStopwords) {
    var words = String(text).toLowerCase().match(/[a-z0-9]+/g) || [];
    var out = [];
    for (var i = 0; i < words.length; i++) {
      var word = words[i];
      if (word.length < 2) continue;
      var root = stem(word);
      if (!keepStopwords && (STOPWORDS.has(word) || STOPWORDS.has(root))) continue;
      out.push(root);
    }
    return out;
  }

  /* ------------------------------------------------------------------ bm25 */

  var K1 = 1.5, B = 0.75;

  function buildIndex(passages) {
    var docs = passages.map(function (p) { return tokenize(p.text); });
    var lengths = docs.map(function (d) { return d.length; });
    var total = lengths.reduce(function (a, b) { return a + b; }, 0);
    var avgLen = docs.length ? total / docs.length : 0;

    var tfs = docs.map(function (doc) {
      var counts = new Map();
      doc.forEach(function (term) { counts.set(term, (counts.get(term) || 0) + 1); });
      return counts;
    });

    var df = new Map();
    docs.forEach(function (doc) {
      new Set(doc).forEach(function (term) { df.set(term, (df.get(term) || 0) + 1); });
    });

    var n = docs.length;
    var idf = new Map();
    df.forEach(function (freq, term) {
      idf.set(term, Math.log(1 + (n - freq + 0.5) / (freq + 0.5)));
    });

    function score(terms, i) {
      var tf = tfs[i], length = lengths[i], sum = 0;
      for (var t = 0; t < terms.length; t++) {
        var freq = tf.get(terms[t]);
        if (!freq) continue;
        var denom = freq + K1 * (1 - B + B * length / (avgLen || 1));
        sum += (idf.get(terms[t]) || 0) * freq * (K1 + 1) / denom;
      }
      return sum;
    }

    return function search(query, topK, allowedIds) {
      var terms = tokenize(query);
      if (!terms.length) return [];
      var hits = [];
      for (var i = 0; i < passages.length; i++) {
        if (allowedIds && !allowedIds.has(passages[i].id)) continue;
        var s = score(terms, i);
        if (s > 0) hits.push({ passage: passages[i], score: s });
      }
      hits.sort(function (a, b) { return b.score - a.score; });
      return hits.slice(0, topK);
    };
  }

  /* ------------------------------------------------------------ guardrails */

  var REDACTION = "[redacted]";

  // Most-specific first, so PAN is not swallowed by a generic alphanumeric rule.
  var PII_PATTERNS = [
    { label: "PAN", re: /\b[A-Z]{5}[0-9]{4}[A-Z]\b/gi },
    { label: "Aadhaar", re: /\b[2-9][0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}\b/g },
    { label: "email address", re: /\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b/g },
    // Indian mobile numbers, tolerating the common "+91 98765 43210" grouping.
    { label: "phone number", re: /(?:\+?91[ -]?)?\b[6-9][0-9]{4}[ -]?[0-9]{5}\b/g },
    { label: "OTP", re: /\botp\b[^0-9]{0,20}[0-9]{4,8}\b/gi },
    { label: "folio or account number", re: /\b(?:folio|account|a\/c|acct)\D{0,10}[0-9]{6,18}\b/gi },
    { label: "bank account number", re: /\b[0-9]{9,18}\b/g }
  ];

  function scanAndRedact(text) {
    var found = [], redacted = String(text);
    PII_PATTERNS.forEach(function (rule) {
      if (redacted.match(rule.re)) {
        found.push(rule.label);
        redacted = redacted.replace(rule.re, REDACTION);
      }
    });
    return { text: redacted, found: found };
  }

  var ADVICE = new RegExp(
    "\\b(should i|shall i|should we|can you recommend|do you recommend|recommend me|" +
    "suggest me|which (?:one |fund |scheme )?(?:is |should )?(?:the )?(?:better|best|good)|" +
    "is it (?:a )?(?:good|bad|safe|wise|worth)|worth (?:buying|investing|it)|" +
    "(?:good|bad|safe|right|suitable|okay|ok|fine) (?:choice |option |pick |bet )?for (?:me|my)\\b|" +
    "suits? me|suitable for me|" +
    "advise|advice|what should i (?:do|buy|pick|choose)|" +
    "(?:buy|sell|switch|exit|redeem|hold|invest in) (?:or|now|it|this|that)\\b|" +
    "help me (?:choose|pick|decide|build)|" +
    "(?:my|build a|review my|rebalance) portfolio|asset allocation for me|" +
    "how much should i (?:invest|put)|" +
    "will (?:it|this|the fund) (?:go up|grow|give|beat|outperform)|" +
    "(?:good|best) (?:fund|scheme)s? (?:to|for) (?:buy|invest))\\b", "i");

  var PERFORMANCE = new RegExp(
    "\\b(returns?|cagr|xirr|performance|how much (?:will|would|did) i (?:get|make|earn)|" +
    "profit|gain[s]? (?:will|would)|compare (?:the )?(?:returns|performance)|" +
    "(?:1|3|5|ten|10)[ -]?(?:year|yr) (?:return|performance)|past performance|" +
    "which (?:fund|scheme) (?:gave|has given|performed))\\b", "i");

  var GREETING = /^\s*(hi|hey|hello|namaste|thanks|thank you|ok|okay)\b[\s!.?]*$/i;

  function classify(text) {
    if (GREETING.test(text)) return "greeting";
    if (ADVICE.test(text)) return "advice";
    if (PERFORMANCE.test(text)) return "performance";
    return "fact";
  }

  /* ------------------------------------------------------------- assistant */

  var DISCLAIMER = "Facts-only. No investment advice.";
  var SCORE_FLOOR = 1.2;

  var OTHER_AMCS = [
    "sbi", "hdfc", "icici", "prudential", "axis", "nippon", "kotak", "uti",
    "mirae", "quant", "parag parikh", "ppfas", "dsp", "franklin", "templeton",
    "aditya birla", "birla", "canara", "robeco", "edelweiss", "motilal",
    "tata", "bandhan", "idfc", "invesco", "jm financial", "lic mf", "sundaram",
    "zerodha", "navi", "bajaj finserv", "whiteoak", "white oak", "360 one",
    "helios", "samco", "union mutual", "baroda", "bnp", "mahindra", "pgim",
    "shriram", "taurus", "trust mutual", "quantum", "indiabulls", "iti mutual",
    "angel one", "jio blackrock", "blackrock", "nj mutual", "old bridge",
    "unifi", "capitalmind", "choice mutual"
  ];

  var OTHER_AMC_RE = new RegExp(
    "\\b(" + OTHER_AMCS.map(function (n) {
      return n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }).join("|") + ")\\b", "i");

  var SCHEME_ATTRIBUTE_RE = new RegExp(
    "\\b(exit load|lock[ -]?in|minimum|min\\.? ?sip|lumpsum|lump sum|benchmark|" +
    "riskometer|risk[ -]?o[ -]?meter|category)\\b", "i");

  function create(corpus) {
    var meta = corpus.meta;
    var links = corpus.educational_links;

    var sources = {};
    corpus.sources.forEach(function (s) { sources[s.id] = s; });
    var schemes = {};
    corpus.schemes.forEach(function (s) { schemes[s.id] = s; });

    var passages = [];
    corpus.facts.forEach(function (fact) {
      var scheme = schemes[fact.scheme];
      passages.push({
        id: fact.id, kind: "fact", scheme: fact.scheme,
        attribute: fact.attribute, answer: fact.answer, source_id: fact.source_id,
        text: [scheme.name, scheme.aliases.join(" "),
               fact.attribute.replace(/_/g, " "), fact.keywords, fact.answer].join(" ")
      });
    });
    corpus.documents.forEach(function (doc) {
      passages.push({
        id: doc.id, kind: "document", scheme: null,
        attribute: doc.topic, answer: doc.answer, source_id: doc.source_id,
        text: [doc.topic.replace(/_/g, " "), doc.keywords, doc.answer].join(" ")
      });
    });

    var search = buildIndex(passages);

    // Longest aliases first, so "groww nifty total market index fund" is not
    // matched by the shorter "index fund".
    var aliasMap = [];
    corpus.schemes.forEach(function (scheme) {
      [scheme.name].concat(scheme.aliases).forEach(function (alias) {
        aliasMap.push({ alias: alias.toLowerCase(), id: scheme.id });
      });
    });
    aliasMap.sort(function (a, b) { return b.alias.length - a.alias.length; });

    // Tokens that merely name a scheme; a passage matching only these has not
    // answered the attribute that was actually asked about.
    var schemeTokens = new Set();
    aliasMap.forEach(function (entry) {
      tokenize(entry.alias, true).forEach(function (t) { schemeTokens.add(t); });
    });

    var schemeNames = corpus.schemes.map(function (s) { return s.name; });

    function resolveScheme(text) {
      var lowered = (" " + String(text).toLowerCase().replace(/[^a-z0-9 ]+/g, " ") + " ")
        .replace(/\s+/g, " ");
      for (var i = 0; i < aliasMap.length; i++) {
        if (lowered.indexOf(" " + aliasMap[i].alias + " ") !== -1) return aliasMap[i].id;
      }
      return null;
    }

    function answersTheQuestion(question, passage) {
      var topic = tokenize(question).filter(function (t) { return !schemeTokens.has(t); });
      if (!topic.length) return true;
      var terms = new Set(tokenize(passage.text));
      return topic.some(function (t) { return terms.has(t); });
    }

    function cite(sourceId) {
      var s = sources[sourceId];
      return { url: s.url, title: s.title, publisher: s.publisher, source_id: s.id };
    }

    function reply(answer, citation, extra) {
      var out = {
        answer: answer,
        citation: citation,
        last_updated_from_sources: meta.last_updated_from_sources,
        disclaimer: DISCLAIMER
      };
      Object.keys(extra || {}).forEach(function (k) { out[k] = extra[k]; });
      return out;
    }

    function linkOf(name) {
      var link = links[name];
      var match = corpus.sources.filter(function (s) { return s.url === link.url; })[0];
      return {
        url: link.url, title: link.title, publisher: link.publisher,
        source_id: match ? match.id : null
      };
    }

    function noAnswer(question, schemeId) {
      var inScope = schemeNames.join(", ");
      var answer;
      if (schemeId === null && SCHEME_ATTRIBUTE_RE.test(question)) {
        answer = "Which scheme do you mean? That fact is per-scheme, and I cover four: "
          + inScope + ".";
      } else if (schemeId === null && /\bfund\b|\bscheme\b|\bamc\b/i.test(question)) {
        answer = "That scheme isn't in this assistant's corpus. I cover four Groww Mutual "
          + "Fund schemes: " + inScope + ". Ask me about one of those and I'll cite the "
          + "official page.";
      } else {
        answer = "I don't have that fact in my corpus, so I won't guess. I can answer exit "
          + "load, minimum SIP or lumpsum, benchmark, riskometer, scheme category, ELSS "
          + "lock-in, expense ratio and statement downloads for: " + inScope + ".";
      }
      return reply(answer, linkOf("no_answer"), { intent: "no_answer" });
    }

    function ask(question) {
      question = String(question == null ? "" : question).trim();

      if (!question) {
        return reply(
          "Ask me a factual question about a Groww Mutual Fund scheme - for example its "
          + "exit load, minimum SIP, benchmark, riskometer or lock-in.",
          linkOf("advice_refusal"), { intent: "empty" });
      }

      // 1. PII gate. The raw question is dropped here and never indexed or stored.
      var scan = scanAndRedact(question);
      if (scan.found.length) {
        return reply(
          "I can't accept personal or account details, so I've discarded what you sent and "
          + "detected " + scan.found.join(", ") + " in it. Ask me about a scheme's published "
          + "facts instead - for example \"What is the exit load of Groww Value Fund?\" For "
          + "anything tied to your own folio, use the official investor channels.",
          linkOf("pii_refusal"), { intent: "pii_refusal", pii_detected: scan.found });
      }
      var safe = scan.text;

      // 2. Opinion / performance gates.
      var intent = classify(safe);

      if (intent === "greeting") {
        return reply(
          "Hello. I answer published facts about Groww Mutual Fund schemes - exit load, "
          + "minimum SIP, benchmark, riskometer, ELSS lock-in, expense ratio and statement "
          + "downloads. Try: \"What is the exit load of Groww Value Fund?\"",
          linkOf("advice_refusal"), { intent: "greeting" });
      }

      if (intent === "advice") {
        var adviceLink = resolveScheme(safe) === "elss" ? "elss_refusal" : "advice_refusal";
        return reply(
          "I can only share published facts, so I can't tell you whether to buy, sell, hold "
          + "or switch - that call depends on your own goals and is one for a SEBI-registered "
          + "investment adviser. I'm happy to give you the scheme's exit load, minimum SIP, "
          + "benchmark, riskometer or lock-in instead.",
          linkOf(adviceLink), { intent: "advice_refusal" });
      }

      if (intent === "performance") {
        return reply(
          "I don't compute or compare returns, and I don't make performance claims. Groww "
          + "Mutual Fund publishes disclosed performance for every scheme in its monthly "
          + "factsheet, linked below. Ask me a scheme fact - exit load, minimum SIP, "
          + "benchmark, riskometer or lock-in - and I'll answer that.",
          linkOf("performance_refusal"), { intent: "performance_refusal" });
      }

      // 3. Scope gate, before alias matching.
      var otherAmc = safe.match(OTHER_AMC_RE);
      if (otherAmc) {
        return reply(
          "That fund house isn't in this assistant's corpus - I only cover four Groww Mutual "
          + "Fund schemes: " + schemeNames.join(", ") + ". Ask me about one of those, or look "
          + "the other scheme up in its own AMC's Scheme Information Document.",
          linkOf("no_answer"), { intent: "out_of_scope", out_of_scope: otherAmc[1] });
      }

      var schemeId = resolveScheme(safe);

      var allowed = new Set();
      passages.forEach(function (p) {
        if (schemeId ? (p.scheme === schemeId || p.scheme === null) : p.scheme === null) {
          allowed.add(p.id);
        }
      });

      var hits = search(safe, 3, allowed).filter(function (hit) {
        return answersTheQuestion(safe, hit.passage);
      });

      if (!hits.length || hits[0].score < SCORE_FLOOR) return noAnswer(safe, schemeId);

      var passage = hits[0].passage;
      return reply(passage.answer, cite(passage.source_id), {
        intent: "fact",
        matched: passage.id,
        attribute: passage.attribute,
        scheme: passage.scheme ? schemes[passage.scheme].name : null,
        score: Math.round(hits[0].score * 1000) / 1000
      });
    }

    return {
      ask: ask,
      meta: meta,
      sources: corpus.sources,
      schemes: corpus.schemes,
      schemeNames: schemeNames,
      passageCount: passages.length,
      DISCLAIMER: DISCLAIMER
    };
  }

  var api = { create: create, tokenize: tokenize, scanAndRedact: scanAndRedact, classify: classify };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.MFFaq = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
