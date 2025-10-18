/**
 * utils.js - Pure Helper Functions
 * ฟังก์ชันช่วยเหลือที่ไม่ขึ้นอยู่กับ DOM หรือ I/O operations
 */

/**
 * ตรวจสอบว่า LOT number มีรูปแบบที่ถูกต้องหรือไม่
 * รูปแบบใหม่: Alphanumeric 12 ตัว (xxxxxxxxx.xx)
 * - 9 ตัวอักษร/ตัวเลข + จุด + 2 ตัวเลข
 * - ตัวอย่าง: ABC123DEF.01, Y540C02AS.01, 123456789.99
 * @param {string} lotNo - หมายเลข LOT ที่ต้องตรวจสอบ
 * @returns {boolean} - true ถ้ารูปแบบถูกต้อง
 */
function isValidLotNumberFormat(lotNo) {
    if (!lotNo || typeof lotNo !== 'string') {
        return false;
    }
    
    const trimmedLot = lotNo.trim();
    
    // รูปแบบหลัก: Alphanumeric 12 ตัว (xxxxxxxxx.xx)
    // 9 ตัวอักษร/ตัวเลข + จุด + 2 ตัวเลข
    // ตัวอย่าง: ABC123DEF.01, Y540C02AS.01, 123456789.99
    const mainPattern = /^[A-Za-z0-9]{9}\.\d{2}$/;
    
    console.log(`🔍 Validating LOT format: "${trimmedLot}" against pattern: ${mainPattern}`);
    const isValid = mainPattern.test(trimmedLot);
    console.log(`✅ LOT validation result: ${isValid} (Expected format: xxxxxxxxx.xx)`);
    
    return isValid;
}

/**
 * แยกข้อมูลตำแหน่งจากบาร์โค้ด
 * รูปแบบที่รองรับ: L1-B2, 1-2, L1B2, 1,2 เป็นต้น
 * @param {string} barcode - บาร์โค้ดที่ต้องการแยกข้อมูล
 * @returns {Object|null} - {level, block} หรือ null ถ้าไม่ตรงรูปแบบ
 */
function parseLocationFromBarcode(barcode) {
    // ลบช่องว่างและแปลงเป็นตัวพิมพ์ใหญ่
    const cleaned = barcode.replace(/\s+/g, '').toUpperCase();
    
    // รูปแบบต่างๆ ที่รองรับ
    const patterns = [
        /^L(\d+)-?B(\d+)$/,  // L1-B2 หรือ L1B2
        /^(\d+)-(\d+)$/,     // 1-2
        /^(\d+),(\d+)$/,     // 1,2
        /^(\d+)_(\d+)$/,     // 1_2
        /^L(\d+)B(\d+)$/     // L1B2
    ];

    for (const pattern of patterns) {
        const match = cleaned.match(pattern);
        if (match) {
            return {
                level: parseInt(match[1], 10),
                block: parseInt(match[2], 10)
            };
        }
    }

    return null;
}

// Export functions for module usage
if (typeof window !== 'undefined') {
    // Browser environment
    window.ShelfUtils = {
        isValidLotNumberFormat,
        parseLocationFromBarcode
    };
}

// For CommonJS/Node.js environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        isValidLotNumberFormat,
        parseLocationFromBarcode
    };
}