import tqdm
import pandas as pd
import json

# Clustering & classification

from models import embedding_model
from processing import prepare_text, extract_keywords, analyze_sentiment

def run_live_pipeline(article, clf, le):
    """
    article: dict with
    id, title, content, url, date, location
    """

    text = prepare_text(article["title"], article["content"])

    keywords = extract_keywords(text)
    embedding = embedding_model.encode(
        [text], normalize_embeddings=True
    )[0]

    category = le.inverse_transform(
        clf.predict([embedding])
    )[0]

    sentiment = analyze_sentiment(text)

    # ---- CSV-compatible outputs ----
    csv1 = {
        "id": article["id"],
        "date": article["date"],
        "category": category,
        "location": article["location"],
        "sentiment": sentiment
    }

    csv2 = {
        "id": article["id"],
        "embedding": json.dumps(embedding.tolist())
    }

    csv3 = [{"date": article["date"], "keyword": k} for k in keywords]

    csv4 = {
        "id": article["id"],
        "title": article["title"],
        "url": article["url"]
    }

    return csv1, csv2, csv3, csv4
