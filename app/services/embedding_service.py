_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("[Embedding Service] Loading model...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("[Embedding Service] Model loaded [OK]")
    return _model

def embed_text(text: str) -> list[float]:
    model = _get_model()
    return model.encode(text, convert_to_numpy=True).tolist()
