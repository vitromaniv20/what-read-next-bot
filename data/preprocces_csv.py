import pandas as pd
import ast
import html

INPUT = "your_50000_books.csv"   # <-- your raw file
OUTPUT = "data/books.csv"

GENRE_PRIORITY = {
    'science fiction': 'sci-fi', 'sci-fi': 'sci-fi', 'dystopia': 'sci-fi',
    'post apocalyptic': 'sci-fi', 'apocalyptic': 'sci-fi', 'cyberpunk': 'sci-fi',
    'fantasy': 'fantasy', 'magic': 'fantasy', 'supernatural': 'fantasy',
    'romance': 'romance', 'historical romance': 'romance', 'love': 'romance',
    'mystery': 'mystery', 'thriller': 'mystery', 'crime': 'mystery',
    'suspense': 'mystery', 'detective': 'mystery',
    'historical': 'historical', 'historical fiction': 'historical',
    'history': 'historical', 'war': 'historical',
    'young adult': 'young_adult', 'ya': 'young_adult', 'teen': 'young_adult',
    'juvenile': 'young_adult', 'coming of age': 'young_adult',
    'horror': 'horror', 'ghost': 'horror', 'paranormal': 'horror',
    'nonfiction': 'nonfiction', 'non-fiction': 'nonfiction',
    'biography': 'nonfiction', 'memoir': 'nonfiction', 'self-help': 'nonfiction',
}

def map_genre(val):
    if pd.isna(val):
        return 'fantasy'
    try:
        genres = ast.literal_eval(str(val))
        if not isinstance(genres, list):
            genres = str(val).split(',')
    except Exception:
        genres = str(val).split(',')
    genres = [g.strip().lower() for g in genres]
    for g in genres:
        if g in GENRE_PRIORITY:
            return GENRE_PRIORITY[g]
    return 'fantasy'

def clean_author(val):
    if pd.isna(val):
        return "Unknown"
    first = str(val).split(',')[0].strip()
    first = first.split('(')[0].strip()
    return html.escape(first)

print("Reading...")
df = pd.read_csv(INPUT, low_memory=False)

out = pd.DataFrame()
out['title'] = df['title'].fillna('Unknown').apply(lambda x: html.escape(str(x)))
out['author'] = df['author'].apply(clean_author)
out['genres'] = df['genres'].apply(map_genre)
out['description'] = df['description'].fillna('').apply(lambda x: html.escape(str(x).replace('<','').replace('>','')))
out['coverimg'] = df.get('coverImg', df.get('cover_img', '')).fillna('')
out['rating'] = pd.to_numeric(df.get('rating', 0), errors='coerce')
out['pages'] = pd.to_numeric(df.get('pages', 0), errors='coerce').astype('Int64')

# Mark as famous if it has many ratings (adjust threshold as needed)
if 'numRatings' in df.columns:
    out['is_famous'] = (pd.to_numeric(df['numRatings'], errors='coerce') > 10000).astype(int)
else:
    out['is_famous'] = 1

out = out[out['title'].str.len() > 0]
out.to_csv(OUTPUT, index=False, encoding='utf-8')
print(f"Saved {len(out)} books to {OUTPUT}")
print(out['genres'].value_counts())