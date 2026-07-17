// Native IndexedDB wrapper for offline document caching + queued write actions.
// ponytail: no idb/dexie — two object stores and a handful of promisified calls is the whole ask.

const DB_NAME = 'edgp-offline';
const DB_VERSION = 1;
const DOCS_STORE = 'documents';
const QUEUE_STORE = 'pending-actions';

export interface OfflineDocument {
  id: string;
  [key: string]: unknown;
}

export interface QueuedAction {
  id?: number;
  type: string;
  payload: unknown;
  createdAt: number;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(DOCS_STORE)) {
        db.createObjectStore(DOCS_STORE, { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        db.createObjectStore(QUEUE_STORE, { keyPath: 'id', autoIncrement: true });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function txDone<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// --- T-3067: offline document list ---

export async function cacheDocuments(docs: OfflineDocument[]): Promise<void> {
  const db = await openDb();
  const tx = db.transaction(DOCS_STORE, 'readwrite');
  const store = tx.objectStore(DOCS_STORE);
  docs.forEach((doc) => store.put(doc));
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getCachedDocuments(): Promise<OfflineDocument[]> {
  const db = await openDb();
  const tx = db.transaction(DOCS_STORE, 'readonly');
  return txDone(tx.objectStore(DOCS_STORE).getAll());
}

// --- T-3068: queue offline write actions ---

export async function queueAction(type: string, payload: unknown): Promise<void> {
  const db = await openDb();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  tx.objectStore(QUEUE_STORE).add({ type, payload, createdAt: Date.now() });
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getQueuedActions(): Promise<QueuedAction[]> {
  const db = await openDb();
  const tx = db.transaction(QUEUE_STORE, 'readonly');
  return txDone(tx.objectStore(QUEUE_STORE).getAll());
}

async function clearQueuedAction(id: number): Promise<void> {
  const db = await openDb();
  const tx = db.transaction(QUEUE_STORE, 'readwrite');
  tx.objectStore(QUEUE_STORE).delete(id);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

/**
 * Replays queued actions against `handler`, in order, removing each from the
 * queue once it succeeds. A failure stops the replay (queue order preserved)
 * so the next `sync()` (e.g. next 'online' event) retries from that point.
 */
export async function sync(handler: (action: QueuedAction) => Promise<void>): Promise<void> {
  const actions = await getQueuedActions();
  for (const action of actions) {
    if (action.id === undefined) continue;
    await handler(action);
    await clearQueuedAction(action.id);
  }
}

let syncListenerAttached = false;

/** Wires `sync(handler)` to fire automatically whenever the browser regains connectivity. */
export function registerBackgroundSync(handler: (action: QueuedAction) => Promise<void>): void {
  if (syncListenerAttached || typeof window === 'undefined') return;
  syncListenerAttached = true;
  window.addEventListener('online', () => {
    sync(handler).catch((err) => console.error('offline-db sync failed', err));
  });
}
