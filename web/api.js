// A single ordered game-request lane. Uncertain writes retain their exact intent.
const base = new URL('.', document.baseURI);
export const storageScope = `orbloam-v1:${base.pathname}`;
export function loadLocal(key) { try { return localStorage.getItem(`${storageScope}:${key}`); } catch { return null; } }
export function saveLocal(key, value) { try { value === null ? localStorage.removeItem(`${storageScope}:${key}`) : localStorage.setItem(`${storageScope}:${key}`, value); } catch { /* Private modes may forbid persistence. */ } }
export class ApiError extends Error {
  constructor(status, code) { super(code); this.status = status; this.code = code; }
}
// The native JSON codec represents maps as ordered [key, value] pairs.
// This is a view adapter, not an economic simulation or a source of game rewards.
export function decodeSnapshot(data) {
  const map = pairs => {
    if (!Array.isArray(pairs) || pairs.some(p => !Array.isArray(p) || p.length !== 2 || typeof p[0] !== 'string')) throw new ApiError(502, 'invalid_response');
    const result = Object.create(null);
    for (const [key, value] of pairs) { if (Object.hasOwn(result, key)) throw new ApiError(502, 'invalid_response'); result[key] = value; }
    return result;
  };
  if (!Array.isArray(data.world.colonies)) throw new ApiError(502, 'invalid_response');
  return {...data, world: {...data.world, nodes: map(data.world.nodes), colonies: data.world.colonies.map(colony =>
    ({...colony, inventory: map(colony.inventory), research: map(colony.research), receipts: map(colony.receipts)}))}};
}
export class GameAPI {
  constructor(onState, onPending) {
    this.token = ''; this.state = null; this.queue = []; this.busy = false; this.onState = onState; this.onPending = onPending;
    this.pollQueued = false; this.pending = null; this.writeQueued = false; this.latency = 0; this.maximumInFlight = 0; this.inFlight = 0;
  }
  enqueue(work, urgent = false) {
    return new Promise((resolve, reject) => { const task = {work, resolve, reject}; urgent ? this.queue.unshift(task) : this.queue.push(task); this.drain(); });
  }
  async drain() {
    if (this.busy) return; this.busy = true;
    try { while (this.queue.length) { const task = this.queue.shift(); try { task.resolve(await task.work()); } catch (error) { task.reject(error); } } }
    finally { this.busy = false; }
  }
  async request(path, method = 'GET', body) {
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 20000), started = performance.now();
    const headers = {}; if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    this.inFlight++; this.maximumInFlight = Math.max(this.maximumInFlight, this.inFlight);
    try {
      const response = await fetch(new URL(path, base), {method, headers, body: body === undefined ? undefined : JSON.stringify(body),
        cache: 'no-store', credentials: 'omit', redirect: 'error', signal: controller.signal});
      let data; try { data = await response.json(); } catch { throw new ApiError(response.status || 502, 'invalid_response'); }
      this.latency = performance.now() - started;
      if (!response.ok) throw new ApiError(response.status, typeof data.error === 'string' ? data.error : data.error?.code || `http_${response.status}`);
      if (data.world && Number.isSafeInteger(data.me)) { data = decodeSnapshot(data); this.state = data; this.onState(data); }
      return data;
    } catch (error) { if (error instanceof ApiError) throw error; throw new ApiError(0, 'network_uncertain'); }
    finally { clearTimeout(timeout); this.inFlight--; }
  }
  catalog() { return this.enqueue(() => this.request('api/catalog')); }
  join(name, token) { return this.enqueue(() => this.request('api/join', 'POST', {name, token}), true); }
  async restore(token) {
    this.token = token;
    const state = await this.enqueue(() => this.request('api/view'), true);
    try { const saved = JSON.parse(loadLocal('pending') || 'null'); if (saved?.owner === state.me) this.setPending(saved); } catch { saveLocal('pending', null); }
    return state;
  }
  poll() {
    if (!this.token || this.pollQueued) return Promise.resolve(null);
    this.pollQueued = true;
    return this.enqueue(() => this.request('api/sync', 'POST', {})).finally(() => { this.pollQueued = false; });
  }
  setPending(record) { this.pending = record; this.pendingError = null; saveLocal('pending', record ? JSON.stringify(record) : null); this.onPending(record); }
  command(op, parameters = {}) {
    if (this.writeQueued || this.pending) return Promise.reject(new ApiError(0, 'pending_action'));
    this.writeQueued = true;
    return this.enqueue(async () => {
      if (this.pending) throw new ApiError(0, 'pending_action');
      const colony = this.state?.world.colonies.find(c => c.id === this.state.me);
      if (!colony) throw new ApiError(401, 'unauthorized');
      const action = {op, sequence: colony.sequence + 1, index: 0, value: 0, x: 0, y: 0, text: '', ...parameters};
      const record = {owner: colony.id, action}; this.setPending(record);
      return this.sendIntent(record);
    }, true).finally(() => { this.writeQueued = false; });
  }
  async sendIntent(record) {
    try {
      for (let attempt = 0; attempt < 4; attempt++) {
        try { const result = await this.request('api/action', 'POST', record.action); this.setPending(null); return result; }
        catch (error) {
          if (error.code !== 'catchup_required' || attempt === 3) throw error;
          await this.request('api/sync', 'POST', {});
        }
      }
    } catch (error) {
      // A network/5xx failure may have occurred after publication. Never mint a new sequence.
      this.pendingError = error.code;
      if (error.status >= 400 && error.status < 500 && error.code !== 'sequence_conflict') this.setPending(null);
      throw error;
    }
  }
  retryPending() {
    if (!this.pending) return Promise.resolve(null);
    const record = this.pending;
    return this.enqueue(() => this.pending === record ? this.sendIntent(record) : null, true);
  }
  discardPending() { this.setPending(null); }
}
export const ERROR_TEXT = {
  unauthorized: 'This recovery key does not belong to this world.',
  network_uncertain: 'Connection interrupted. Any unfinished action will be checked before another is sent.',
  persistence_shape: 'The save could not be read safely. Keep it intact and contact the server operator.',
  schema_mismatch: 'This save belongs to a different game format. Keep the original data.',
  invalid_registration: 'Check your colony name and recovery key.',
  invalid_json: 'The server could not read this action.', invalid_action: 'That action is not available.',
  invalid_name: 'Choose a name of 1–32 characters.', world_full: 'All 64 core places are occupied.',
  research_cost: 'Not enough Essence or research materials.', research_order: 'Discover this node’s parent first. An owned node cannot be purchased again.',
  recipe_locked: 'This workshop or recipe is still locked.', building_limit: 'No workshop places remain. Discover Industry or grow your core.',
  building_cost: 'Not enough timber or stone.', building_spacing: 'Leave a little more space between workshops.',
  out_of_range: 'That is beyond your core’s reach.', building_missing: 'This workshop no longer exists.',
  transfer_cost: 'Not enough goods, or the recipient’s store is full.', neighbor_missing: 'That core could not be found.',
  warehouse_full: 'The store is full.', transaction_conflict: 'Another update arrived first. Check the current state before trying again.',
  sequence_conflict: 'Another device changed the action sequence. Review the current state before clearing the pending action.',
  catchup_required: 'The world is catching up with elapsed time.', pending_action: 'Finishing the previous action.',
  content_type: 'Actions must use JSON.', invalid_response: 'A valid game response was not received.'
};
export const errorText = error => ERROR_TEXT[error.code] || `Connection error (${error.status || 0}). Reconnect without deleting your data.`;
