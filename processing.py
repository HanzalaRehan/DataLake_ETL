from models import kw_model, embedding_model, sent_tokenizer, sent_model, SENTIMENT_LABELS
import pandas as pd
from collections import Counter
import torch
import torch.nn.functional as F

def prepare_text(title, content):
    title = "" if not isinstance(title, str) else title
    content = "" if not isinstance(content, str) else content
    body = " ".join(content.split())
    return f"{title}. {body}".strip()

def extract_keywords(text, top_k=10):
    keywords = kw_model.extract_keywords(
        text,
        keyphrase_ngram_range=(1, 3),
        stop_words="english",
        use_mmr=True,
        diversity=0.7,
        top_n=top_k
    )
    return [kw for kw, _ in keywords]

def embed_texts(texts, batch_size=64):
    return embedding_model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True
    )

def analyze_sentiment(text):
    inputs = sent_tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )
    with torch.no_grad():
        outputs = sent_model(**inputs)
        probs = F.softmax(outputs.logits, dim=1)[0]

    label = SENTIMENT_LABELS[int(torch.argmax(probs))]
    return label

def get_keywords_per_cluster(
    df,
    keywords_col="keywords",
    cluster_col="cluster_id",
    top_n=10
):
    """
    Returns a DataFrame:
    cluster_id | top_keywords
    """

    results = []

    # Ignore HDBSCAN noise
    clusters = sorted(c for c in df[cluster_col].unique() if c != -1)

    for cluster_id in clusters:
        cluster_rows = df[df[cluster_col] == cluster_id]

        # Flatten all keyword lists in this cluster
        all_keywords = []
        for kws in cluster_rows[keywords_col]:
            if isinstance(kws, list):
                all_keywords.extend(kws)

        if not all_keywords:
            continue

        # Count keyword frequency
        counter = Counter(all_keywords)

        top_keywords = [
            kw for kw, _ in counter.most_common(top_n)
        ]

        results.append({
            "cluster_id": cluster_id,
            "top_keywords": top_keywords
        })

    return pd.DataFrame(results)