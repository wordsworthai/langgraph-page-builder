export const BUSINESS_ID_POOL = [
  '660097b0-03df-42b5-b68e-5ccf18193b26',
  '47b28fbd-4d6b-4ba7-b8bf-c46cdb08471b',
  '32ca8b8b-be55-4825-aae3-e9ba549ec255',
]

export function pickRandomBusinessId() {
  if (!BUSINESS_ID_POOL.length) return ''
  const idx = Math.floor(Math.random() * BUSINESS_ID_POOL.length)
  return BUSINESS_ID_POOL[idx]
}

