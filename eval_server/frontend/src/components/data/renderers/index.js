import React from 'react'
import SectionCatalogAllResult from './sectionCatalogAll'
import SectionL0CategoriesResult from './sectionL0Categories'
import TradeClassificationResult from './tradeClassification'
import TradesCatalogResult from './tradesCatalog'
import BusinessPhotosResult from './businessPhotos'
import BusinessProfileResult from './businessProfile'
import LogosResult from './logos'
import ReviewsResult from './reviews'
import MediaAssetsResult from './mediaAssets'
import ReviewPhotosResult from './reviewPhotos'
import MediaMatchImagesResult from './mediaMatchImages'
import MediaMatchVideosResult from './mediaMatchVideos'

const RESULT_RENDERERS = {
  sectionCatalogAll: SectionCatalogAllResult,
  sectionL0Categories: SectionL0CategoriesResult,
  tradeClassification: TradeClassificationResult,
  tradesCatalog: TradesCatalogResult,
  businessPhotos: BusinessPhotosResult,
  businessProfile: BusinessProfileResult,
  logos: LogosResult,
  reviews: ReviewsResult,
  mediaAssets: MediaAssetsResult,
  reviewPhotos: ReviewPhotosResult,
  mediaMatchImages: MediaMatchImagesResult,
  mediaMatchVideos: MediaMatchVideosResult,
}

export function renderDataDebugResult({ target, result }) {
  const key = target?.result_renderer
  if (!key) return null
  const Renderer = RESULT_RENDERERS[key]
  if (!Renderer) return null
  return React.createElement(Renderer, { result, target })
}

