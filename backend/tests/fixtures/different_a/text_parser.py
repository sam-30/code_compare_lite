"""Token-level text parsing and lexical analysis."""
import re
from collections import Counter, defaultdict
from typing import Dict, Iterator, List, Tuple


PUNCTUATION = re.compile(r"[^\w\s]")
WHITESPACE = re.compile(r"\s+")


def tokenize(text: str) -> List[str]:
    cleaned = PUNCTUATION.sub(" ", text.lower())
    return [tok for tok in WHITESPACE.split(cleaned) if tok]


def bigrams(tokens: List[str]) -> List[Tuple[str, str]]:
    return [(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)]


def term_frequency(tokens: List[str]) -> Dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = len(tokens)
    return {word: count / total for word, count in counts.items()}


def inverse_document_frequency(
    documents: List[List[str]],
) -> Dict[str, float]:
    import math

    num_docs = len(documents)
    doc_freq: Counter = Counter()
    for doc in documents:
        for word in set(doc):
            doc_freq[word] += 1
    return {
        word: math.log(num_docs / freq)
        for word, freq in doc_freq.items()
        if freq > 0
    }


def tfidf(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = term_frequency(tokens)
    return {word: tf_val * idf.get(word, 0.0) for word, tf_val in tf.items()}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self._pos = 0

    def peek(self) -> str:
        if self._pos < len(self.source):
            return self.source[self._pos]
        return ""

    def advance(self) -> str:
        char = self.peek()
        self._pos += 1
        return char

    def skip_whitespace(self) -> None:
        while self._pos < len(self.source) and self.source[self._pos].isspace():
            self._pos += 1

    def read_word(self) -> str:
        start = self._pos
        while self._pos < len(self.source) and self.source[self._pos].isalnum():
            self._pos += 1
        return self.source[start : self._pos]

    def tokens(self) -> Iterator[str]:
        while self._pos < len(self.source):
            self.skip_whitespace()
            if self._pos >= len(self.source):
                break
            if self.source[self._pos].isalnum():
                yield self.read_word()
            else:
                yield self.advance()


class VocabularyBuilder:
    def __init__(self) -> None:
        self._vocab: Dict[str, int] = {}
        self._next_id = 0

    def add(self, token: str) -> int:
        if token not in self._vocab:
            self._vocab[token] = self._next_id
            self._next_id += 1
        return self._vocab[token]

    def encode(self, tokens: List[str]) -> List[int]:
        return [self.add(t) for t in tokens]

    def size(self) -> int:
        return len(self._vocab)

    def lookup(self, token: str) -> int:
        return self._vocab.get(token, -1)
