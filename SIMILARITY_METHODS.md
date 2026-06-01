# How the Similarity Methods Work

This tool compares two codebases across nine independent methods, then combines their results into a single **overall similarity score** from 0 (nothing in common) to 1 (identical). Each method looks at a different aspect of the code, so the combined score is more reliable than any single check alone.

---

## Overall Score

The overall score is a weighted average of all nine methods. Methods that tend to be more accurate carry more weight. A score above **0.70** generally indicates substantial overlap worth investigating. Scores in the **0.30–0.70** range may reflect shared libraries, common patterns, or partial copying. Scores below **0.30** typically suggest independent codebases.

---

## The Nine Methods

### 1. File Hash — *~13% of the overall score*

**What it does:** Strips out all comments and blank lines from each file, then generates a unique "fingerprint" for what remains. If any file in Project B has an identical fingerprint to any file in Project A, it counts as a match.

**Think of it as:** Checking whether someone literally copy-pasted a file. Even if they removed the comments or added blank lines, this will still catch it.

**High score means:** One or more files are essentially identical between the two projects.

**What it misses:** Any change to the actual code — even renaming a single variable — will produce a different fingerprint.

**Excluded files:** The following common boilerplate files are ignored entirely, as they are nearly identical across most projects and would inflate the score: `__init__.py`, `__main__.py`, `conftest.py`, `setup.py`, `index.js`, `index.ts`, `index.jsx`, `index.tsx`, `index.mjs`, `index.cjs`.

---

### 2. Line Similarity — *~17% of the overall score*

**What it does:** Normalises every line in both projects (strips comments, punctuation-only lines, and whitespace), then checks whether each line from Project B appears anywhere in Project A — regardless of which file or where in that file. The score is the percentage of Project B's lines that have a match somewhere in Project A.

**Think of it as:** Cutting both books into individual sentences, shuffling them into two piles, and asking how many sentences from pile B also appear somewhere in pile A. Order doesn't matter — a line found in a completely different file still counts.

**High score means:** A large portion of Project B's code appears — verbatim, after stripping formatting — somewhere in Project A.

**What it misses:** Code that was paraphrased rather than copied (same logic, different wording) won't be caught. Very common boilerplate lines (e.g. `import os` or `return None`) will match across unrelated projects, so context from the other methods matters.

---

### 3. Function Names — *~13% of the overall score*

**What it does:** Collects every function, method, and class name defined in each project. Compares the two lists to see how many names they share.

**Think of it as:** Comparing the table of contents of two books. Even if the content is rewritten, the same chapter titles are a meaningful signal.

**High score means:** Both projects define functions and classes with the same names.

**What it misses:** Common, generic names like `calculate`, `fetchData`, or `handleError` appear in many projects and will inflate the score. Renaming functions will deflate it even if the logic is identical.

---

### 4. Code Structure (AST) — *~17% of the overall score*

**What it does:** Parses each file into its grammatical structure — the logical skeleton of the code, ignoring what variables or functions are actually named. It then fingerprints the shapes of code blocks and compares them.

**Think of it as:** Comparing the blueprints of two buildings. Even if the rooms have different names, the same floor plan is a strong signal.

**High score means:** The logical structure of the code is similar — the same kinds of nested loops, conditionals, and function calls appear in the same arrangements, regardless of what they're called.

**What it misses:** Code in different languages will always score 0 here. Very simple files (short scripts) may match by coincidence.

---

### 5. Token Fingerprinting — *~17% of the overall score*

**What it does:** Converts each file into a simplified sequence of code "tokens" (variable names all become `ID`, numbers become `NUM`, strings become `STR`, etc.), then creates a compact fingerprint of that sequence. This is the same technique used by academic plagiarism detection systems like MOSS and JPlag.

**Think of it as:** Summarizing a document by its sentence structure and word types rather than the actual words. "The dog chased the cat" and "The programmer wrote the function" have the same grammatical fingerprint.

**High score means:** The code follows the same patterns and sequences of operations, even if names and values differ.

**What it misses:** Code that was heavily restructured or broken into many small helper functions may score lower even if the underlying logic is the same.

---

### 6. Call Graph — *~9% of the overall score*

**What it does:** Maps out which functions call which other functions in each project, then compares the shape of those maps. Two projects don't need the same function names — only the same calling patterns.

**Think of it as:** Comparing an org chart. If both companies have the same reporting structure (one executive, three managers, ten engineers each), that's a match — even if the people have different names.

**High score means:** Functions in both projects are organized with similar relationships — the same nesting and calling patterns.

**What it misses:** Relies on correctly identifying function definitions and calls, which can fail on unusual code styles. Small projects with few functions may match by chance.

---

### 7. Import Analysis — *~4% of the overall score*

**What it does:** Lists every external library imported in each project and compares the two lists.

**Think of it as:** Looking at the bibliography of two papers. If they cite the same obscure sources, that's notable. If they both cite Wikipedia, that tells you less.

**High score means:** Both projects rely on the same set of third-party libraries.

**What it misses:** Many projects share common libraries (web frameworks, testing tools, etc.) without being related. This method is most meaningful when the shared libraries are specialized or uncommon.

---

### 8. Identifier Names — *~4% of the overall score*

**What it does:** Collects every variable, function, and class name used anywhere in each project (excluding language keywords). Compares the two sets.

**Think of it as:** Comparing the glossaries of two technical documents. Shared specialized terminology — like `user_embedding`, `priceMatrix`, or `normalise_weights` — is more telling than shared common words like `index` or `data`.

**High score means:** Both projects use many of the same names for their variables and internal concepts.

**What it misses:** Common names are everywhere and will inflate this score. Very generic projects may score high without any real connection.

---

### 9. Complexity Profile — *~4% of the overall score*

**What it does:** Measures how complex each function is — counting the number of decision points (if-statements, loops, error handling, etc.) inside it. Then compares the *distribution* of complexity scores: does both projects' code have the same mix of simple, medium, and complex functions?

**Think of it as:** Comparing the difficulty profile of two courses. If one has mostly easy assignments with a few very hard ones, and the other matches that pattern exactly, they may be related — even if the topics are different.

**High score means:** Both projects have a similar overall complexity distribution — the same ratio of simple to complex functions.

**What it misses:** Complexity profiles are a weak signal on their own. Many unrelated projects end up with similar distributions. This method is most useful as a tiebreaker.

---

## Reading the Results Together

No single method is definitive. Here is how to interpret combinations:

| Pattern | Likely explanation |
|---|---|
| File Hash is high | Direct file copying, possibly with minor cosmetic changes |
| Line Similarity and Token Fingerprinting are both high | Substantial code was copied and lightly modified |
| Structure (AST) is high but Line Similarity is low | Code was rewritten from scratch but follows the same design |
| Function Names and Identifier Names are high | Naming conventions were carried over, possibly alongside structural copying |
| Only Import Analysis is high | Both projects use a common framework — not evidence of copying on its own |
| All methods are low | Projects appear to be independently developed |

The output JSON file for each comparison contains the individual score for every method, which files matched, and (for Line Similarity) the specific lines that are shared.
