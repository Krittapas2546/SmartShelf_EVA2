/**
 * state.js - State Management, Actions & Selectors
 * จัดการสถานะระบบ, การกระทำ และ Selectors สำหรับอ่านข้อมูล
 */

// State Keys
const ACTIVE_JOB_KEY = 'activeJob';
const GLOBAL_SHELF_STATE_KEY = 'globalShelfState';
const QUEUE_KEY = 'shelfQueue';

// Global State Variables
let SHELF_CONFIG = {};
let TOTAL_LEVELS = 0;
let MAX_BLOCKS = 0;
let CELL_CAPACITIES = {};
let shelf_id = null;

// UI State Management
let showMainWithQueue = false;
let autoReturnTimer = null;
let activityDetectionActive = false;
let pendingJobsLoaded = false;

// Global logged cells tracker
if (!window.__rfid_loggedCells) window.__rfid_loggedCells = new Set();

/**
 * ===================
 * STATE GETTERS (Read-only access)
 * ===================
 */

function getShelfConfig() {
    return { ...SHELF_CONFIG };
}

function getTotalLevels() {
    return TOTAL_LEVELS;
}

function getMaxBlocks() {
    return MAX_BLOCKS;
}

function getCellCapacities() {
    return { ...CELL_CAPACITIES };
}

function getShelfId() {
    return shelf_id;
}

function getUIState() {
    return {
        showMainWithQueue,
        autoReturnTimer: !!autoReturnTimer,
        activityDetectionActive,
        pendingJobsLoaded
    };
}

/**
 * ===================
 * STATE SETTERS (Actions)
 * ===================
 */

function setShelfConfig(config) {
    SHELF_CONFIG = { ...config };
    TOTAL_LEVELS = Math.max(...Object.keys(config).map(Number));
    MAX_BLOCKS = Math.max(...Object.values(config));
    console.log('📋 Shelf config updated:', SHELF_CONFIG);
}

function setCellCapacities(capacities) {
    CELL_CAPACITIES = { ...capacities };
    console.log('📏 Cell capacities updated:', CELL_CAPACITIES);
}

function setShelfId(id) {
    shelf_id = id;
    console.log('🏷️ Shelf ID updated:', shelf_id);
}

function setShowMainWithQueue(show) {
    showMainWithQueue = show;
}

function setAutoReturnTimer(timer) {
    if (autoReturnTimer) {
        clearTimeout(autoReturnTimer);
    }
    autoReturnTimer = timer;
}

function setActivityDetectionActive(active) {
    activityDetectionActive = active;
}

function setPendingJobsLoaded(loaded) {
    pendingJobsLoaded = loaded;
}

/**
 * ===================
 * LOCALSTORAGE OPERATIONS
 * ===================
 */

function getActiveJob() {
    const activeJobData = localStorage.getItem(ACTIVE_JOB_KEY);
    
    if (!activeJobData || activeJobData === 'null') {
        return null;
    }
    
    try {
        return JSON.parse(activeJobData);
    } catch (error) {
        console.error('Error parsing active job data:', error);
        return null;
    }
}

function setActiveJob(job) {
    localStorage.setItem(ACTIVE_JOB_KEY, JSON.stringify(job));
}

function removeActiveJob() {
    localStorage.removeItem(ACTIVE_JOB_KEY);
}

function getQueue() {
    return cleanInvalidJobs();
}

function setQueue(queue) {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

function addToQueue(job) {
    const queue = getQueue();
    queue.push(job);
    setQueue(queue);
}

function removeFromQueue(jobId) {
    const queue = getQueue();
    const filteredQueue = queue.filter(job => job.jobId !== jobId);
    setQueue(filteredQueue);
}

function cleanInvalidJobs() {
    const queue = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
    const cleanedQueue = queue.filter(job => job && job.lot_no && job.level && job.block);
    if (cleanedQueue.length !== queue.length) {
        console.warn("Removed invalid jobs from the queue.");
        localStorage.setItem(QUEUE_KEY, JSON.stringify(cleanedQueue));
    }
    return cleanedQueue;
}

function getShelfState() {
    return JSON.parse(localStorage.getItem(GLOBAL_SHELF_STATE_KEY) || '[]');
}

function setShelfState(state) {
    localStorage.setItem(GLOBAL_SHELF_STATE_KEY, JSON.stringify(state));
}

function initializeShelfState() {
    if (!localStorage.getItem(GLOBAL_SHELF_STATE_KEY)) {
        const defaultState = [];
        // สร้างสถานะเริ่มต้นตาม SHELF_CONFIG
        for (let level = 1; level <= TOTAL_LEVELS; level++) {
            const blocksInLevel = SHELF_CONFIG[level] || 0;
            for (let block = 1; block <= blocksInLevel; block++) {
                defaultState.push({ level, block, lots: [] });
            }
        }
        localStorage.setItem(GLOBAL_SHELF_STATE_KEY, JSON.stringify(defaultState));
    }
}

/**
 * ===================
 * SELECTORS (Data Access)
 * ===================
 */

// Utility: Get lots in a specific cell (level, block)
function getLotsInCell(level, block) {
    const shelfState = getShelfState();
    for (const cellData of shelfState) {
        let cellLevel, cellBlock, cellLots;
        if (Array.isArray(cellData)) {
            // แบบเก่า: [level, block, lots]
            [cellLevel, cellBlock, cellLots] = cellData;
        } else {
            // แบบใหม่: {level, block, lots}
            cellLevel = cellData.level;
            cellBlock = cellData.block;
            cellLots = cellData.lots;
        }
        if (String(cellLevel) === String(level) && String(cellBlock) === String(block)) {
            return Array.isArray(cellLots) ? cellLots : [];
        }
    }
    return [];
}

// Utility: Get cell capacity (actual max trays for a specific cell)
function getCellCapacity(level, block) {
    const cellKey = `${level}-${block}`;
    // ใช้ข้อมูลจาก Backend ที่โหลดมาแล้ว
    return CELL_CAPACITIES[cellKey] || 24; // ถ้าไม่มีข้อมูล ใช้ 24 เป็นค่าเริ่มต้น
}

// Get job by ID
function getJobById(jobId) {
    const queue = getQueue();
    return queue.find(job => job.jobId === jobId);
}

// Get job by lot number
function getJobByLotNo(lotNo) {
    const queue = getQueue();
    return queue.find(job => job.lot_no === lotNo);
}

// Check if lot exists in queue
function isLotInQueue(lotNo) {
    return !!getJobByLotNo(lotNo);
}

// Get place jobs (วาง)
function getPlaceJobs() {
    const queue = getQueue();
    return queue.filter(job => job.place_flg === '1');
}

// Get pick jobs (หยิบ)
function getPickJobs() {
    const queue = getQueue();
    return queue.filter(job => job.place_flg === '0');
}

// Get queue count
function getQueueCount() {
    return getQueue().length;
}

/**
 * ===================
 * TIMER MANAGEMENT
 * ===================
 */

function startAutoReturnTimer(callback, delay = 7000) {
    if (autoReturnTimer) {
        clearTimeout(autoReturnTimer);
    }
    
    autoReturnTimer = setTimeout(() => {
        callback();
        autoReturnTimer = null;
    }, delay);
}

function stopAutoReturnTimer() {
    if (autoReturnTimer) {
        clearTimeout(autoReturnTimer);
        autoReturnTimer = null;
    }
}

function resetAutoReturnTimer(callback, delay = 7000) {
    if (showMainWithQueue && autoReturnTimer) {
        stopAutoReturnTimer();
        startAutoReturnTimer(callback, delay);
    }
}

/**
 * ===================
 * LOGGED CELLS MANAGEMENT
 * ===================
 */

function clearLoggedCells() {
    if (window.__rfid_loggedCells) {
        window.__rfid_loggedCells.clear();
    }
}

function addLoggedCell(cellKey) {
    if (window.__rfid_loggedCells) {
        window.__rfid_loggedCells.add(cellKey);
    }
}

function hasLoggedCell(cellKey) {
    return window.__rfid_loggedCells ? window.__rfid_loggedCells.has(cellKey) : false;
}

/**
 * ===================
 * EXPORT STATE MODULE
 * ===================
 */

if (typeof window !== 'undefined') {
    window.ShelfState = {
        // Constants
        ACTIVE_JOB_KEY,
        GLOBAL_SHELF_STATE_KEY,
        QUEUE_KEY,
        
        // State Getters
        getShelfConfig,
        getTotalLevels,
        getMaxBlocks,
        getCellCapacities,
        getShelfId,
        getUIState,
        
        // State Actions
        setShelfConfig,
        setCellCapacities,
        setShelfId,
        setShowMainWithQueue,
        setAutoReturnTimer,
        setActivityDetectionActive,
        setPendingJobsLoaded,
        
        // LocalStorage Operations
        getActiveJob,
        setActiveJob,
        removeActiveJob,
        getQueue,
        setQueue,
        addToQueue,
        removeFromQueue,
        cleanInvalidJobs,
        getShelfState,
        setShelfState,
        initializeShelfState,
        
        // Selectors
        getLotsInCell,
        getCellCapacity,
        getJobById,
        getJobByLotNo,
        isLotInQueue,
        getPlaceJobs,
        getPickJobs,
        getQueueCount,
        
        // Timer Management
        startAutoReturnTimer,
        stopAutoReturnTimer,
        resetAutoReturnTimer,
        
        // Logged Cells
        clearLoggedCells,
        addLoggedCell,
        hasLoggedCell
    };
}