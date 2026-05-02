import tqdm
import pandas as pd
import json

# Clustering & classification
import hdbscan
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

from processing import prepare_text, extract_keywords, embed_texts, analyze_sentiment, get_keywords_per_cluster


def run_cached_pipeline(df):
    """
    df columns required:
    id, title, content, url, date, location
    """

    tqdm.pandas()

    # ---- Step 1: Prepare text ----
    df["text"] = df.progress_apply(
        lambda r: prepare_text(r["title"], r["content"]),
        axis=1
    )

    # ---- Step 2: Keywords ----
    df["keywords"] = df["text"].progress_apply(extract_keywords)

    # ---- Step 3: Embeddings ----
    embeddings = embed_texts(df["text"].tolist())

    # ---- Step 4: Clustering ----
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=20,
        min_samples=10,
        metric="euclidean"
    )
    df["cluster_id"] = clusterer.fit_predict(embeddings)

    cluster_keywords = get_keywords_per_cluster(df)
    print(cluster_keywords)

    # ---- Step 5: Cluster → Category (MANUAL MAP) ----
    # Example mapping (you define this after inspection)
    CLUSTER_TO_CATEGORY = {
        0: "Politics",
        1: "Technology",
        2: "Health",
        3: "Business",
        4: "Sports"
    }

    df["category"] = df["cluster_id"].map(CLUSTER_TO_CATEGORY)
    df["category"] = df["category"].fillna("Other")

    # ---- Step 6: Train classifier ----
    mask = df["category"] != "Other"
    le = LabelEncoder()
    y = le.fit_transform(df.loc[mask, "category"])

    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced"
    )
    clf.fit(embeddings[mask], y)

    # ---- Step 7: Predict categories ----
    df["category"] = le.inverse_transform(
        clf.predict(embeddings)
    )

    # ---- Step 8: Sentiment ----
    df["sentiment"] = df["text"].progress_apply(analyze_sentiment)

    # ================= CSV OUTPUTS ================= #

    # CSV1: id, date, category, location, sentiment
    csv1 = df[["id", "date", "category", "location", "sentiment"]]
    csv1.to_csv("output/csv1_core.csv", index=False)

    # CSV2: id, embedding
    csv2 = pd.DataFrame({
        "id": df["id"],
        "embedding": [json.dumps(e.tolist()) for e in embeddings]
    })
    csv2.to_csv("output/csv2_embeddings.csv", index=False)

    # CSV3: date, keyword
    rows = []
    for _, r in df.iterrows():
        for kw in r["keywords"]:
            rows.append({"date": r["date"], "keyword": kw})

    pd.DataFrame(rows).to_csv(
        "output/csv3_keywords.csv", index=False
    )

    # CSV4: id, title, url
    csv4 = df[["id", "title", "url"]]
    csv4.to_csv("output/csv4_metadata.csv", index=False)

    print("Cached pipeline complete")


def main():
    pass

if __name__ == "__main__":
    main()