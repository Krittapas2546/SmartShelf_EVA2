/**
 * services.js - I/O Operations & External Services
 * จัดการ API calls, WebSocket, LED control และ LocalStorage operations
 */

// WebSocket Connection
let websocketConnection = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

/**
 * ===================
 * API SERVICES
 * ===================
 */

/**
 * โหลดการกำหนดค่าจาก Server
 */
async function loadShelfConfig() {
    try {
        // ลองโหลด layout จาก Gateway ก่อน
        const layoutLoaded = await loadLayoutFromGateway();
        
        // ถ้าโหลด layout จาก Gateway ไม่สำเร็จ ให้ใช้ config ปกติ
        if (!layoutLoaded) {
            console.warn('⚠️ Failed to load layout from Gateway, using default config');
            const response = await fetch('/api/shelf/config');
            if (response.ok) {
                const data = await response.json();
                // อ่านฟิลด์ตามรูปแบบเดิม: config, cell_capacities
                const config = data.shelf_config || data.config || {};
                const capacities = data.cell_capacities || {};
                
                ShelfState.setShelfConfig(config);
                ShelfState.setCellCapacities(capacities);
                return true;
            }
        }
        return layoutLoaded;
        
    } catch (error) {
        console.warn('⚠️ Failed to load shelf config from server:', error);
        // Fallback config - ใช้ข้อมูลเดียวกับที่ Gateway ส่งมา (8 columns x 4 levels)
        const fallbackConfig = {
            1: 8, 2: 8, 3: 8, 4: 8
        };
        const fallbackCapacities = {};
        // สร้าง capacity สำหรับทุก cell (8x4 = 32 cells)
        for (let level = 1; level <= 4; level++) {
            for (let block = 1; block <= 8; block++) {
                fallbackCapacities[`${level}-${block}`] = 40;
            }
        }
        ShelfState.setShelfConfig(fallbackConfig);
        ShelfState.setCellCapacities(fallbackCapacities);
        console.log('📋 Using fallback config (8x4):', fallbackConfig);
        return false;
    }
}

/**
 * โหลด layout จาก Gateway
 */
async function loadLayoutFromGateway() {
    try {
        console.log('🔄 Loading layout from Gateway...');
        
        const response = await fetch('/api/shelf/layout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                shelf_id: ShelfState.getShelfId() || "PC2",
                update_flg: "0",
                slots: {}
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📋 Gateway layout response:', data);

            // ตรวจสอบ format ใหม่จาก Backend API
            if (data.status === "success" && data.layout) {
                const layout = data.layout;
                const newConfig = {};
                const newCapacities = {};

                // แปลง layout เป็น SHELF_CONFIG และ CELL_CAPACITIES
                // layout format: {"L1B1": {...}, "L1B2": {...}, ...}
                Object.keys(layout).forEach(positionKey => {
                    // Parse position key (L1B1 -> level=1, block=1)
                    const match = positionKey.match(/^L(\d+)B(\d+)$/);
                    if (match) {
                        const level = parseInt(match[1]);
                        const block = parseInt(match[2]);
                        const slot = layout[positionKey];
                        const capacity = slot.max_tray_count || 40;

                        // อัปเดต SHELF_CONFIG
                        if (!newConfig[level] || newConfig[level] < block) {
                            newConfig[level] = block;
                        }

                        // อัปเดต CELL_CAPACITIES
                        newCapacities[`${level}-${block}`] = capacity;
                    }
                });

                ShelfState.setShelfConfig(newConfig);
                ShelfState.setCellCapacities(newCapacities);
                
                console.log('✅ Layout loaded from Gateway successfully');
                console.log('📋 New shelf config:', newConfig);
                console.log('📏 New cell capacities:', newCapacities);
                return true;
            }
        }
        
        console.log('⚠️ Failed to load layout from Gateway, using local config');
        return false;
        
    } catch (error) {
        console.error('❌ Error loading layout from Gateway:', error);
        return false;
    }
}

/**
 * ดึงข้อมูล shelf state จาก server
 */
async function getShelfStateFromServer() {
    try {
        const response = await fetch('/api/shelf/state');
        if (response.ok) {
            const data = await response.json();
            return data.shelf_state || [];
        }
        return null;
    } catch (error) {
        console.error('❌ Error fetching shelf state:', error);
        return null;
    }
}

/**
 * ซิงค์คิวจาก backend
 */
async function syncQueueFromBackend() {
    try {
        console.log('🔄 Syncing queue from backend...');
        const response = await fetch('/command');
        if (response.ok) {
            const data = await response.json();
            const jobs = data.jobs || [];
            if (Array.isArray(jobs)) {
                ShelfState.setQueue(jobs);
                console.log(`✅ Queue synced: ${jobs.length} jobs`);
                return jobs;
            }
        }
        console.warn('⚠️ Failed to sync queue from backend');
        return null;
    } catch (error) {
        console.error('❌ Error syncing queue:', error);
        return null;
    }
}

/**
 * โหลดงานที่ค้างอยู่จาก Gateway
 */
async function loadPendingJobsFromGateway() {
    console.log('🔄 กำลังดึงงานที่ค้างอยู่จาก Gateway ผ่าน API...');
    
    const uiState = ShelfState.getUIState();
    if (uiState.pendingJobsLoaded) {
        console.log('📋 งานที่ค้างอยู่ถูกโหลดแล้ว - ข้าม');
        return false;
    }
    
    try {
        // ใช้ endpoint เดิม ไม่ต้องส่ง shelf_id ใน body
        const response = await fetch('/api/shelf/pending/load', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📋 Pending jobs response:', data);
            
            if (data.status === 'success' && data.loaded_count > 0) {
                console.log(`✅ โหลดงานที่ค้างอยู่ ${data.loaded_count} งาน`);
                
                // รอ WebSocket broadcast jobs_reloaded หรือ sync queue ใหม่
                await new Promise(resolve => setTimeout(resolve, 1000));
                await syncQueueFromBackend();
                
                ShelfState.setPendingJobsLoaded(true);
                return true;
            } else {
                console.log('📋 ไม่พบงานที่ค้างอยู่');
                ShelfState.setPendingJobsLoaded(true);
                return false;
            }
        } else {
            console.error('❌ Failed to load pending jobs:', response.status);
            return false;
        }
        
    } catch (error) {
        console.error('❌ Error loading pending jobs:', error);
        return false;
    }
}

/**
 * ส่งคำสั่ง Complete Job
 */
async function completeJob(jobId) {
    try {
        console.log(`🚀 Completing job: ${jobId}`);
        
        const response = await fetch(`/command/${jobId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Job completed successfully:', data);
            return { success: true, data };
        } else {
            const errorData = await response.json();
            console.error('❌ Job completion failed:', errorData);
            return { success: false, error: errorData };
        }
    } catch (error) {
        console.error('❌ Error completing job:', error);
        return { success: false, error: error.message };
    }
}

/**
 * ตรวจสอบชั้นวางที่ถูกต้องจาก LMS
 */
async function checkShelfFromLMS(lotNo, placeFlg) {
    if (!lotNo) {
        console.warn('⚠️ ไม่มี LOT number สำหรับตรวจสอบ LMS');
        return { success: false, error: 'ไม่มี LOT number' };
    }

    try {
        console.log(`🔍 ตรวจสอบชั้นวางจาก LMS สำหรับ LOT: ${lotNo}`);
        
        const response = await fetch('/api/shelf/askCorrectShelf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                lotNo: lotNo,
                placeFlg: placeFlg || "1",
                shelf_id: ShelfState.getShelfId() || "PC2"
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📋 LMS response:', data);
            
            if (data.success) {
                return {
                    success: true,
                    lotNo: data.lotNo,
                    correctShelf: data.correctShelf,
                    placeFlg: data.placeFlg
                };
            } else {
                return { success: false, error: data.error || 'ไม่พบข้อมูลจาก LMS' };
            }
        } else {
            const errorData = await response.json();
            return { success: false, error: errorData.error || 'เกิดข้อผิดพลาดในการเชื่อมต่อ LMS' };
        }
        
    } catch (error) {
        console.error('❌ Error checking LMS:', error);
        return { success: false, error: 'เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์' };
    }
}

/**
 * รีเฟรช shelf state จาก server
 */
async function refreshShelfStateFromServer() {
    try {
        console.log('🔄 Refreshing shelf state from server...');
        const shelfState = await getShelfStateFromServer();
        if (shelfState) {
            ShelfState.setShelfState(shelfState);
            console.log('✅ Shelf state refreshed from server');
            return true;
        }
        return false;
    } catch (error) {
        console.error('❌ Error refreshing shelf state:', error);
        return false;
    }
}

/**
 * ดึงข้อมูล shelf name และ shelf_id
 */
async function initializeShelfName() {
    console.log('🏷️ กำลังดึงข้อมูล shelf name และ shelf_id จาก Gateway...');
    
    try {
        const response = await fetch('/ShelfName');
        if (response.ok) {
            const data = await response.json();
            console.log('📋 Shelf name response:', data);
            
            if (data.success && data.shelf_id) {
                ShelfState.setShelfId(data.shelf_id);
                console.log(`✅ Shelf ID set to: ${data.shelf_id}`);
                
                // อัปเดต title ด้วย shelf_id
                document.title = `Smart Shelf - ${data.shelf_id}`;
                console.log(`🏷️ Page title updated to: ${document.title}`);
                
                return true;
            } else {
                console.warn('⚠️ ไม่ได้รับ shelf_id จาก response');
                return false;
            }
        } else {
            console.error('❌ Failed to fetch shelf name:', response.status);
            return false;
        }
    } catch (error) {
        console.error('❌ Error fetching shelf name:', error);
        return false;
    }
}

/**
 * ===================
 * LED CONTROL SERVICES
 * ===================
 */

/**
 * ล้างไฟ LED ทั้งหมด
 */
async function clearLED() {
    try {
        const response = await fetch('/api/led/clear', { method: 'POST' });
        if (response.ok) {
            console.log('💡 LED cleared');
            return true;
        }
        return false;
    } catch (error) {
        console.error('💡 LED clear error:', error);
        return false;
    }
}

/**
 * ตั้งค่าไฟ LED สำหรับตำแหน่งเดียว
 */
async function setLED(position, r = 0, g = 255, b = 0) {
    try {
        const response = await fetch('/api/led', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ position, r, g, b })
        });
        
        if (response.ok) {
            console.log(`💡 LED set: ${position} RGB(${r},${g},${b})`);
            return true;
        }
        return false;
    } catch (error) {
        console.error('💡 LED set error:', error);
        return false;
    }
}

/**
 * ตั้งค่าไฟ LED หลายตำแหน่งพร้อมกัน
 */
async function setBatchLED(positions, clearFirst = true) {
    try {
        const response = await fetch('/api/led', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                positions,
                clear_first: clearFirst 
            })
        });
        
        if (response.ok) {
            console.log(`💡 LED batch set: ${positions.length} positions`);
            return true;
        }
        return false;
    } catch (error) {
        console.error('💡 LED batch error:', error);
        return false;
    }
}

/**
 * ===================
 * HYDRATION FUNCTIONS
 * ===================
 */

/**
 * สร้างงานตัวอย่างสำหรับทดสอบ
 */
function hydrateWithDummyJobs() {
    console.log('📋 กำลังสร้างงานตัวอย่างสำหรับทดสอบ...');
    
    const dummyJobs = [
        {
            jobId: 'JOB-2024-001',
            lotNo: 'LOT001',
            productCode: 'PRD-001',
            productName: 'สินค้าทดสอบ A',
            quantity: 10,
            targetCell: 'A1',
            status: 'pending',
            createdAt: new Date().toISOString()
        },
        {
            jobId: 'JOB-2024-002', 
            lotNo: 'LOT002',
            productCode: 'PRD-002',
            productName: 'สินค้าทดสอบ B',
            quantity: 15,
            targetCell: 'B3',
            status: 'pending',
            createdAt: new Date().toISOString()
        }
    ];
    
    // เพิ่มงานลงใน localStorage และ state
    const currentQueue = ShelfState.getQueue() || [];
    const newQueue = [...currentQueue, ...dummyJobs];
    ShelfState.setQueue(newQueue);
    
    console.log(`✅ เพิ่มงานตัวอย่าง ${dummyJobs.length} งาน`);
    return dummyJobs;
}

/**
 * สร้าง shelf config ตัวอย่าง (8x4 grid)
 */
function hydrateWithDefaultShelfConfig() {
    console.log('🏗️ กำลังสร้าง shelf config ตัวอย่าง...');
    
    const defaultConfig = {
        rows: 4,
        columns: 8,
        total_cells: 32,
        shelf_id: "PC2",
        cell_capacities: {}
    };
    
    // สร้าง cell capacities สำหรับ grid 8x4
    const rows = ['A', 'B', 'C', 'D'];
    for (let row = 0; row < 4; row++) {
        for (let col = 1; col <= 8; col++) {
            const cellId = `${rows[row]}${col}`;
            defaultConfig.cell_capacities[cellId] = 50; // default capacity
        }
    }
    
    ShelfState.setShelfConfig(defaultConfig);
    
    console.log('✅ สร้าง default shelf config (8x4) สำเร็จ');
    return defaultConfig;
}

/**
 * ===================
 * WEBSOCKET SERVICES
 * ===================
 */

/**
 * เริ่มต้น WebSocket connection พร้อม auto-reconnection
 */
function setupWebSocket(onMessageCallback) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    console.log(`🔄 กำลังเชื่อมต่อ WebSocket: ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);
    
    websocketConnection = ws;

    ws.onopen = function(event) {
        console.log('🔌 WebSocket connected');
        reconnectAttempts = 0; // Reset counter on successful connection
    };

    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            console.log('📨 WebSocket message received:', data);
            
            if (onMessageCallback && typeof onMessageCallback === 'function') {
                onMessageCallback(data);
            }
        } catch (error) {
            console.error('❌ Error parsing WebSocket message:', error);
        }
    };

    ws.onclose = function(event) {
        console.log('🔌 WebSocket disconnected:', event.code, event.reason);
        websocketConnection = null;
        
        // Auto reconnect after 3 seconds
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++;
            console.log(`🔄 กำลังลอง reconnect ครั้งที่ ${reconnectAttempts}/${maxReconnectAttempts} ใน 3 วินาที...`);
            setTimeout(() => {
                setupWebSocket(onMessageCallback);
            }, 3000);
        } else {
            console.error('❌ ไม่สามารถ reconnect WebSocket ได้หลังจาก', maxReconnectAttempts, 'ครั้ง');
        }
    };

    ws.onerror = function(error) {
        console.error('❌ WebSocket error:', error);
    };

    return ws;
}

/**
 * ส่งข้อความผ่าน WebSocket
 */
function sendWebSocketMessage(message) {
    if (websocketConnection && websocketConnection.readyState === WebSocket.OPEN) {
        websocketConnection.send(JSON.stringify(message));
        return true;
    }
    console.warn('⚠️ WebSocket not connected');
    return false;
}

/**
 * ปิด WebSocket connection
 */
function closeWebSocket() {
    if (websocketConnection) {
        websocketConnection.close();
        websocketConnection = null;
    }
}

/**
 * ===================
 * EXPORT SERVICES MODULE
 * ===================
 */

if (typeof window !== 'undefined') {
    window.ShelfServices = {
        // API Services
        loadShelfConfig,
        loadLayoutFromGateway,
        getShelfStateFromServer,
        syncQueueFromBackend,
        loadPendingJobsFromGateway,
        completeJob,
        checkShelfFromLMS,
        refreshShelfStateFromServer,
        initializeShelfName,
        
        // LED Control
        clearLED,
        setLED,
        setBatchLED,
        
        // WebSocket
        setupWebSocket,
        sendWebSocketMessage,
        closeWebSocket,
        
        // Hydration (Development)
        hydrateWithDummyJobs,
        hydrateWithDefaultShelfConfig
    };
}