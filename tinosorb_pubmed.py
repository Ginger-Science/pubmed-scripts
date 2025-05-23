#!/usr/bin/env python3
"""
Fetch Tinosorb-related PubMed papers and export to Excel.

Usage
-----
$ python3 tinosorb_pubmed.py
"""

import time
import pandas as pd
from Bio import Entrez

# ------------------------------------------------------------------
# 1 ── USER CONFIGURATION
# ------------------------------------------------------------------
Entrez.email = "nina@marsmetro.com"        # ← change to your contact email

CORE_TERMS = [
    "Tinosorb",
    "bemotrizinol",      # Tinosorb S (BEMT, bis-ethylhexyloxyphenol methoxyphenyl triazine)
    '"bis-ethylhexyloxyphenol methoxyphenyl triazine"',
    '"Tinosorb M"',
    "methylene bis-benzotriazolyl tetramethylbutylphenol"
]

CONTEXT_TERMS = [
    "photostability",
    "toxicity",
    "UV protection",
    "skin absorption",
    "endocrine",
    "cancer risk"
]

DATE_RANGE      = '("2000/01/01"[Date - Create] : "2025/05/21"[Date - Create])'
HUMANS_ONLY     = True
USE_MESH_TERN   = False      # not needed here; left for parity
RETMAX          = 500
PAUSE_SECONDS   = 0.35
OUTFILE         = "Tinosorb_PubMed_Results.xlsx"

# ------------------------------------------------------------------
# 2 ── BUILD PUBMED QUERY
# ------------------------------------------------------------------
core_block    = " OR ".join(f'{kw}[Title/Abstract]' for kw in CORE_TERMS)
context_block = " OR ".join(f'{kw}[Title/Abstract]' for kw in CONTEXT_TERMS)

query_parts = [f"({core_block})"]
if CONTEXT_TERMS:
    query_parts.append(f"({context_block})")
if HUMANS_ONLY:
    query_parts.append('"Humans"[MeSH Terms]')
query_parts.append(DATE_RANGE)

full_query = " AND ".join(query_parts)
print(f"🔎 PubMed query:\n{full_query}\n")

# ------------------------------------------------------------------
# 3 ── SEARCH PUBMED
# ------------------------------------------------------------------
search_handle = Entrez.esearch(
    db="pubmed",
    term=full_query,
    retmax=RETMAX,
    sort="relevance"
)
id_list = Entrez.read(search_handle)["IdList"]
print(f"Found {len(id_list)} candidate records\n")

# ------------------------------------------------------------------
# 4 ── PREP DATAFRAME
# ------------------------------------------------------------------
df = pd.DataFrame(
    columns=[
        "PMID", "Title", "Abstract", "Authors",
        "Journal", "Year", "Keywords", "URL", "Affiliations"
    ]
)

# ------------------------------------------------------------------
# 5 ── FETCH & PROCESS ARTICLES
# ------------------------------------------------------------------
for i, pmid in enumerate(id_list, 1):
    try:
        records = Entrez.read(
            Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
        )

        for article in records["PubmedArticle"]:
            medline   = article["MedlineCitation"]
            article_md = medline["Article"]

            title = article_md.get("ArticleTitle", "")
            abstract = " ".join(
                article_md["Abstract"]["AbstractText"]
            ) if "Abstract" in article_md else ""

            # Post-fetch relevance guard
            haystack = (title + " " + abstract).lower()
            if not any(term.strip('"').lower() in haystack for term in CORE_TERMS):
                continue

            authors = ", ".join(
                f"{a.get('LastName', '')} {a.get('ForeName', '')}".strip()
                for a in article_md.get("AuthorList", [])
            )

            affiliations = []
            for a in article_md.get("AuthorList", []):
                if a.get("AffiliationInfo"):
                    affiliations.append(a["AffiliationInfo"][0]["Affiliation"])
            affiliations = "; ".join(sorted(set(affiliations)))

            journal = article_md["Journal"]["Title"]
            year    = article_md["Journal"]["JournalIssue"]["PubDate"].get("Year", "")
            keywords = ", ".join(
                kw["DescriptorName"]
                for kw in medline.get("MeshHeadingList", [])
            )
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            df.loc[len(df)] = [
                pmid, title, abstract, authors,
                journal, year, keywords, url, affiliations
            ]

        if i % 25 == 0 or i == len(id_list):
            print(f"  • processed {i}/{len(id_list)} PMIDs")

        time.sleep(PAUSE_SECONDS)

    except Exception as e:
        print(f"⚠️  Error on PMID {pmid}: {e}")

# ------------------------------------------------------------------
# 6 ── SAVE TO EXCEL
# ------------------------------------------------------------------
df.to_excel(OUTFILE, index=False)
print(f"\n✅ Export complete → {OUTFILE}")
