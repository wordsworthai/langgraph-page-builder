// Common CSS and JS imports for HTML preview
// This file exports reusable HTML strings and configurations

// Font preload links
export const FONT_PRELOADS = `
<link rel="preload" href="https://cdn.shopify.com/s/files/1/0809/9538/5662/files/NeueHaasUnicaPro-UltraLight.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="https://cdn.shopify.com/s/files/1/0809/9538/5662/files/NeueHaasUnicaPro-Light.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="https://cdn.shopify.com/s/files/1/0809/9538/5662/files/NeueHaasUnicaPro-Regular.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="https://cdn.shopify.com/s/files/1/0809/9538/5662/files/NeueHaasUnicaPro-Medium.woff2" as="font" type="font/woff2" crossorigin="">
<link rel="preload" href="https://cdn.shopify.com/s/files/1/0809/9538/5662/files/NeueHaasUnicaPro-Bold.woff2" as="font" type="font/woff2" crossorigin="">
`;

// CSS stylesheets
export const CSS_LINKS = `
<link rel="stylesheet" href="https://curation-frontend-wwai.s3.ap-south-1.amazonaws.com/wwai_section_assets/a6f452b4e8377dad0ab352fa24629597a5276d0c0fd454be314aee545790408c_20250922_123225/output.css" type="text/css">
<link rel="stylesheet" href="https://curation-frontend-wwai.s3.ap-south-1.amazonaws.com/wwai_section_assets/a6f452b4e8377dad0ab352fa24629597a5276d0c0fd454be314aee545790408c_20250922_123225/wwai_base_style.css" type="text/css">
<link rel="stylesheet" href="https://curation-frontend-wwai.s3.ap-south-1.amazonaws.com/wwai_section_assets/a6f452b4e8377dad0ab352fa24629597a5276d0c0fd454be314aee545790408c_20250922_123225/wwai-video-player.css" type="text/css">
<link rel="stylesheet" href="https://curation-frontend-wwai.s3.ap-south-1.amazonaws.com/wwai_section_assets/a6f452b4e8377dad0ab352fa24629597a5276d0c0fd454be314aee545790408c_20250922_123225/swiper-bundle.min.css" type="text/css">
`;

// JavaScript files
export const JS_SCRIPTS = `
<script src="https://curation-frontend-wwai.s3.ap-south-1.amazonaws.com/wwai_section_assets/a6f452b4e8377dad0ab352fa24629597a5276d0c0fd454be314aee545790408c_20250922_123225/swiper-bundle.min.js" defer=""></script>
<script src="https://curation-frontend-wwai.s3.ap-south-1.amazonaws.com/wwai_section_assets/a6f452b4e8377dad0ab352fa24629597a5276d0c0fd454be314aee545790408c_20250922_123225/wwai-fast-video-player.js" defer=""></script>
`;

// Complete head section combining all imports
export const COMPLETE_HEAD_IMPORTS = `
${FONT_PRELOADS}
${CSS_LINKS}
${JS_SCRIPTS}
`;