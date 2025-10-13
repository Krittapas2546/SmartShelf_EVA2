/**
 * services.js - I/O Operations & External Services
 * จัดการ API calls, WebSocket, LED control และ LocalStorage operations
 */

// WebSocket Connection
let websocketConnection = null;

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
                const config = await response.json();
                ShelfState.setShelfConfig(config.SHELF_CONFIG);
                ShelfState.setCellCapacities(config.CELL_CAPACITIES);
                return true;
            }
        }
        return layoutLoaded;
        
    } catch (error) {
        console.warn('⚠️ Failed to load shelf config from server:', error);
        // Fallback config
        const fallbackConfig = {
            1: 6, 2: 6, 3: 6, 4: 6
        };
        const fallbackCapacities = {
            '1-1': 22, '1-2': 24, '1-3': 24, '1-4': 24, '1-5': 24, '1-6': 24
        };
        ShelfState.setShelfConfig(fallbackConfig);
        ShelfState.setCellCapacities(fallbackCapacities);
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

            if (data.success && data.layout && data.layout.slots) {
                const slots = data.layout.slots;
                const newConfig = {};
                const newCapacities = {};

                // แปลง slots เป็น SHELF_CONFIG และ CELL_CAPACITIES
                Object.keys(slots).forEach(slotKey => {
                    const slot = slots[slotKey];
                    const level = slot.level;
                    const block = slot.block;
                    const capacity = slot.max_tray_count || 24;

                    // อัปเดต SHELF_CONFIG
                    if (!newConfig[level] || newConfig[level] < block) {
                        newConfig[level] = block;
                    }

                    // อัปเดต CELL_CAPACITIES
                    newCapacities[`${level}-${block}`] = capacity;
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
        const response = await fetch('/api/queue');
        if (response.ok) {
            const queueData = await response.json();
            if (Array.isArray(queueData)) {
                ShelfState.setQueue(queueData);
                console.log(`✅ Queue synced: ${queueData.length} jobs`);
                return queueData;
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
    
    const shelfId = ShelfState.getShelfId();
    if (!shelfId) {
        console.warn('⚠️ ไม่มี shelf_id - ไม่สามารถดึงงานที่ค้างอยู่ได้');
        return false;
    }
    
    try {
        const response = await fetch('/api/pending-jobs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                shelf_id: shelfId
            })
        });

        if (response.ok) {
            const data = await response.json();
            console.log('📋 Pending jobs response:', data);
            
            if (data.success && Array.isArray(data.jobs) && data.jobs.length > 0) {
                console.log(`✅ พบงานที่ค้างอยู่ ${data.jobs.length} งาน`);
                
                // เพิ่มงานลงใน queue โดยไม่ซ้ำกับที่มีอยู่แล้ว
                const currentQueue = ShelfState.getQueue();
                const existingJobIds = new Set(currentQueue.map(job => job.jobId));
                
                const newJobs = data.jobs.filter(job => !existingJobIds.has(job.jobId));
                
                if (newJobs.length > 0) {
                    const updatedQueue = [...currentQueue, ...newJobs];
                    ShelfState.setQueue(updatedQueue);
                    console.log(`📝 เพิ่มงานใหม่ ${newJobs.length} งาน เข้าสู่คิว`);
                }
            } else {
                console.log('📋 ไม่พบงานที่ค้างอยู่');
            }
            
            ShelfState.setPendingJobsLoaded(true);
            return true;
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
        
        const response = await fetch('/api/lms/check-shelf', {
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
        const response = await fetch('/api/shelf/name');
        if (response.ok) {
            const data = await response.json();
            console.log('📋 Shelf name response:', data);
            
            if (data.success && data.shelf_id) {
                ShelfState.setShelfId(data.shelf_id);
                console.log(`✅ Shelf ID set to: ${data.shelf_id}`);
                
                // อัปเดต title ถ้ามีข้อมูล shelf_name
                if (data.shelf_name) {
                    document.title = `Smart Shelf - ${data.shelf_name}`;
                    console.log(`🏷️ Page title updated to: ${document.title}`);
                }
                
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
 * WEBSOCKET SERVICES
 * ===================
 */

/**
 * เริ่มต้น WebSocket connection
 */
function setupWebSocket(onMessageCallback) {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    websocketConnection = ws;

    ws.onopen = function(event) {
        console.log('🔌 WebSocket connected');
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
        console.log('🔌 WebSocket disconnected');
        websocketConnection = null;
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
        closeWebSocket
    };
}