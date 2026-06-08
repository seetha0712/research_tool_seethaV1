// Simple KV store for tracking sent articles
// Uses Vercel KV if available, falls back to in-memory (not persistent across cold starts)

let kvStore = null;

// Try to use Vercel KV if available
async function getKV() {
  if (kvStore !== null) return kvStore;

  try {
    // Dynamic import for Vercel KV
    const { kv } = await import('@vercel/kv');
    kvStore = kv;
    console.log('Using Vercel KV for persistent storage');
    return kvStore;
  } catch {
    console.log('Vercel KV not available, using fallback');
    kvStore = false;
    return null;
  }
}

// Fallback in-memory store (loses state on cold start)
const memoryStore = new Map();

const SENT_ARTICLES_KEY = 'sent_article_ids';
const MAX_STORED_IDS = 500; // Keep last 500 article IDs

export async function getSentArticleIds() {
  const kv = await getKV();

  if (kv) {
    const ids = await kv.get(SENT_ARTICLES_KEY);
    return ids || [];
  }

  return memoryStore.get(SENT_ARTICLES_KEY) || [];
}

export async function addSentArticleIds(newIds) {
  const kv = await getKV();
  const existing = await getSentArticleIds();

  // Combine and deduplicate, keeping most recent
  const combined = [...new Set([...newIds, ...existing])].slice(0, MAX_STORED_IDS);

  if (kv) {
    await kv.set(SENT_ARTICLES_KEY, combined);
  } else {
    memoryStore.set(SENT_ARTICLES_KEY, combined);
  }

  return combined;
}

export async function filterUnsentArticles(articles) {
  const sentIds = await getSentArticleIds();
  const sentIdSet = new Set(sentIds);

  return articles.filter(article => {
    const id = article.id?.toString() || article.link;
    return !sentIdSet.has(id);
  });
}

export async function markArticlesAsSent(articles) {
  const ids = articles.map(a => a.id?.toString() || a.link).filter(Boolean);
  return addSentArticleIds(ids);
}
