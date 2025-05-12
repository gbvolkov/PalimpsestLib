from functools import lru_cache
from typing import Any, Callable, List, Tuple

from nltk.tokenize import word_tokenize, sent_tokenize

# ---------------------
# Helper: Split a single long word into subwords
# such that each subword's _len is <= max_chunk_size.
def split_long_word(word: str, max_chunk_size: int, _len: Callable[[str], int]) -> List[str]:
    subwords = []
    i = 0
    while i < len(word):
        # Find the largest substring starting at i with _len <= max_chunk_size.
        j = i + 1
        while j <= len(word) and _len(word[i:j]) <= max_chunk_size:
            j += 1
        # word[i:j-1] is the largest acceptable chunk.
        # If no progress is made (should not happen), force one character.
        if j - 1 == i:
            subwords.append(word[i:j])
            i = j
        else:
            subwords.append(word[i:j-1])
            i = j - 1
    return subwords

# ---------------------
# Helper: Split a long sentence into smaller pieces.
# The sentence is first split on whitespace. For any word too long,
# further split it into subwords.
def split_long_sentence(sentence: str, max_chunk_size: int, _len: Callable[[str], int]) -> List[str]:
    if _len(sentence) <= max_chunk_size:
        return [sentence]
    
    #words = sentence.split()  # simple whitespace split
    words = word_tokenize(sentence, language='russian')
    result = []
    current_line = ""
    
    for word in words:
        # If the individual word is too long, split it further.
        if _len(word) > max_chunk_size:
            subwords = split_long_word(word, max_chunk_size, _len)
        else:
            subwords = [word]
        
        for token in subwords:
            candidate = current_line + (" " if current_line else "") + token
            if _len(candidate) <= max_chunk_size:
                current_line = candidate
            else:
                if current_line:
                    result.append(current_line)
                current_line = token
    if current_line:
        result.append(current_line)
    return result

# ---------------------
# Preprocess the list of sentences: if a sentence's _len is more than max_chunk_size,
# split it further.
def preprocess_sentences(sentences: List[str], max_chunk_size: int, _len: Callable[[str], int]) -> List[str]:
    processed = []
    for sentence in sentences:
        if _len(sentence) > max_chunk_size:
            processed.extend(split_long_sentence(sentence, max_chunk_size, _len))
        else:
            processed.append(sentence)
    return processed

def chunk_sentences(sentences: List[str], max_chunk_size: int, overlap_size: int = 0, _len: Callable[[str], int] = len) -> List[str]:
    # Preprocess sentences to ensure none is longer than max_chunk_size.
    sentences = preprocess_sentences(sentences, max_chunk_size-overlap_size, _len)
    
    chunks = []
    current_chunk = []
    current_length = 0
    idx = 0

    while idx < len(sentences):
        sentence = sentences[idx]
        sentence_length = _len(sentence)
        
        if current_length + sentence_length <= max_chunk_size:
            current_chunk.append(sentence)
            current_length += sentence_length
            idx += 1  # move to next sentence
        else:
            if not current_chunk:
                # The sentence itself is too long (should not happen after preprocessing),
                # but in that case, add it as its own chunk.
                chunks.append(sentence)
                idx += 1
            else:
                # Finalize the current chunk.
                chunks.append(" ".join(current_chunk))
                # Compute overlap from the end of the current_chunk.
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    s_len = _len(s)
                    if overlap_length + s_len <= overlap_size:
                        overlap_sentences.insert(0, s)
                        overlap_length += s_len
                    else:
                        break
                # Try to add the problematic sentence to the overlap.
                if overlap_sentences and (overlap_length + sentence_length <= max_chunk_size):
                    current_chunk = overlap_sentences + [sentence]
                    current_length = overlap_length + sentence_length
                    idx += 1
                else:
                    # Cannot merge the sentence into the overlap; output it separately.
                    current_chunk = []
                    current_length = 0
                    chunks.append(sentence)
                    idx += 1

    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def split_text_by_lines(
    text: str,
    max_chunk_size: int,
    _len: Callable[[str], int] = len
) -> List[Tuple[str, int]]:
    """
    Split `text` into chunks of at most `max_size` characters,
    breaking only between lines. Lines longer than max_size
    become their own chunk. Returns a list of (chunk, length).
    """
    chunks: List[Tuple[str, int]] = []
    current: List[str] = []
    current_size = 0  # running total of len(part) for part in current

    def flush_current():
        nonlocal current_size
        if current:
            chunk = ''.join(current)
            chunks.append((chunk, current_size))
            current.clear()
            current_size = 0

    for line in text.splitlines(keepends=True):
        line_len = _len(line)
        # Would this line overflow the current chunk?
        if current_size + line_len > max_chunk_size:
            # flush what we've got
            flush_current()
            # if the single line is itself too big, emit it alone
            if line_len > max_chunk_size:
                chunks.append((line, line_len))
                continue
        # otherwise, accumulate it
        current.append(line)
        current_size += line_len

    # flush any remaining
    flush_current()
    return chunks

# Main function.
def split_text(text: str, max_chunk_size: int, _len: Callable[[str], int] = len) -> List[str]:
    chunks = []
    lines = split_text_by_lines(text, max_chunk_size=max_chunk_size, _len=_len)

    for i, (line, line_length) in enumerate(lines, 1):
        if line_length > max_chunk_size:
            sentences = sent_tokenize(line, language='russian')
            chunks.extend(chunk_sentences(sentences=sentences, max_chunk_size=max_chunk_size, _len=_len))
        else:
            chunks.append(line)
    return chunks
