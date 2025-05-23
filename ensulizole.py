#!/usr/bin/env python3
"""
Fetch MC1R / red-hair–relevant PubMed papers and export to Excel.

Usage
-----
$ python3 avobenzone.py
"""

import time
import pandas as pd
from Bio import Entrez

# ------------------------------------------------------------------
# 1 ── USER CONFIGURATION
# ------------------------------------------------------------------
Entrez.email = "nina@marsmetro.com"        # ← change to your contact email

CORE_TERMS = [
    "ensulizole",
    "phenylbenzimidazole sulfonic acid"

    
]

CONTEXT_TERMS = [
    "teratogenic",
    "toxicity",
    "UV sensitivity",
    "sunburn",
    "cancer risk"
]

DATE_RANGE      = '("2000/01/01"[Date - Create] : "2025/05/21"[Date - Create])'
HUMANS_ONLY     = True     # include '"Humans"[MeSH Terms]'
USE_MESH_MC1R   = False    # include '"Receptor, Melanocortin, Type 1"[MeSH]'
RETMAX          = 500      # how many PubMed IDs to pull (top relevance first)
PAUSE_SECONDS   = 0.35     # delay between efetch calls to respect NCBI limits
OUTFILE         = "Ensulizole_PubMed_Results.xlsx"

# ------------------------------------------------------------------
# 2 ── BUILD PUBMED QUERY
# ------------------------------------------------------------------
core_block    = " OR ".join(f'{kw}[Title/Abstract]' for kw in CORE_TERMS)
context_block = " OR ".join(f'{kw}[Title/Abstract]' for kw in CONTEXT_TERMS)

query_parts = [f"({core_block})"]                       # mandatory
if CONTEXT_TERMS:
    query_parts.append(f"({context_block})")            # AND context
if USE_MESH_MC1R:
    query_parts.append('"Receptor, Melanocortin, Type 1"[MeSH Terms]')
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
search_record = Entrez.read(search_handle)
id_list = search_record["IdList"]
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
        fetch_handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
        records = Entrez.read(fetch_handle)

        for article in records["PubmedArticle"]:
            medline   = article["MedlineCitation"]
            article_md = medline["Article"]

            title   = article_md.get("ArticleTitle", "")
            abstract = " ".join(
                article_md["Abstract"]["AbstractText"]
            ) if "Abstract" in article_md else ""

            # Post-fetch relevance guard
            haystack = (title + " " + abstract).lower()
            if not any(term.strip('"').lower() in haystack for term in CORE_TERMS):
                continue  # skip loose match

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

        time.sleep(PAUSE_SECONDS)  # be polite to NCBI servers

    except Exception as e:
        print(f"⚠️  Error on PMID {pmid}: {e}")

# ------------------------------------------------------------------
# 6 ── SAVE TO EXCEL
# ------------------------------------------------------------------
df.to_excel(OUTFILE, index=False)
print(f"\n✅ Export complete → {OUTFILE}")
