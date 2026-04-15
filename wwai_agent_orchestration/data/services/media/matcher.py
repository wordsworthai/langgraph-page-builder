"""
MediaAssetMatcher with source-weighted scoring.

Scoring formula:
    final_score = source_weight × dimension_score

Where:
    - Google Maps photos: source_weight = 100
    - Stock/Generated: source_weight = 50
    - dimension_score = AR fit + size fit - orientation penalty (0-1)
"""
from typing import Optional, List, Tuple, Set, Dict
from wwai_agent_orchestration.data.services.models.media_asset import MediaAsset


# =============================================================================
# SOURCE WEIGHTS CONFIGURATION
# =============================================================================

class SourceBonus:
    """
    Additive bonus for source preference.
    
    Bonus is ADDED to dimension score, not multiplied.
    This ensures dimensions remain primary factor.
    """
    GOOGLE_MAPS_FULL = 0.15     # When dimension score >= 0.85
    GOOGLE_MAPS_PARTIAL = 0.08  # When dimension score >= 0.70
    STOCK = 0.0
    GENERATED = 0.0
    
    @classmethod
    def get(cls, source: str, dimension_score: float) -> float:
        """
        Get bonus for a source based on dimension quality.
        
        Tiered logic:
        - Excellent dims (>= 0.85): Full bonus
        - Good dims (>= 0.70): Partial bonus  
        - Fair/Poor dims (< 0.70): No bonus
        """
        if source != "google_maps":
            return 0.0
        
        if dimension_score >= 0.85:
            return cls.GOOGLE_MAPS_FULL
        elif dimension_score >= 0.70:
            return cls.GOOGLE_MAPS_PARTIAL
        else:
            return 0.0  # No bonus for poor fits


# =============================================================================
# HELPERS
# =============================================================================

def _is_svg_asset(asset: MediaAsset) -> bool:
    """Check if asset is SVG (excluded from raster matching)."""
    src_without_params = asset.src.split('?')[0].split('#')[0]
    return src_without_params.lower().endswith('.svg')


# =============================================================================
# MATCHER
# =============================================================================

class MediaAssetMatcher:
    """
    Media matching with source-weighted, dimension-aware scoring.
    
    Features:
    - Source weighting (Google Maps > Stock)
    - Aspect-ratio-first scoring with size fit
    - Strong anti-upscale penalty
    - Orientation mismatch penalty
    - Used asset tracking (no reuse)
    - Extreme fallback (always returns something if available)
    """
    
    def __init__(
        self,
        *,
        fallback_threshold: float = 0.60,
        ar_weight: float = 0.50,
        size_weight: float = 0.50,
        orientation_weight: float = 0.12,
        max_upscale_factor: float = 1.25,
        catastrophic_upscale_factor: float = 2.0,
        min_side_ratio: float = 0.85,
        prefer_higher_res_on_tie: bool = True,
        always_return: bool = True,
        allow_undimensioned_extreme_fallback: bool = True,
        use_source_weighting: bool = True,  # NEW
    ):
        self.fallback_threshold = fallback_threshold
        self.ar_weight = ar_weight
        self.size_weight = size_weight
        self.orientation_weight = orientation_weight
        self.max_upscale_factor = max_upscale_factor
        self.catastrophic_upscale_factor = catastrophic_upscale_factor
        self.min_side_ratio = min_side_ratio
        self.prefer_higher_res_on_tie = prefer_higher_res_on_tie
        self.always_return = always_return
        self.allow_undimensioned_extreme_fallback = allow_undimensioned_extreme_fallback
        self.use_source_weighting = use_source_weighting
        
        self.used_assets: Set[str] = set()
    
    # =========================================================================
    # ASSET TRACKING
    # =========================================================================
    
    def _identity_key(self, asset: MediaAsset) -> str:
        """Get unique identity key for deduplication."""
        return asset.meta.get("dedupe_key", asset.src)
    
    def reset_used_assets(self):
        """Clear used assets tracking."""
        self.used_assets.clear()
    
    def mark_as_used(self, asset: MediaAsset):
        """Mark asset as used."""
        self.used_assets.add(self._identity_key(asset))
    
    def is_available(self, asset: MediaAsset) -> bool:
        """Check if asset is available (not used)."""
        return self._identity_key(asset) not in self.used_assets
    
    # =========================================================================
    # SOURCE WEIGHTING (Tiered Additive Bonus)
    # =========================================================================
    
    def _get_source_bonus(self, asset: MediaAsset, dimension_score: float) -> float:
        """Get source bonus for an asset based on dimension quality."""
        source = asset.meta.get("source", "stock")
        return SourceBonus.get(source, dimension_score)
    
    def _weighted_score(
        self, 
        asset: MediaAsset, 
        req_w: int, 
        req_h: int
    ) -> float:
        """
        Calculate final score using tiered additive bonus.
        
        Algorithm:
        ┌────────────────────────────────────────────────────────┐
        │ dim >= 0.85 (Excellent) → dim + FULL bonus (0.15)      │
        │ dim >= 0.70 (Good)      → dim + PARTIAL bonus (0.08)   │
        │ dim >= 0.50 (Fair)      → dim only (no bonus)          │
        │ dim <  0.50 (Poor)      → dim × 0.5 (penalized)        │
        └────────────────────────────────────────────────────────┘
        
        Args:
            asset: MediaAsset to score
            req_w: Required width
            req_h: Required height
            
        Returns:
            Score in range [0, ~1.15] - dimension score + optional bonus
        """
        dimension_score = self._fit_score(asset.width, asset.height, req_w, req_h)
        
        if not self.use_source_weighting:
            return dimension_score
        
        # Tiered scoring logic
        if dimension_score >= 0.85:
            # Excellent fit: full source bonus
            bonus = self._get_source_bonus(asset, dimension_score)
            return dimension_score + bonus
        
        elif dimension_score >= 0.70:
            # Good fit: partial source bonus
            bonus = self._get_source_bonus(asset, dimension_score)
            return dimension_score + bonus
        
        elif dimension_score >= 0.50:
            # Fair fit: no bonus, pure dimension competition
            return dimension_score
        
        else:
            # Poor fit: penalize heavily (last resort)
            return dimension_score * 0.5
    
    def _get_weighted_threshold(self) -> float:
        """
        Get threshold for matching.
        
        With additive bonus, threshold stays in 0-1 range.
        """
        return self.fallback_threshold  # 0.60 default
    
    # =========================================================================
    # PUBLIC MATCHING METHODS
    # =========================================================================
    
    def find_best_image_matches(
        self,
        available_images: List[MediaAsset],
        required_dimensions: List[Tuple[int, int]]
    ) -> List[Optional[MediaAsset]]:
        """
        Find best image match for each required dimension.
        
        Args:
            available_images: Pool of available images
            required_dimensions: List of (width, height) tuples
            
        Returns:
            List of matched MediaAsset (None if no match found)
        """
        # Filter out SVGs and used assets
        pool = [
            a for a in available_images 
            if self.is_available(a) and not _is_svg_asset(a)
        ]
        
        results: List[Optional[MediaAsset]] = []
        threshold = self._get_weighted_threshold()
        
        for (req_w, req_h) in required_dimensions:
            available_pool = [a for a in pool if self.is_available(a)]
            
            # Try to find best fit above threshold
            match = self._find_best_fit(available_pool, req_w, req_h)
            
            if match:
                score = self._weighted_score(match, req_w, req_h)
                
                if score >= threshold:
                    # Good match found
                    self._annotate_match(match, "dimension_fit", score, req_w, req_h)
                    self.mark_as_used(match)
                    results.append(match)
                    continue
            
            # Fallback: return best available even if below threshold
            if self.always_return and available_pool:
                match = self._extreme_fallback(available_pool, req_w, req_h)
                if match:
                    self.mark_as_used(match)
                    results.append(match)
                    continue
            
            # No match found
            results.append(None)
        
        return results
    
    def find_top_image_matches(
        self,
        available_images: List[MediaAsset],
        required_dimensions: List[Tuple[int, int]],
        max_per_slot: int = 10
    ) -> List[List[MediaAsset]]:
        """
        Find top N image matches for each required dimension without marking as used.
        
        This method is used when we want multiple recommendations per slot (e.g., for UI display).
        Assets are NOT marked as used, allowing the caller (e.g., autopop mapper) to handle deduplication.
        
        Args:
            available_images: Pool of available images
            required_dimensions: List of (width, height) tuples
            max_per_slot: Maximum number of matches to return per slot
            
        Returns:
            List of lists, where each inner list contains top N MediaAsset matches for that slot
        """
        # Filter out SVGs (but not used assets - we don't mark as used here)
        pool = [
            a for a in available_images 
            if not _is_svg_asset(a)
        ]
        
        results: List[List[MediaAsset]] = []
        threshold = self._get_weighted_threshold()
        
        for (req_w, req_h) in required_dimensions:
            slot_matches: List[MediaAsset] = []
            seen_ids: Set[str] = set()  # Deduplicate within slot
            
            # Score all available assets for this slot
            scored_assets: List[Tuple[MediaAsset, float]] = []
            
            for asset in pool:
                if not asset.width or not asset.height:
                    continue
                
                # Skip if we've already seen this asset (dedup within slot)
                asset_id = self._identity_key(asset)
                if asset_id in seen_ids:
                    continue
                
                score = self._weighted_score(asset, req_w, req_h)
                scored_assets.append((asset, score))
            
            # Sort by score descending
            scored_assets.sort(key=lambda x: x[1], reverse=True)
            
            # Take top N matches
            for asset, score in scored_assets[:max_per_slot]:
                # Annotate match metadata
                self._annotate_match(asset, "dimension_fit" if score >= threshold else "extreme_fallback", score, req_w, req_h)
                slot_matches.append(asset)
                seen_ids.add(self._identity_key(asset))
            
            # If we don't have enough matches and always_return is True, add fallbacks
            if len(slot_matches) < max_per_slot and self.always_return:
                remaining_needed = max_per_slot - len(slot_matches)
                for asset in pool:
                    if len(slot_matches) >= max_per_slot:
                        break
                    
                    asset_id = self._identity_key(asset)
                    if asset_id in seen_ids:
                        continue
                    
                    # Only add if not already dimensioned (extreme fallback)
                    if not asset.width or not asset.height:
                        self._annotate_match(asset, "extreme_fallback", 0.0, req_w, req_h)
                        slot_matches.append(asset)
                        seen_ids.add(asset_id)
            
            results.append(slot_matches)
        
        return results
    
    def find_best_video_match(
        self,
        available_videos: List[MediaAsset],
        required_dimensions: Tuple[int, int]
    ) -> Optional[MediaAsset]:
        """
        Find best video match for required dimensions.
        
        Args:
            available_videos: Pool of available videos
            required_dimensions: (width, height) tuple
            
        Returns:
            Matched MediaAsset or None
        """
        req_w, req_h = required_dimensions
        pool = [v for v in available_videos if self.is_available(v)]
        
        if not pool:
            return None
        
        threshold = self._get_weighted_threshold()
        
        # Try to find best fit
        match = self._find_best_fit(pool, req_w, req_h)
        
        if match:
            score = self._weighted_score(match, req_w, req_h)
            
            if score >= threshold:
                self._annotate_match(match, "dimension_fit", score, req_w, req_h)
                self.mark_as_used(match)
                return match
        
        # Extreme fallback
        if self.always_return:
            match = self._extreme_fallback(pool, req_w, req_h)
            if match:
                self.mark_as_used(match)
                return match
        
        return None
    
    def find_top_video_matches(
        self,
        available_videos: List[MediaAsset],
        required_dimensions: List[Tuple[int, int]],
        max_per_slot: int = 10
    ) -> List[List[MediaAsset]]:
        """
        Find top N video matches for each required dimension without marking as used.
        
        This method is used when we want multiple recommendations per slot (e.g., for UI display).
        Assets are NOT marked as used, allowing the caller (e.g., autopop mapper) to handle deduplication.
        
        Args:
            available_videos: Pool of available videos
            required_dimensions: List of (width, height) tuples
            max_per_slot: Maximum number of matches to return per slot
            
        Returns:
            List of lists, where each inner list contains top N MediaAsset matches for that slot
        """
        # Filter available videos
        pool = [v for v in available_videos if self.is_available(v)]
        
        if not pool:
            return [[] for _ in required_dimensions]
        
        results: List[List[MediaAsset]] = []
        threshold = self._get_weighted_threshold()
        
        for (req_w, req_h) in required_dimensions:
            slot_matches: List[MediaAsset] = []
            seen_ids: Set[str] = set()  # Deduplicate within slot
            
            # Score all available assets for this slot
            scored_assets: List[Tuple[MediaAsset, float]] = []
            
            for asset in pool:
                if not asset.width or not asset.height:
                    continue
                
                # Skip if we've already seen this asset (dedup within slot)
                asset_id = self._identity_key(asset)
                if asset_id in seen_ids:
                    continue
                
                score = self._weighted_score(asset, req_w, req_h)
                scored_assets.append((asset, score))
            
            # Sort by score descending
            scored_assets.sort(key=lambda x: x[1], reverse=True)
            
            # Take top N matches
            for asset, score in scored_assets[:max_per_slot]:
                # Annotate match metadata
                self._annotate_match(asset, "dimension_fit" if score >= threshold else "extreme_fallback", score, req_w, req_h)
                slot_matches.append(asset)
                seen_ids.add(self._identity_key(asset))
            
            # If we don't have enough matches and always_return is True, add fallbacks
            if len(slot_matches) < max_per_slot and self.always_return:
                remaining_needed = max_per_slot - len(slot_matches)
                for asset in pool:
                    if len(slot_matches) >= max_per_slot:
                        break
                    
                    asset_id = self._identity_key(asset)
                    if asset_id in seen_ids:
                        continue
                    
                    # Only add if not already dimensioned (extreme fallback)
                    if not asset.width or not asset.height:
                        self._annotate_match(asset, "extreme_fallback", 0.0, req_w, req_h)
                        slot_matches.append(asset)
                        seen_ids.add(asset_id)
            
            results.append(slot_matches)
        
        return results
    
    # =========================================================================
    # INTERNAL MATCHING
    # =========================================================================
    
    def _find_best_fit(
        self, 
        assets: List[MediaAsset], 
        req_w: int, 
        req_h: int
    ) -> Optional[MediaAsset]:
        """Find best fit from pool using weighted scoring."""
        best: Optional[MediaAsset] = None
        best_score = -1.0
        
        for asset in assets:
            if not asset.width or not asset.height:
                continue
            
            # Use weighted score
            score = self._weighted_score(asset, req_w, req_h)
            
            if score > best_score:
                best, best_score = asset, score
            elif score == best_score and self.prefer_higher_res_on_tie and best:
                # Tie-breaker: prefer higher resolution
                if (asset.width * asset.height) > (best.width * best.height):
                    best = asset
        
        return best
    
    def _extreme_fallback(
        self, 
        assets: List[MediaAsset], 
        req_w: int, 
        req_h: int
    ) -> Optional[MediaAsset]:
        """Pick best available even if below threshold."""
        # Try dimensioned assets first
        best = self._find_best_fit(assets, req_w, req_h)
        
        if best:
            score = self._weighted_score(best, req_w, req_h)
            self._annotate_match(best, "extreme_fallback", score, req_w, req_h)
            return best
        
        # Last resort: undimensioned asset
        if self.allow_undimensioned_extreme_fallback:
            for asset in assets:
                if not asset.width or not asset.height:
                    self._annotate_match(asset, "extreme_fallback", 0.0, req_w, req_h)
                    return asset
        
        return None
    
    def _annotate_match(
        self, 
        asset: MediaAsset, 
        match_type: str, 
        score: float,
        req_w: int,
        req_h: int
    ):
        """Add match metadata to asset (mutates meta dict)."""
        source = asset.meta.get("source", "stock")
        dim_score = self._fit_score(asset.width, asset.height, req_w, req_h)
        bonus = self._get_source_bonus(asset, dim_score)
        
        # Determine quality tier
        if dim_score >= 0.85:
            quality_tier = "excellent"
        elif dim_score >= 0.70:
            quality_tier = "good"
        elif dim_score >= 0.50:
            quality_tier = "fair"
        else:
            quality_tier = "poor"
        
        asset.meta["match_type"] = match_type
        asset.meta["fit_score"] = round(score, 4)
        asset.meta["dimension_score"] = round(dim_score, 4)
        asset.meta["source_bonus"] = round(bonus, 4)
        asset.meta["quality_tier"] = quality_tier
        asset.meta["match_explanation"] = self._generate_explanation(
            asset, match_type, score, req_w, req_h
        )
        asset.meta["match_reason"] = self._generate_reason(
            asset, match_type, score, req_w, req_h
        )
    
    # =========================================================================
    # DIMENSION SCORING
    # =========================================================================
    
    def _fit_score(
        self, 
        w: Optional[int], 
        h: Optional[int], 
        req_w: int, 
        req_h: int
    ) -> float:
        """
        Calculate dimension-based fit score.
        
        Returns:
            Score in range [0, 1]
        """
        if not w or not h:
            return 0.0
        
        ar_fit = self._aspect_ratio_fit(w, h, req_w, req_h)
        size_fit = self._normalized_size_fit(w, h, req_w, req_h)
        penalty = self._orientation_penalty(w, h, req_w, req_h)
        
        score = (self.ar_weight * ar_fit + self.size_weight * size_fit) - penalty
        return max(0.0, min(1.0, score))
    
    def _aspect_ratio_fit(
        self, 
        w: int, 
        h: int, 
        req_w: int, 
        req_h: int
    ) -> float:
        """Calculate aspect ratio fit score."""
        ar = w / h
        req_ar = req_w / req_h
        rel_err = abs(ar - req_ar) / max(req_ar, 1e-6)
        return max(0.0, 1.0 - rel_err)
    
    def _normalized_size_fit(
        self, 
        w: int, 
        h: int, 
        req_w: int, 
        req_h: int
    ) -> float:
        """
        Calculate size fit score with anti-upscale penalty.
        
        Scale ranges:
        - ≤1.0 (downscale): 1.0
        - 1.0-1.25 (mild): 1.0 → 0.875
        - 1.25-1.5 (risky): 0.3 → 0.1
        - 1.5-2.0 (severe): 0.1 → 0.0
        - >2.0 (catastrophic): 0.0
        """
        scale_w = req_w / w
        scale_h = req_h / h
        scale = max(scale_w, scale_h)
        
        if scale > self.catastrophic_upscale_factor:
            return 0.0
        if scale > 1.5:
            return max(0.0, 0.1 - (scale - 1.5) * 0.2)
        if scale > self.max_upscale_factor:
            return max(0.0, 0.3 - (scale - self.max_upscale_factor) * 0.8)
        if scale > 1.0:
            return max(0.0, 1.0 - (scale - 1.0) * 0.5)
        
        return 1.0
    
    def _orientation_penalty(
        self, 
        w: int, 
        h: int, 
        req_w: int, 
        req_h: int
    ) -> float:
        """Calculate orientation mismatch penalty."""
        def ori(a_w, a_h):
            if a_w == a_h:
                return "square"
            return "landscape" if a_w > a_h else "portrait"
        
        o1 = ori(w, h)
        o2 = ori(req_w, req_h)
        
        if o1 == "square" or o2 == "square":
            return 0.0
        
        return self.orientation_weight if o1 != o2 else 0.0
    
    # =========================================================================
    # EXPLANATION GENERATION
    # =========================================================================
    
    def _generate_explanation(
        self, 
        asset: MediaAsset, 
        match_type: str, 
        score: float,
        req_w: int,
        req_h: int
    ) -> str:
        """Generate human-readable match explanation."""
        explanations = []
        source = asset.meta.get("source", "stock")
        dim_score = self._fit_score(asset.width, asset.height, req_w, req_h)
        bonus = self._get_source_bonus(asset, dim_score)
        
        # Quality tier
        if dim_score >= 0.85:
            tier = "EXCELLENT"
        elif dim_score >= 0.70:
            tier = "GOOD"
        elif dim_score >= 0.50:
            tier = "FAIR"
        else:
            tier = "POOR"
        
        # Source info with bonus
        if bonus > 0:
            explanations.append(f"Source: {source} (+{bonus:.2f} bonus, tier={tier})")
        else:
            explanations.append(f"Source: {source} (no bonus, tier={tier})")
        
        # Match type explanation
        if match_type == "dimension_fit":
            explanations.append("Good dimensional match found")
        elif match_type == "extreme_fallback":
            explanations.append("Emergency fallback: no asset met quality threshold")
        
        # Dimensional explanation
        if asset.width and asset.height:
            ar = asset.width / asset.height
            req_ar = req_w / req_h
            
            explanations.append(
                f"Dimensions: {asset.width}×{asset.height} (AR={ar:.2f}) "
                f"vs required {req_w}×{req_h} (AR={req_ar:.2f})"
            )
            
            # Upscale/downscale info
            scale_w = req_w / asset.width
            scale_h = req_h / asset.height
            scale = max(scale_w, scale_h)
            
            if scale > 1.0:
                if scale > self.max_upscale_factor:
                    explanations.append(
                        f"⚠️ Requires {scale:.1f}x upscale (risky - may be blurry)"
                    )
                else:
                    explanations.append(f"Requires {scale:.1f}x upscale")
            else:
                explanations.append(f"Downscale by {1/scale:.1f}x (safe)")
            
            # Orientation info
            asset_ori = asset.orientation()
            req_ori = "square" if req_w == req_h else (
                "landscape" if req_w > req_h else "portrait"
            )
            
            if asset_ori != req_ori and asset_ori != "square" and req_ori != "square":
                explanations.append(
                    f"⚠️ Orientation mismatch: {asset_ori} vs {req_ori}"
                )
            else:
                explanations.append(f"Orientation: {asset_ori} ✓")
            
            # Score breakdown
            explanations.append(
                f"Dim score: {dim_score:.3f} + Bonus: {bonus:.2f} = Final: {score:.3f}"
            )
        else:
            explanations.append("⚠️ No dimension data available")
        
        return " | ".join(explanations)

    def _generate_reason(
        self,
        asset: MediaAsset,
        match_type: str,
        score: float,
        req_w: int,
        req_h: int
    ) -> str:
        """Generate concise, URL-safe reason code."""
        reason_parts = []
        source = asset.meta.get("source", "stock")
        dim_score = self._fit_score(asset.width, asset.height, req_w, req_h)
        
        # Source
        reason_parts.append(f"src_{source}")
        
        # Quality tier
        if dim_score >= 0.85:
            reason_parts.append("tier_excellent")
        elif dim_score >= 0.70:
            reason_parts.append("tier_good")
        elif dim_score >= 0.50:
            reason_parts.append("tier_fair")
        else:
            reason_parts.append("tier_poor")
        
        # Match type (abbreviated)
        if match_type == "dimension_fit":
            reason_parts.append("good_match")
        elif match_type == "extreme_fallback":
            reason_parts.append("emergency_fallback")
        
        # Dimensional info
        if asset.width and asset.height:
            reason_parts.append(f"asset_{asset.width}x{asset.height}")
            reason_parts.append(f"req_{req_w}x{req_h}")
            
            # Upscale/downscale info
            scale_w = req_w / asset.width
            scale_h = req_h / asset.height
            scale = max(scale_w, scale_h)
            
            if scale > self.catastrophic_upscale_factor:
                reason_parts.append("catastrophic_upscale")
            elif scale > 1.5:
                reason_parts.append("severe_upscale")
            elif scale > self.max_upscale_factor:
                reason_parts.append("risky_upscale")
            elif scale > 1.0:
                reason_parts.append("upscale")
            else:
                reason_parts.append("downscale")
            
            # Orientation match
            asset_ori = asset.orientation()
            req_ori = "square" if req_w == req_h else (
                "landscape" if req_w > req_h else "portrait"
            )
            
            if asset_ori != req_ori and asset_ori != "square" and req_ori != "square":
                reason_parts.append("wrong_orientation")
            else:
                reason_parts.append("correct_orientation")
        else:
            reason_parts.append("no_dims")
            reason_parts.append(f"req_{req_w}x{req_h}")
        
        return "_".join(reason_parts)