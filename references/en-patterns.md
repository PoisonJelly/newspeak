# English AI-writing patterns

Format: `ID [severity] name: condition → fix`. [auto] = lint.py catches it. [eye] = read for it.
S1 fix on first sight · S2 fix when clustered · S3 fix only when it stacks with other patterns.
Sources: (W) Wikipedia "Signs of AI writing", 2026-11 revision · (S) stop-slop, MIT · (R) published research · (G) Graphite "AI Tells", 2026-09 · (P) Pangram/GPTZero vendor data, baselines not published.

## Never touch

Names, numbers, dates, units, direct quotations with a speaker, legal and medical wording (the hedge is the meaning there), standard technical terms, the writer's mood (must/should/may/might keep their strength), and structure that a format rule requires (bullet decks, STE short sentences, subtitles).

## A. Content inflation

- **EN-A1** [S2 auto] Significance and legacy inflation (W): "stands as a testament to", "plays a pivotal/crucial/vital role", "marks a turning point", "setting the stage for", "indelible mark", "evolving landscape", "deeply rooted", "reflects broader trends", "underscores the importance", "enduring legacy", "focal point", "the transformative role that libraries play". → Say what happened. Keep a legacy claim only when a cited source makes it.
  - A person's role ("played a pivotal role in developing"): drop the inflation and keep the degree in plain words: "had a central part in developing", "was a core member of the team that developed". Do not raise it ("I developed") or lower it ("helped develop", "assisted with"). Unsure → keep the degree and add [writer to confirm: led, co-led, or supported?] (gate check `contribution`, SKILL.md 4-1 #38). A habit or object ("walking may play a crucial role in managing blood sugar") is not a person: "may help manage blood sugar" is fine.
- **EN-A2** [S2 auto] "This matters because…", "why this matters" (G: GPT-6 357x; S). → Cut the announcement; state the consequence.
- **EN-A3** [S3 on one, S2 on two+, auto] Trailing -ing analysis (W, R), including ", making it…", ", allowing…" and "and fostering/highlighting…": "…, highlighting/underscoring/reflecting/symbolizing/ensuring/fostering/contributing to …". Instruction-tuned models use present-participle clauses 2–5x as often as people (Reinhart 2025, PNAS). → End the sentence at the fact. Put a real effect in its own sentence.
- **EN-A4** [S2 auto] Promotional register (W historical, still common in copy): "nestled", "in the heart of", "boasts", "breathtaking", "rich heritage", "vibrant community", "hidden gem", "world-class", "cutting-edge", "game-changer", "revolutionize", "unlock the potential", "seamless", "elevate your". → Replace with a checkable detail (size, year, price, who uses it). Product copy may keep one or two plain descriptors that a fact backs ("just 940 g"). Slogans ("Elevate your…") go.
- **EN-A5** [S2 auto] Challenges-and-future formula (W): "Despite its …, X faces several challenges… Despite these challenges…", "future prospects", "remains to be seen", "(only) time will tell", "delivers on its promise", "will become clearer". → Name the actual problem. No vague optimism. A closing kicker that pairs a triad with one of these phrases keeps only the concrete checkpoint, stated as the original states it ("The first segments open in 2028.").
- **EN-A7** [S2 auto] Product-copy stock phrases: "Whether you're X or Y", "delivers all-day comfort", "without compromising (on)", "ensures that your…", "always within reach", "when the skies turn grey", "designed with you in mind", "the perfect choice", "stands the test of time", "peace of mind", "where X meets Y". → The checkable fact ("It weighs 940 g."). If nothing factual is left, cut the sentence. Apply the same standard to list items.
  - Split the stock shell from the benefit under it. Cut the shell, keep the benefit in plain words ("light enough to carry all day"). Do not raise a performance claim (water-resistant stays water-resistant). Keep the X and Y of "Whether you're X or Y" when they are real uses. The goal is plain human sales copy, not a spec sheet (SKILL.md 4-1 #30).
- **EN-A6** [S2 auto] Press-release and research stock phrases: "sheds light on", "paves the way", "a promising tool/avenue/approach", "a growing body of evidence", "opens new avenues", and the colon reveal "one simple habit: walking after meals". → Say only what the original says was done or found: "looked at one habit: walking after meals". Do not invent the study's aim or hypothesis. Keep the hedge.
- **EN-A9** [S2 eye] Bare metaphor left after removing inflation: "serves as a vital link" stripped to "is a link between farmers and residents"; same for hub, bridge, beacon, cornerstone. → State the literal relation: "connects local farmers with residents". Add no facts.
- **EN-A10** [S2 eye] Notability padding (W, GPT-5 era): listing where something was covered instead of what it is ("featured in regional media outlets", "maintains an active social media presence", "independent coverage"). → Summarize what the source says, or cut.
- **EN-A11** [S2 eye] "Identified by" padding (W, 2026): "Company filings identify him as…", "is listed in…". → "He founded the firm (filing, 2021)."
- **EN-A8** [S2 eye] Vague association (W, 2026): "became associated with leadership at Acme", "in connection with". → State the relation: "became CEO of Acme".

## B. Vocabulary

- **EN-B1** [S2 auto] AI-vocabulary cluster (W, R, P): delve, tapestry, testament, pivotal, underscore, showcase, intricate, meticulous, vibrant, bolster, garner, interplay, enduring, foster, enhance, crucial, realm, robust, seamless, leverage, multifaceted, dependable, landscape (abstract), navigate (the complexities), commendable, camaraderie, paramount, nuanced, holistic, streamline, unwavering, resonate, elevate. → One alone is fine. Two or more distinct ones in a short text read as AI; use plain words (use, show, important, careful, many, strong).
  - The list ages. delve peaked 2023–early 2024 and fell after April 2024 (Geng & Trotta 2025; WaPo: 1 per 1,000 ChatGPT chats by July 2025). Graphite 2026 tells: "dependable" (GPT-6), "deliberate", "single most", "arguably the most" (Claude Opus 5), "furthermore", "absolutely essential", "incredibly" (Gemini 3.1 Pro).
  - Do not swap a listed word for its fancier synonym. The synonym is not the problem; the inflation is.
- **EN-B2** [S3 eye] Overused business jargon (S): navigate, unpack, lean into, deep dive, double down, circle back, moving forward, game-changer. → Plain verbs: handle, explain, accept, analysis, commit, return to, next.

## C. Contrast and correction frames

- **EN-C1** [S1 auto] Negative parallelism (W, S, R; WaPo: 6% of GPT-4o chats in July 2025): "not just X, but Y", "It's not X, it's Y", "didn't just X — she Y", "X isn't the problem. Y is.", "more than just", "rather than merely", "not simply", "less like X and more like Y", "Not X. Not Y. Just Z.", uncontracted "Libraries are not just places to borrow books; they are …". → State Y.
  - If X carries information or reassurance ("It's not a verdict on who you are"), drop only the frame and keep X's meaning in one plain sentence ("Failure is feedback on what to try next, and it says nothing about who you are."). A generic maxim ("Leadership isn't about titles, it's about people") is cut. Delete X when it is a straw man. Never rebuild it as a short pair (EN-C1c). See SKILL.md 4-1 #15.
  - Also caught: "This isn't a choice between X and Y — it's about…", "goes beyond X — it's Y", a heading "…, Not a Quick Vote".
  - Keep the contrast where the text corrects a claim made earlier, and where a first-person story corrects a concrete sense or degree ("Not a gentle tick. A full, angry clang.").
- **EN-C1d** [S3 auto, 2+ S2] Comparative maxim: "getting it right matters more than getting it done fast", "Showing up every day matters more than showing up perfectly". → A plain statement tied to the text, or cut if it repeats a point.
- **EN-C1c** [S2 auto] Contrast rebuilt as a short pair after a rewrite: "The title is new. The people who lifted me up are not.", "It changed. We didn't." (self-test). → Write the information once as a plain sentence, or cut the maxim. Reversing the order ("Y. It isn't X.") is the same pattern (EN-C1b).
- **EN-C1b** [S2 auto] Two-sentence contrast "This isn't a story about success. It's a story about resilience." → Same rules as EN-C1; abstract reframes go, concrete corrections stay.
- **EN-C2** [S2 auto] Corrective framing (W mid-2026+, G): "should be treated as tradition rather than fact", "does not by itself establish", "should not be confused with". → Say what the thing is. Drop the pre-emptive correction unless a reader would really confuse the two.
  - Medical, legal and safety distinctions ("a complement to, not a replacement for, medical care") are the meaning: keep the distinction and its "should", and write it as one clean clause: "it should go alongside medical care, not replace it". Check that the subject still fits the new verb.
- **EN-C3** [S3 auto] "rather than" density. → Keep one.
- **EN-C4** [S2 eye] Telegraphed reversal (S): "Not because X. Because Y.", "The answer isn't X. It's Y.", "It feels like X. It's actually Y.", "stops being X and starts being Y". → State the point.

## D. Formulaic structure

- **EN-D1** [S2 auto] Summary label (W historical, S): "In conclusion,", "In summary,", "Overall,", "Ultimately,", "To sum up,". → Delete the label.
- **EN-D2** [S3 auto] Rule of three, with "and" or "or" (W, R; Pangram: ~19 vs ~5 per 10k words). → A single triplet is fine. When triplets cluster, drop an item that overlaps another ("free, accessible, and easy" → "free and easy"). Keep short concrete items (measures, conditions, skills, colours); a cluster made only of these is not a finding to fix. Do not split a triplet by repeating subject and verb ("free, and it is accessible and easy").
- **EN-D3** [S2 eye] Announce-then-answer: "Short answer:", "Here's the breakdown:", "Let me walk you through". → Answer.
- **EN-D4** [S2 auto] Rhetorical question answered at once: "So what does this mean? It means…", "So what's the right answer? The truth is, it's complicated.". → Make the statement.
- **EN-D9** [S2 auto] Moralising closer with an abstract triplet: "Our children deserve a thoughtful, transparent, and data-driven process." (self-test). → After cutting a closing label, re-check the new last sentence. End on the concrete recommendation or a fact.
- **EN-D5** [S2 eye] Every paragraph opens with a topic sentence and closes with a punchy line (S). → Vary openings; cut the pull-quote endings.
- **EN-D6** [S3 eye] "X and Y" headings everywhere, "Awards and recognition" sections (W). → Use plain headings only where the reader needs them.
- **EN-D7** [S3 auto] Conclusion or evaluative headings: "Conclusion", "Summary", "Key Takeaways", "Challenges", "Legacy", "Future Prospects" (W). → In short texts delete the heading; otherwise rename it after the subject ("Demographics and transport"). After deleting a heading, check that the paragraph fits under the heading above.
- **EN-D8** [S2 eye] Closing section restates an earlier claim ("may help manage blood sugar" again under "Conclusion"). → Merge or cut the restatement.

## E. Copula and agency

- **EN-E1** [S3 auto] Copula avoidance (W, R): "serves as", "stands as", "functions as", "boasts", "features", "refers to" in a definition. → "is", "has".
- **EN-F1** [S2 auto] Vague attribution (W, S): "Experts argue", "Studies show", "Observers have noted", "It is widely believed that", "Industry reports". Never turn the claim into the writer's own statement. Allowed outcomes:
  - name a source already in the text;
  - keep the attribution and add "[source needed]" for the user;
  - cut the claim and list the cut in the report;
  - only in blogs and marketing, lower it to a hedge: "One possible reason is timing: muscles may take up more glucose after a meal."
  - News, wiki, academic and medical text: the first three only. gate warns when attribution disappears (attribution). Never invent a source.
- **EN-F2** [S3 auto] False agency (S): "the data tells us", "a consensus emerges", "the market rewards". → Name who acts.
- **EN-F4** [S2 auto] Declared balance: "Critics raise equally important concerns", "just as compelling", "both sides make valid points". → Say what the concern is. Keep the writer's balance only if no other sentence carries it.
- **EN-F3** [S2 eye] Actor-hiding passive (S, narrowed): "It is believed that", "Mistakes were made", "The decision was reached". → Name the actor. Leave ordinary passives alone; GPT-4o uses agentless passives about half as often as people (Reinhart 2025), so removing every passive makes text read more machine-like, not less.

## G. Throat-clearing and meta

- **EN-G1** [S2 auto] Throat-clearing and signposting (S, W): "Here's the thing", "Here's what/why", "Let's dive in", "Let's break this down", "Let me be clear", "It turns out", "The truth is", "Make no mistake", "Let that sink in", "Full stop", "In this article", "It's worth noting", "It's important to note", "At its core", "In today's fast-paced world", "When it comes to", "At the end of the day", "In a world where", "And honestly?", "No fluff". → Delete; start with the point. A list header keeps its content: "Here's what I learned along the way:" → "What I learned along the way:".
- **EN-G2** [S2 eye] Meta-commentary (S): "As we'll see", "The rest of this essay", "Plot twist:", "X is a feature, not a bug". → Delete.
  - Exception: when a brief says the body follows (a blog intro before tips), one plain handoff line is fine ("they're all below"). "In this post, I will…" is still meta.

## H. Chatbot residue (all S1)

- **EN-H1** [S1 auto] Assistant talk left in a document (W G15, R): "Certainly!", "Great question", "You're absolutely right!", "I hope this helps", "Let me know if", "Feel free to", "Would you like me to", "Happy to help", "As an AI", "As of my last knowledge update", "Here is a revised version". → Delete.
- **EN-H2** [S1 auto] Therapist mode (2025–26 GPT reports): "You're not alone/broken/imagining it", "Take a breath", "It's okay to", "Your feelings are valid", "sit with that", "You're right to push back". → Delete; answer the actual problem.
- **EN-H4** [S1 auto] Social-post formulas: "I'm humbled/thrilled/excited/proud to share/announce", "Drop it in the comments (below)", "Let me know in the comments", "Tag someone who", "Repost if you", "This is your sign to", a bare "Agree?"/"Thoughts?" closer. → State the fact plainly and keep the original time words ("Today, I've been promoted to Head of Operations."). Delete bait closers or keep one plain question if the author wants replies. A question followed by "Share it in the comments." keeps only the question (SKILL.md 4-1 #49).
- **EN-H5** [S2 auto] Hook openers: "I almost didn't post this", "I never thought I'd share this", "Unpopular opinion:", "Story time:". → Drop unless the post later explains the hook.
- **EN-H6** [S2 eye] Slogan list: every bullet is "Maxim. Gloss." ("Consistency beats talent.", "Mentorship is everything."). → Lead with the concrete part; fold or drop the maxim.
- **EN-H7** [S3 auto, 2+ S2, 4+ S1] Customer-service stock phrases: "Rest assured", "your satisfaction is our top priority", "don't hesitate to reach out", "we value your business", "I completely understand how frustrating", "we take this very seriously", "apologize for any inconvenience", "to make things right", "look forward to serving you". → Keep one apology and the real offer. Cut reassurance with no fact. Keep real requests to the customer ("Please let me know which option works best").
- **EN-H3** [S1 auto] Tool residue and placeholders (W G15): `utm_source=chatgpt.com`, `turn0search0`, `oaicite`, `contentReference[…]`, `[cite: 3]`, `grok-card`, `【12†L3-5】`, "[Your Name]", "2025-XX-XX". → Remove or fill. `utm_source=chatgpt.com` proves ChatGPT found the link, not that it wrote the text.

## I. Hedging and disclaimers

- **EN-I1** [S1 auto] Source-availability disclaimer (W 2024–25 RAG failure): "While specific details are limited…", "not widely documented", "based on available information", "maintains a low profile". → State what is known; cut speculation about the unknown.
- **EN-I2** [S2 auto] Stacked hedges: "may potentially", "could possibly", "it could be argued that". → Keep one hedge at the original strength.
- **EN-I3** [S2 eye] Didactic disclaimer (W 2023–24): "It's important to remember…", "It's crucial to consult…" where nobody asked. → Delete unless it is legally or medically required.
- Note: research finds LLMs use fewer hedges and epistemic markers than people overall (Herbold 2023; Jiang & Hyland 2025) and express too little uncertainty (Zhou 2024). Do not strip legitimate hedges; strip boilerplate disclaimers.

## J. Formatting

- **EN-J1** [S3 auto: AN-J1, 5+ S2; with --genre sns/chat any `**` is S2] Bold on a word in every sentence (W). → Bold only headings or one key term per section.
- **EN-J2** [S3 auto: AN-J2, 4+ S2] Bold inline-header list items "- **Speed:** It runs fast." (W). → Prose, or plain list items.
- **EN-J3** [S3 auto] Title Case Headings (W). → Sentence case. News headlines keep the outlet's own headline style. Fix all headings or none (SKILL.md 4-1 #46). A heading that is a product or place name used in the body, or that has a number, is skipped.
- **EN-J4** [S2 auto: AN-J5] Emoji as bullets or heading markers (W; WaPo: 70% of GPT-4o messages). → Delete outside social posts.
- **EN-J8** [S2 auto: AN-J6] Stock hype emoji (🚀🔥✨💯🙌👇💡✅👉🎉💪🙏📌🔹) anywhere, social posts included. → Delete. A social post may keep one emoji that carries meaning.
- Social platforms (LinkedIn, Instagram, X, Threads, YouTube descriptions) do not render Markdown: remove `**` and `#`; plain hyphen lists are fine.
- **EN-J5** [S2 eye] Thin tables for content that fits in a sentence (W). → Prose.
- **EN-J6** [S1 eye] Markdown leaking into a non-Markdown target (`**`, `##`, `---` in an email or a wiki page) (W). → Convert to the target format. If the target is unknown, leave the markup alone.
- **EN-J7** [S2 eye] Folding a bold label into prose with an invented gloss ("HbA1c (blood sugar)"). → Turn the label into a lead-in phrase or drop it; never add a definition that is not exact.

## K. Punctuation

- **EN-K1** [S3/S2 auto] Em dash. News: keep dateline dashes ("PORT CALDER —", not counted) and dashes inside quotes; change dash pairs in running copy only when they cluster, using commas, a colon or a rewrite, never parentheses. Elsewhere: at most one per ~300 words. Mix the replacements: comma, colon, parentheses, a new sentence. Do not turn every dash into a comma; 2026 data shows ChatGPT and Gemini now use fewer dashes than people, and a text with only commas and periods is the newer tell. Human writers average about 3 per 1,000 words, with a wide range.
- **EN-K2** [S3 auto] Curly and straight quotes mixed (W). → Pick one style.
- **EN-K3** [S3 eye] No semicolons, parentheses or exclamation marks anywhere in a long casual text (R, G). → Let the register decide; casual writing usually has some. Pieces under ~300 words are exempt.

## L. Rhythm

- **EN-L1** [S3 auto] Uniform sentence length, no long sentence (R, S). → Merge two short sentences or split a long one. Add no content.
- **EN-L2** [S2 eye] Staccato fragments for drama: "Speed. Quality. Cost. Pick two. That's it." (S). → One sentence.
- **EN-L4** [S3 auto, 6+ S2] Four or more sentences in a row start with "I" (cover letters after a rewrite; self-test). → Start one or two with the fact, the place or the other person.
- **EN-L3** [S3 auto, 4+ S2] Three or more paragraphs open with a very short sentence (5 words or fewer), often from turning a bullet brief into one paragraph per bullet (self-test). → Vary openings; merge the short opener into the next sentence or start with the fact.

## M. Adverbs

- **EN-M1** [S3 auto] AI-favoured adverbs (S narrowed, G, Reddit reports): quietly, deeply, fundamentally, truly, genuinely, incredibly, profoundly, inherently, seamlessly, undeniably, notably, crucially, importantly, essentially, remarkably. → Cut these.
- **EN-M2** [S2 auto] "quiet" as a mood word: "quiet confidence", "quiet rebellion". → Describe the behaviour.
- **EN-M3** [S3 auto, 3+ S2, 5+ S1] Cover-letter stock phrases: "I am writing to express my keen interest" (→ "I am applying for …"), "What excites me most about X is your commitment to", "bring a genuine enthusiasm", "passionate advocate for", "my skills and values align with your mission", "positions me well to", "from day one", "dynamic team", "continued success", "I am confident that my skills", "I look forward to the possibility of", "would welcome the opportunity to discuss". → One opener and one closer are the genre. Replace the rest with a fact from the letter, or cut. Start-of-sentence "Additionally," → "also" after the subject.
- **EN-M4** [S3 auto, 2+ S2] Stock self-deprecation in casual first person: "I have a real talent for…", "which I'm counting as a win", "ask me how I know", "Narrator:", "Reader, I…". → One per piece; make the rest specific.
- Keep: very, perhaps, tends to, often, probably. Wikipedia lists hedges and intensifiers like these as more common in human text.

## Human signals to keep (do not edit these away)

- Plain "is/has" sentences and plain verbs (wrote, moved, used, tried, died).
- Concrete numbers, names, dates, places; direct quotes with a speaker.
- Some superlatives or flat statements ("the first", "the only") when the source supports them.
- Contractions in neutral or casual registers; an occasional parenthesis, semicolon or exclamation in casual writing.
- Wordy idioms people actually use ("as a result of", "in order to", "the fact that") at normal density.
- Mixed formal and informal register by itself is NOT an AI sign (W).
- Perfect grammar by itself is NOT an AI sign (W).
