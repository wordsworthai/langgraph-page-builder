import generateMediaImageSlots from './mediaImageSlots'
import applyDefaultBusinessId from './defaultBusinessId'

const ARG_GENERATORS = {
  mediaImageSlots: generateMediaImageSlots,
}

export function generateDataDebugArgs({ target, sampleArgs }) {
  const key = target?.random_args_generator
  if (!key) return applyDefaultBusinessId(sampleArgs || {})
  const generator = ARG_GENERATORS[key]
  if (!generator) return applyDefaultBusinessId(sampleArgs || {})
  return generator(sampleArgs || {})
}

