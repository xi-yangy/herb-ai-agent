/**
 * 识别图片本地存储（IndexedDB）。
 *
 * 合规约定：识别上传图片仅保存在本机浏览器中，用于历史记录回看；
 * 服务端不持久化用户图片。清空历史时配合 clearImages 一并清除。
 *
 * 所有 API 失败时静默降级（saveImage 忽略、getImage 返回 null），
 * 保证 IndexedDB 不可用（隐私模式/浏览器限制）时历史链路不受影响（仅无图展示）。
 */

const DB_NAME = 'herb-ai-images'
const DB_VERSION = 1
const STORE_NAME = 'history-images'

let _dbPromise = null

function openDb() {
  if (_dbPromise) return _dbPromise
  _dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB 不可用'))
      return
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error || new Error('打开 IndexedDB 失败'))
  })
  return _dbPromise
}

/** dataURL（含 data:image 前缀）转为 Blob。 */
function dataUrlToBlob(dataUrl) {
  const [head, body] = dataUrl.split(',')
  const mime = (head.match(/data:([^;]+)/) || [])[1] || 'image/jpeg'
  const binary = atob(body)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return new Blob([bytes], { type: mime })
}

/** Blob 转为 dataURL。 */
function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error || new Error('读取 Blob 失败'))
    reader.readAsDataURL(blob)
  })
}

/** 保存识别图：key = 历史记录 id；失败静默忽略，不阻塞历史写入。 */
export async function saveImage(id, dataUrl) {
  if (id == null || !dataUrl) return
  try {
    const db = await openDb()
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).put({ id, blob: dataUrlToBlob(dataUrl) })
      tx.oncomplete = resolve
      tx.onerror = () => reject(tx.error || new Error('保存图片失败'))
    })
  } catch (err) {
    console.warn('[imageStore] saveImage 失败', err)
  }
}

/** 读取识别图，返回 dataURL；无记录/异常返回 null。 */
export async function getImage(id) {
  if (id == null) return null
  try {
    const db = await openDb()
    const record = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const req = tx.objectStore(STORE_NAME).get(id)
      req.onsuccess = () => resolve(req.result || null)
      req.onerror = () => reject(req.error || new Error('读取图片失败'))
    })
    return record ? blobToDataUrl(record.blob) : null
  } catch (err) {
    console.warn('[imageStore] getImage 失败', err)
    return null
  }
}

/** 清空全部本地识别图（配合清空历史）。 */
export async function clearImages() {
  try {
    const db = await openDb()
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).clear()
      tx.oncomplete = resolve
      tx.onerror = () => reject(tx.error || new Error('清空图片失败'))
    })
  } catch (err) {
    console.warn('[imageStore] clearImages 失败', err)
  }
}

/** 删除单条识别图（配合删除单条历史）。 */
export async function removeImage(id) {
  if (id == null) return
  try {
    const db = await openDb()
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).delete(id)
      tx.oncomplete = resolve
      tx.onerror = () => reject(tx.error || new Error('删除图片失败'))
    })
  } catch (err) {
    console.warn('[imageStore] removeImage 失败', err)
  }
}
