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
    this.pollQueued = false; this.pending = null; this.latency = 0; this.maximumInFlight = 0; this.inFlight = 0;
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
  setPending(record) { this.pending = record; saveLocal('pending', record ? JSON.stringify(record) : null); this.onPending(record); }
  command(op, parameters = {}) {
    return this.enqueue(async () => {
      if (this.pending) throw new ApiError(0, 'pending_action');
      const colony = this.state?.world.colonies.find(c => c.id === this.state.me);
      if (!colony) throw new ApiError(401, 'unauthorized');
      const action = {op, sequence: colony.sequence + 1, index: 0, value: 0, x: 0, y: 0, text: '', ...parameters};
      const record = {owner: colony.id, action}; this.setPending(record);
      return this.sendIntent(record);
    }, true);
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
      if (error.status >= 400 && error.status < 500 && error.code !== 'sequence_conflict') this.setPending(null);
      throw error;
    }
  }
  retryPending() {
    if (!this.pending) return Promise.resolve(null);
    return this.enqueue(() => this.sendIntent(this.pending), true);
  }
  discardPending() { this.setPending(null); }
}
export const ERROR_TEXT = {
  unauthorized: 'キーが認証されませんでした。同じ世界の復帰キーか確認してください。',
  network_uncertain: '通信が完了しませんでした。操作した場合は、同じ操作を再確認してください。',
  persistence_shape: '保存データを安全に読み取れません。リセットせず、サーバーの管理者に確認してください。',
  schema_mismatch: '保存データの形式が、このゲームの版と一致しません。元のデータを保管してください。',
  invalid_registration: '名前または復帰キーの形式を確認してください。',
  invalid_json: '操作内容の形式を読み取れませんでした。', invalid_action: 'この操作は受け付けられません。',
  invalid_name: '名前は1〜32文字にしてください。', world_full: 'この世界の64コアが埋まっています。',
  research_cost: 'エッセンスまたは研究素材が不足しています。', research_order: 'ひとつ前の研究から順番に解放してください。',
  recipe_locked: 'その施設またはレシピの研究がまだ解放されていません。', building_limit: '建物の上限です。工業研究やコアの成長で増えます。',
  building_cost: '原木または石材が足りません。', building_spacing: 'ほかの建物と近すぎます。少し離して置いてください。',
  out_of_range: 'コアから遠すぎます。近くへ移動してください。', building_missing: 'その建物はもう存在しません。',
  transfer_cost: '送る物資が不足しているか、相手の倉庫が満杯です。', neighbor_missing: '送り先のコアが見つかりません。',
  warehouse_full: '倉庫が満杯です。空きをつくってください。', transaction_conflict: '別の更新と競合しました。状態を確認して操作し直してください。',
  sequence_conflict: '別の端末で操作番号が更新されました。現在の状態を確認し、未確定操作を解除してください。',
  catchup_required: '世界が現在時刻に追いつくまで計算しています。', pending_action: '先に未確定の操作を再確認してください。',
  content_type: 'JSON形式の操作が必要です。', invalid_response: 'サーバーからゲームの応答を取得できませんでした。'
};
export const errorText = error => ERROR_TEXT[error.code] || `通信エラー (${error.status || 0})。データを削除せず、再接続してください。`;
