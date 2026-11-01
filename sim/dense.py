import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import CrossEncoder, SentenceTransformer

EMB_DIR = Path(__file__).resolve().parent / "runs" / "emb"
EMBEDDER = "BAAI/bge-m3"
RERANKER = "BAAI/bge-reranker-v2-m3"
DOC_FIELDS = ("title", "location", "problem", "cause", "resolution")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
GPU = threading.Lock()
torch.backends.cuda.enable_flash_sdp(False)
torch.backends.cuda.enable_mem_efficient_sdp(False)


def doc_text(record):
    return "\n".join(record[f] for f in DOC_FIELDS if record[f])


@lru_cache(maxsize=1)
def embedder():
    model = SentenceTransformer(EMBEDDER, device=DEVICE)
    model.max_seq_length = 512
    if DEVICE == "cuda":
        model.half()
    return model


@lru_cache(maxsize=1)
def reranker():
    model = CrossEncoder(RERANKER, device=DEVICE, max_length=512)
    if DEVICE == "cuda":
        model.model.half()
    return model


def corpus_matrix(records):
    EMB_DIR.mkdir(parents=True, exist_ok=True)
    path = EMB_DIR / "bge-m3.npy"
    codes_path = EMB_DIR / "bge-m3.codes.txt"
    codes = [r["case_code"] for r in records]
    if path.exists() and codes_path.read_text().split("\n") == codes:
        return np.load(path)
    matrix = embedder().encode([doc_text(r) for r in records], batch_size=32, normalize_embeddings=True,
                               show_progress_bar=True, convert_to_numpy=True).astype(np.float32)
    np.save(path, matrix)
    codes_path.write_text("\n".join(codes))
    return matrix


@lru_cache(maxsize=4096)
def query_vector(query):
    with GPU:
        return embedder().encode([query], normalize_embeddings=True, convert_to_numpy=True)[0].astype(np.float32)


def similarities(matrix, query):
    return matrix @ query_vector(query)


_rerank_cache = {}


def rerank_scores(query, codes, texts):
    missing = [(c, t) for c, t in zip(codes, texts) if (query, c) not in _rerank_cache]
    if missing:
        with GPU:
            scores = reranker().predict([(query, t) for _, t in missing], batch_size=32, activation_fn=torch.nn.Sigmoid())
        for (c, _), s in zip(missing, scores):
            _rerank_cache[(query, c)] = float(s)
    return [_rerank_cache[(query, c)] for c in codes]
