import { pickRandomBusinessId } from './constants'

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function randomFrom(values) {
  return values[randInt(0, values.length - 1)]
}

function buildRandomSlot(index) {
  const presetSizes = [
    [1200, 800],
    [1440, 900],
    [1280, 720],
    [1080, 1080],
    [1600, 900],
  ]
  const [width, height] = randomFrom(presetSizes)
  const blockTypes = ['hero', 'gallery', 'feature', 'testimonial', 'service']
  const blockType = randomFrom(blockTypes)

  return {
    width,
    height,
    slot_identity: {
      element_id: `${blockType}_image_${index + 1}`,
      block_type: blockType,
      block_index: index,
      section_id: `section_${index + 1}`,
    },
  }
}

export default function generateMediaImageSlots(sampleArgs = {}) {
  const slotCount = randInt(1, 5)
  const slots = Array.from({ length: slotCount }, (_, idx) => buildRandomSlot(idx))

  return {
    business_id: pickRandomBusinessId(),
    slots,
    retrieval_sources: sampleArgs.retrieval_sources || ['generated'],
    max_recommendations_per_slot: sampleArgs.max_recommendations_per_slot || 1,
  }
}

