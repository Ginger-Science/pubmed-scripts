"""Embed abstracts, cluster, and export a JSON map for visualization."""
import pandas as pd
import sentence_transformers, umap, hdbscan, json

def cluster(excel_file: str, out_json: str = "map.json"):
    df = pd.read_excel(excel_file)
    texts = (df["Title"].fillna("") + ". " + df["Abstract"].fillna("")).tolist()

    model = sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts, show_progress_bar=True)

    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, metric="cosine")
    coords = reducer.fit_transform(embeddings)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=5, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)

    df["x"], df["y"], df["cluster"] = coords[:,0], coords[:,1], labels

    df.to_json(out_json, orient="records")
    print(f"Saved JSON map → {out_json}")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Cluster abstract embeddings")
    p.add_argument("excel_file", help="Input Excel from litminer harvest")
    p.add_argument("--out", default="map.json")
    args = p.parse_args()
    cluster(args.excel_file, args.out)
