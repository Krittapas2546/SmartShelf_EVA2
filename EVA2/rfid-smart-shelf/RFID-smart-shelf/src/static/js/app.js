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
            case 'initial_state':
                console.log('🎯 Initial state from WebSocket');
                if (data.payload && data.payload.shelf_state) {
                    ShelfState.setShelfState(data.payload.shelf_state);
                    ShelfUI.renderShelfGrid();
                }
                break;
                
            case 'new_job':
                console.log('📋 New job from WebSocket');
                if (data.payload) {
                    ShelfState.addToQueue(data.payload);
                    ShelfQueue.renderAll();
                    ShelfNotifications.showNotification(
                        `งานใหม่: ${data.payload.lot_no}`,
                        'info'
                    );
                }
                break;
                
            case 'jobs_reloaded':
                console.log('🔄 Jobs reloaded from WebSocket');
                // Re-sync queue from backend
                ShelfServices.syncQueueFromBackend().then(() => {
                    ShelfQueue.renderAll();
                    ShelfNotifications.showNotification('คิวงานได้รับการอัปเดต', 'info');
                });
                break;
                
            case 'job_completed':
                console.log('✅ Job completed notification from WebSocket');
                const payload = data.payload || data;
                
                // เคลียร์ active job
                ShelfState.removeActiveJob();
                
                // ลบงานจาก queue
                if (payload.completedJobId) {
                    ShelfState.removeFromQueue(payload.completedJobId);
                }
                
                // อัปเดต shelf state
                if (payload.shelf_state) {
                    ShelfState.setShelfState(payload.shelf_state);
                }
                
                // เคลียร์ LED
                ShelfServices.clearLED();
                
                // แสดง notification
                if (payload.lot_no) {
                    ShelfNotifications.showNotification(
                        `งาน ${payload.lot_no} เสร็จสิ้นแล้ว`,
                        'success'
                    );
                }
                
                // รีเฟรช UI
                ShelfQueue.renderAll();
                break;
                
            case 'job_warning':
                console.log('⚠️ Job warning from WebSocket');
                if (data.payload && data.payload.message) {
                    ShelfNotifications.showNotification(
                        `คำเตือน: ${data.payload.message}`,
                        'warning'
                    );
                }
                break;
                
            case 'job_error':
                console.log('❌ Job error from WebSocket');
                if (data.payload && data.payload.message) {
                    ShelfNotifications.showNotification(
                        `ข้อผิดพลาด: ${data.payload.message}`,
                        'error'
                    );
                }
                break;
                
            case 'job_canceled':
                console.log('🚫 Job canceled from WebSocket');
                if (data.payload) {
                    // ลบงานจาก queue
                    if (data.payload.lot_no) {
                        const queue = ShelfState.getQueue();
                        const filteredQueue = queue.filter(job => job.lot_no !== data.payload.lot_no);
                        ShelfState.setQueue(filteredQueue);
                    }
                    
                    // เคลียร์ active job ถ้าตรงกัน
                    const activeJob = ShelfState.getActiveJob();
                    if (activeJob && activeJob.lot_no === data.payload.lot_no) {
                        ShelfState.removeActiveJob();
                    }
                    
                    ShelfQueue.renderAll();
                    ShelfNotifications.showNotification(
                        `งาน ${data.payload.lot_no} ถูกยกเลิก`,
                        'warning'
                    );
                }
                break;
                
            case 'system_reset':
                console.log('🔄 System reset from WebSocket');
                // เคลียร์ทุกอย่าง
                ShelfState.setQueue([]);
                ShelfState.removeActiveJob();
                ShelfState.initializeShelfState();
                ShelfServices.clearLED();
                ShelfQueue.renderAll();
                ShelfNotifications.showNotification('ระบบถูกรีเซ็ต', 'info');
                break;
                
            case 'shelf_state_updated':
                console.log('🔄 Shelf state updated notification from WebSocket');
                if (data.shelf_state || (data.payload && data.payload.shelf_state)) {
                    const shelfState = data.shelf_state || data.payload.shelf_state;
                    ShelfState.setShelfState(shelfState);
                    ShelfUI.renderShelfGrid();
                }
                break;
                
            case 'queue_updated':
                console.log('📋 Queue updated notification from WebSocket');
                const queueData = data.queue || (data.payload && data.payload.queue);
                if (Array.isArray(queueData)) {
                    ShelfState.setQueue(queueData);
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
 * Hydrate application state from localStorage
 */
function hydrateFromLocalStorage() {
    try {
        // กู้คืน queue จาก localStorage
        const storedQueue = localStorage.getItem(ShelfState.QUEUE_KEY);
        if (storedQueue) {
            const queue = JSON.parse(storedQueue);
            if (Array.isArray(queue)) {
                ShelfState.setQueue(queue);
                console.log(`💾 Restored ${queue.length} jobs from localStorage`);
            }
        }
        
        // กู้คืน active job จาก localStorage
        const storedActiveJob = localStorage.getItem(ShelfState.ACTIVE_JOB_KEY);
        if (storedActiveJob && storedActiveJob !== 'null') {
            const activeJob = JSON.parse(storedActiveJob);
            if (activeJob && activeJob.lot_no) {
                ShelfState.setActiveJob(activeJob);
                console.log(`💾 Restored active job: ${activeJob.lot_no}`);
            }
        }
        
        // กู้คืน shelf state จาก localStorage
        const storedShelfState = localStorage.getItem(ShelfState.GLOBAL_SHELF_STATE_KEY);
        if (storedShelfState) {
            const shelfState = JSON.parse(storedShelfState);
            if (Array.isArray(shelfState)) {
                ShelfState.setShelfState(shelfState);
                console.log(`💾 Restored shelf state with ${shelfState.length} cells`);
            }
        }
        
        console.log('💾 localStorage hydration complete');
        
    } catch (error) {
        console.error('❌ Error hydrating from localStorage:', error);
        // ไม่ throw error เพื่อให้แอปยังทำงานได้
    }
}

/**
 * Initialize application
 */
async function initializeApplication() {
    console.log('📄 DOM Content Loaded - เริ่มต้นระบบ');
    
    try {
        // 0. Hydrate จาก localStorage ก่อนอื่น
        console.log('💾 Step 0: Hydrate from localStorage');
        hydrateFromLocalStorage();
        
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
            debouncedRefresh();
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
 * Debounced refresh to prevent multiple rapid refreshes
 */
let refreshTimeout = null;
let isRefreshing = false;

function debouncedRefresh() {
    if (isRefreshing) {
        console.log('🔄 Refresh already in progress, skipping...');
        return;
    }
    
    if (refreshTimeout) {
        clearTimeout(refreshTimeout);
    }
    
    refreshTimeout = setTimeout(() => {
        refreshApplication();
        refreshTimeout = null;
    }, 300); // 300ms debounce
}

/**
 * Manual Application Refresh
 */
async function refreshApplication() {
    if (isRefreshing) {
        console.log('🔄 Refresh already in progress, aborting...');
        return;
    }
    
    isRefreshing = true;
    
    try {
        console.log('🔄 Refreshing application...');
        
        // Refresh shelf state
        await ShelfServices.refreshShelfStateFromServer();
        
        // Sync queue
        await ShelfServices.syncQueueFromBackend();
        
        // Re-render everything
        await ShelfQueue.renderAll();
        
        ShelfNotifications.showNotification('ระบบรีเฟรชเสร็จสิ้น', 'success');
        console.log('✅ Application refresh complete');
        
    } catch (error) {
        console.error('❌ Failed to refresh application:', error);
        ShelfNotifications.showNotification('เกิดข้อผิดพลาดในการรีเฟรช', 'error');
    } finally {
        isRefreshing = false;
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
        refreshGrid: ShelfUI.refreshShelfGrid,
        
        // Additional debug utilities
        clearCache: clearCacheAndRefresh,
        hydrateLocal: hydrateFromLocalStorage,
        debouncedRefresh: debouncedRefresh,
        
        // Global function exposure check
        checkGlobalFunctions: () => {
            const globals = ['selectJob', 'goBackToMain', 'goToQueueSelection', 'handleLotSearch', 'findAndSelectJobByLot'];
            const missing = globals.filter(fn => typeof window[fn] !== 'function');
            if (missing.length > 0) {
                console.warn('⚠️ Missing global functions:', missing);
                return { missing, available: globals.filter(fn => typeof window[fn] === 'function') };
            }
            console.log('✅ All global functions are exposed');
            return { missing: [], available: globals };
        },
        
        // localStorage inspector
        inspectLocalStorage: () => {
            return {
                activeJob: localStorage.getItem(ShelfState.ACTIVE_JOB_KEY),
                queue: localStorage.getItem(ShelfState.QUEUE_KEY),
                shelfState: localStorage.getItem(ShelfState.GLOBAL_SHELF_STATE_KEY),
                shelfConfig: localStorage.getItem('shelfConfig'),
                cellCapacities: localStorage.getItem('cellCapacities')
            };
        }
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

/**
 * เคลียร์ cache และรีโหลด configuration
 */
async function clearCacheAndRefresh() {
    console.log('🔄 Clearing cache and refreshing...');
    
    // เคลียร์ localStorage ครบทุก key
    localStorage.removeItem(ShelfState.GLOBAL_SHELF_STATE_KEY);
    localStorage.removeItem(ShelfState.QUEUE_KEY);
    localStorage.removeItem(ShelfState.ACTIVE_JOB_KEY);
    localStorage.removeItem('shelfConfig');
    localStorage.removeItem('cellCapacities');
    localStorage.removeItem('shelfId');
    
    // เคลียร์ state ใน memory
    ShelfState.setQueue([]);
    ShelfState.removeActiveJob();
    ShelfServices.clearLED();
    
    // รีโหลด configuration
    await ShelfServices.loadShelfConfig();
    
    // สร้าง shelf grid ใหม่
    ShelfUI.refreshShelfGrid();
    
    // รีโหลด shelf state
    await ShelfServices.refreshShelfStateFromServer();
    
    // รีเฟรช UI
    ShelfQueue.renderAll();
    
    console.log('✅ Cache cleared and refreshed');
}

// ฟังก์ชันสำหรับใช้ใน HTML onclick handlers  
function selectJob(jobId) {
    console.log(`🎯 Selecting job: ${jobId}`);
    ShelfQueue.selectJob(jobId);
}

function goBackToMain() {
    console.log('🔙 กลับไปหน้าหลัก');
    window.location.reload();
}

function handleLotSearch(lotNo) {
    console.log(`🔍 ค้นหา LOT: ${lotNo}`);
    // Implementation based on original ui_logic.js behavior
    return false; // Placeholder
}

function onCellClick(cellId) {
    console.log(`📱 Cell clicked: ${cellId}`);
    return ShelfUI.handleCellClick?.(cellId) || false;
}

if (typeof window !== 'undefined') {
    window.ShelfApp = {
        initialize: initializeApplication,
        refresh: refreshApplication,
        clearCacheAndRefresh,
        handleWebSocketMessage,
        setupEventListeners,
        setupConsoleUtilities
    };
    
    // Global functions for HTML onclick handlers
    window.selectJob = selectJob;
    window.goBackToMain = goBackToMain;
    window.handleLotSearch = handleLotSearch;
    window.onCellClick = onCellClick;
}

console.log('📱 Smart Shelf Application loaded');