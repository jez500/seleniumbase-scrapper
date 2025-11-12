// Example user script to remove common ad elements
// This script removes elements with common ad-related class names and IDs

(function() {
    console.log('Running example-remove-ads.js user script');
    
    // Common ad selectors
    const adSelectors = [
        '.advertisement',
        '.ad-container',
        '.ads',
        '#ad',
        '.google-ad',
        '[class*="advertisement"]',
        '[id*="advertisement"]',
        '.banner-ad',
        '.sponsored'
    ];
    
    let removedCount = 0;
    adSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.remove();
            removedCount++;
        });
    });
    
    console.log(`Removed ${removedCount} ad elements`);
})();
