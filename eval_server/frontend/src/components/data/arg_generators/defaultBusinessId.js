import { pickRandomBusinessId } from './constants'

export default function applyDefaultBusinessId(sampleArgs = {}) {
  const cloned = JSON.parse(JSON.stringify(sampleArgs || {}))
  if (!Object.prototype.hasOwnProperty.call(cloned, 'business_id')) {
    return cloned
  }
  cloned.business_id = pickRandomBusinessId()
  return cloned
}

