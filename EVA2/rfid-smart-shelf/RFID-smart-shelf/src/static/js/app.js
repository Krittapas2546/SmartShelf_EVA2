/**
 * app.js - Main Application Entry Point
 * ไฟล์หลักที่รวมทุกอย่างเข้าด้วยกัน และจัดการ DOMContentLoaded
 */

/**
 * ===================
 * APPLICATION INITIALIZATION
 * ===================
 */

/**
 * WebSocket Message Handler
 */
function handleWebSocketMessage(data) {
    console.log('📨 WebSocket message received:', data);
    
    try {
        switch (data.type) {
            case 'job_completed':
                console.log('✅ Job completed notification from WebSocket');
                if (data.job_data) {
                    ShelfNotifications.showNotification(
                        `งาน ${data.job_data.lot_no} เสร็จสิ้นแล้ว`,
                        'success'
                    );
                }
                
                // รีเฟรช UI และ state
                ShelfServices.refreshShelfStateFromServer().then(() => {
                    ShelfQueue.renderAll();
                });
                break;
                
            case 'shelf_state_updated':
                console.log('🔄 Shelf state updated notification from WebSocket');
                if (data.shelf_state) {
                    ShelfState.setShelfState(data.shelf_state);
                    ShelfUI.renderShelfGrid();
                }
                break;
                
            case 'queue_updated':
                console.log('📋 Queue updated notification from WebSocket');
                if (Array.isArray(data.queue)) {
                    ShelfState.setQueue(data.queue);
                    ShelfQueue.renderAll();
                }
                break;
                
            case 'error':
                console.error('❌ WebSocket error:', data.message);
                ShelfNotifications.showNotification(
                    `เกิดข้อผิดพลาด: ${data.message}`,
                    'error'
                );
                break;
                
            case 'lms_response':
                console.log('📋 LMS response from WebSocket:', data);
                if (data.lms_data) {
                    ShelfNotifications.showLMSNotification(data.lms_data);
                }
                break;
                
            default:
                console.log('📨 Unknown WebSocket message type:', data.type);
        }
    } catch (error) {
        console.error('❌ Error handling WebSocket message:', error);
    }
}

/**
 * Initialize application
 */
async function initializeApplication() {
    console.log('📄 DOM Content Loaded - เริ่มต้นระบบ');
    
    try {
        // 1. ดึงข้อมูล shelf name และ ID ก่อน
        console.log('🏷️ Step 1: Initialize shelf name and ID');
        await ShelfServices.initializeShelfName();
        
        // 2. โหลดการกำหนดค่า shelf
        console.log('⚙️ Step 2: Load shelf configuration');
        const configLoaded = await ShelfServices.loadShelfConfig();
        
        if (!configLoaded) {
            console.warn('⚠️ Using fallback configuration');
        }
        
        // 3. สร้าง shelf grid structure
        console.log('🏗️ Step 3: Create shelf grid structure');
        const shelfGrid = document.getElementById('shelfGrid');
        if (shelfGrid) {
            ShelfUI.createShelfGridStructure();
        }
        
        // 4. เริ่มต้น shelf state
        console.log('📊 Step 4: Initialize shelf state');
        ShelfState.initializeShelfState();
        
        // 5. โหลดงานที่ค้างอยู่จาก Gateway
        console.log('📋 Step 5: Load pending jobs');
        await ShelfServices.loadPendingJobsFromGateway();
        
        // 6. ซิงค์คิวจาก backend
        console.log('🔄 Step 6: Sync queue from backend');
        await ShelfServices.syncQueueFromBackend();
        
        // 7. รีเฟรช shelf state จาก server
        console.log('📦 Step 7: Restore shelf state from server');
        await ShelfServices.refreshShelfStateFromServer();
        
        // 8. ตั้งค่า WebSocket
        console.log('🔌 Step 8: Setup WebSocket connection');
        ShelfServices.setupWebSocket(handleWebSocketMessage);
        
        // 9. ตั้งค่า event listeners
        console.log('👂 Step 9: Setup event listeners');
        setupEventListeners();
        
        // 10. แสดงผล UI ครั้งแรก
        console.log('🎨 Step 10: Initial render');
        ShelfQueue.renderAll();
        
        console.log('✅ Application initialized successfully');
        
    } catch (error) {
        console.error('❌ Failed to initialize application:', error);
        ShelfNotifications.showNotification(
            'เกิดข้อผิดพลาดในการเริ่มต้นระบบ',
            'error'
        );
    }
}

/**
 * Setup Event Listeners
 */
function setupEventListeners() {
    // Window resize handler
    window.addEventListener('resize', () => {
        ShelfUI.updateCellSizes();
    });
    
    // Shelf grid mode observer
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                ShelfUI.updateCellSizes();
            }
        });
    });
    
    // เฝ้าดู main-container สำหรับการเปลี่ยนแปลง class
    const mainContainerElement = document.querySelector('.main-container');
    if (mainContainerElement) {
        observer.observe(mainContainerElement, { 
            attributes: true, 
            attributeFilter: ['class'] 
        });
    }
    
    // Setup keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape key to go back
        if (e.key === 'Escape') {
            const activeJob = ShelfState.getActiveJob();
            if (activeJob) {
                ShelfQueue.goBackToQueue();
            } else {
                const uiState = ShelfState.getUIState();
                if (!uiState.showMainWithQueue) {
                    ShelfQueue.goBackToMain();
                }
            }
        }
        
        // F5 to refresh (prevent default and do custom refresh)
        if (e.key === 'F5') {
            e.preventDefault();
            console.log('🔄 Manual refresh triggered');
            refreshApplication();
        }
    });
    
    // Setup LOT input handler
    const lotInput = document.getElementById('lot-no-input');
    if (lotInput) {
        lotInput.addEventListener('keyup', (e) => {
            if (e.key === 'Enter') {
                ShelfQueue.handleLotSearch();
            }
        });
    }
    
    console.log('👂 Event listeners setup complete');
}

/**
 * Manual Application Refresh
 */
async function refreshApplication() {
    try {
        console.log('🔄 Refreshing application...');
        
        // Refresh shelf state
        await ShelfServices.refreshShelfStateFromServer();
        
        // Sync queue
        await ShelfServices.syncQueueFromBackend();
        
        // Re-render everything
        ShelfQueue.renderAll();
        
        ShelfNotifications.showNotification('ระบบรีเฟรชเสร็จสิ้น', 'success');
        console.log('✅ Application refresh complete');
        
    } catch (error) {
        console.error('❌ Failed to refresh application:', error);
        ShelfNotifications.showNotification('เกิดข้อผิดพลาดในการรีเฟรช', 'error');
    }
}

/**
 * ===================
 * UTILITY FUNCTIONS (For Console Access)
 * ===================
 */

/**
 * Console utilities for debugging
 */
function setupConsoleUtilities() {
    // Expose utility functions to console for debugging
    window.ShelfDebug = {
        // State inspection
        getState: () => ({
            config: ShelfState.getShelfConfig(),
            totalLevels: ShelfState.getTotalLevels(),
            maxBlocks: ShelfState.getMaxBlocks(),
            capacities: ShelfState.getCellCapacities(),
            shelfId: ShelfState.getShelfId(),
            uiState: ShelfState.getUIState(),
            activeJob: ShelfState.getActiveJob(),
            queue: ShelfState.getQueue(),
            shelfState: ShelfState.getShelfState()
        }),
        
        // Manual actions
        refresh: refreshApplication,
        clearQueue: () => {
            ShelfState.setQueue([]);
            ShelfQueue.renderAll();
            console.log('🧹 Queue cleared');
        },
        clearActiveJob: () => {
            ShelfState.removeActiveJob();
            ShelfQueue.renderAll();
            console.log('🧹 Active job cleared');
        },
        clearLED: () => {
            ShelfServices.clearLED();
            console.log('💡 LEDs cleared');
        },
        
        // Service calls
        loadPendingJobs: ShelfServices.loadPendingJobsFromGateway,
        syncQueue: ShelfServices.syncQueueFromBackend,
        initShelfName: ShelfServices.initializeShelfName,
        loadLayout: ShelfServices.loadLayoutFromGateway,
        
        // Reset flags
        resetPendingJobsFlag: () => {
            ShelfState.setPendingJobsLoaded(false);
            console.log('🔄 Reset pending jobs flag');
        },
        
        // Force refresh grid
        refreshGrid: ShelfUI.refreshShelfGrid
    };
    
    console.log('🔧 Debug utilities available at window.ShelfDebug');
}

/**
 * ===================
 * APPLICATION ENTRY POINT
 * ===================
 */

// Main entry point
document.addEventListener('DOMContentLoaded', async () => {
    // Setup console utilities first
    setupConsoleUtilities();
    
    // Initialize the application
    await initializeApplication();
});

/**
 * ===================
 * GLOBAL ERROR HANDLER
 * ===================
 */

// Global error handler
window.addEventListener('error', (event) => {
    console.error('🚨 Global error:', event.error);
    ShelfNotifications.showNotification(
        'เกิดข้อผิดพลาดในระบบ กรุณาลองใหม่อีกครั้ง',
        'error'
    );
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
    console.error('🚨 Unhandled promise rejection:', event.reason);
    ShelfNotifications.showNotification(
        'เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้ง',
        'error'
    );
});

/**
 * ===================
 * EXPORT APP MODULE
 * ===================
 */

if (typeof window !== 'undefined') {
    window.ShelfApp = {
        initialize: initializeApplication,
        refresh: refreshApplication,
        handleWebSocketMessage,
        setupEventListeners,
        setupConsoleUtilities
    };
}

console.log('📱 Smart Shelf Application loaded');