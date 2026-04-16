// ---- WWAI: Parent-side mock dynamic fetch function (available in DevTools) ----
declare global {
    interface Window {
        _WWAI_DYNAMIC_PRODUCT_DATA_FETCH_FUNCTION?: (handle: string) => any;
    }
}

// Export to make this a module (required for global augmentation)
export {};
  
if (typeof window !== "undefined" && !window._WWAI_DYNAMIC_PRODUCT_DATA_FETCH_FUNCTION) {
    window._WWAI_DYNAMIC_PRODUCT_DATA_FETCH_FUNCTION = async function (handle: string) {
        return {
            handle,
            title: `Mock Product for ${handle}`,
            variants: [{ id: `${handle}-variant-1`, title: "Default Variant", available: true }],
            selling_plan_groups: [],
            images: [],
            description: `Mock product.`,
            vendor: "MockVendor",
            product_type: "MockType",
        };

        
        try {
        console.log(`[API] Fetching product data for: ${handle}`);
        
        const response = await fetch('https://YOUR_BACKEND_URL/api/products/', {
            method: 'POST',
            headers: {
            'Content-Type': 'application/json',
            },
            body: JSON.stringify({
            shopUrl: 'your-store.myshopify.com',
            productHandles: [handle]
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Extract the product data for the specific handle
        const productData = data[handle];
        
        if (!productData) {
            console.warn(`No product data found for handle: ${handle}`);
            return null;
        }
        
        return productData;
        
        } catch (error) {
        console.error('Error fetching product data:', error);
        
        // Fallback to mock data if API fails
        return {
            handle,
            title: `Mock Product for ${handle}`,
            variants: [{ id: `${handle}-variant-1`, title: "Default Variant", available: true }],
            selling_plan_groups: [],
            images: [],
            description: `Mock product.`,
            vendor: "MockVendor",
            product_type: "MockType",
        };
        }
    };
}