// --- Cell Preview: แสดงรายละเอียดช่องที่เลือก (IMPROVED DESIGN) ---
function renderCellPreview({ level, block, lots, targetLotNo, isPlaceJob = false, newLotTrayCount = 0 }) {
    const container = document.getElementById('cellPreviewContainer');
    if (!container) return;

    // lots: array of {lot_no, tray_count}
    if (!Array.isArray(lots)) lots = [];

    // ถ้าเป็น Place job ให้จำลองการวางของใหม่
    let previewLots = [...lots];
    if (isPlaceJob && targetLotNo && newLotTrayCount > 0) {
        // เพิ่ม lot ใหม่ที่จะวางลงไปด้านบน (LIFO)
        previewLots.push({
            lot_no: targetLotNo,
            tray_count: newLotTrayCount
        });
    }

    let html = '';
    html += `<h3>Level ${level} Block ${block}</h3>`;
    
    // แสดงข้อความแตกต่างกันตาม action
 
    
    html += `<div class="block-preview">`;

    if (previewLots.length > 0) {
        // สร้างรายการ lot แนวตั้ง (จากล่างขึ้นบน)
        for (let i = previewLots.length - 1; i >= 0; i--) {
            const lot = previewLots[i];
            const trayCount = parseInt(lot.tray_count) || 0;
            const isTarget = lot.lot_no === targetLotNo;
            const isNewLot = isPlaceJob && i === previewLots.length - 1 && isTarget;

            // คำนวณความสูงตามสัดส่วน tray_count เทียบกับความจุจริงของ cell
            const maxCapacity = getCellCapacity(level, block); // ใช้ความจุจริงของ cell แทนค่าคงที่ 24
            const maxContainerHeight = 300; // ความสูงที่ใช้ได้ของ container (350px - padding)
            const heightRatio = trayCount / maxCapacity;
            const height = Math.max(heightRatio * maxContainerHeight, 8); // ลดความสูงขั้นต่ำเป็น 8px เพื่อให้แสดงสัดส่วนที่ถูกต้อง

            // ตัดชื่อ lot ถ้ายาวเกินไป (สำหรับ desktop ใช้ 15 ตัวอักษร)
            const displayName = lot.lot_no.length > 15 ?
                lot.lot_no.substring(0, 15) + '...' :
                lot.lot_no;

            let itemClass = 'lot-item';
            if (isTarget) itemClass += ' target-lot';
            if (isNewLot) itemClass += ' new-lot';

            html += `<div class="${itemClass}" style="height: ${height}px;" title="${lot.lot_no} - ${trayCount} trays">`;
            html += `<span class="lot-name ${isTarget ? 'lot-name-large' : ''}">${displayName}</span>`;
            if (isNewLot) {
                html += `<span class="new-badge"> NEW</span>`;
            }
            html += `</div>`;
        }
    } else {
        html += `<div class="lot-item empty-slot">`;
        html += `<span class="lot-name">(empty)</span>`;
        html += `</div>`;
    }

    html += `</div>`;
    container.innerHTML = html;
}
// Utility: Get lots in a specific cell (level, block)
function getLotsInCell(level, block) {
    const shelfState = JSON.parse(localStorage.getItem(GLOBAL_SHELF_STATE_KEY) || '[]');
    for (const cellData of shelfState) {
        let cellLevel, cellBlock, cellLots;
        if (Array.isArray(cellData)) {
            cellLevel = cellData[0];
            cellBlock = cellData[1];
            cellLots = cellData[2];
        } else if (cellData && typeof cellData === 'object') {
            ({ level: cellLevel, block: cellBlock, lots: cellLots } = cellData);
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

// Example usage: log lots in Level 1, Block 2
// console.log(getLotsInCell(1, 2));
        /**
         * แสดงไฟฟ้าทุกช่องที่มี job ใน queue (queueSelectionView)
         */
        function controlLEDByQueue() {
            const queue = getQueue();
            if (!queue || queue.length === 0) {
                console.log('💡 No queue items - clearing LEDs');
                fetch('/api/led/clear', { method: 'POST' });
                return;
            }
            
            console.log(`💡 LED Queue Mode: ${queue.length} jobs`);
            
            // เตรียม batch สำหรับทุก job ใน queue
            const positions = queue.map(job => ({
                position: `L${Number(job.level)}B${Number(job.block)}`,
                r: 0, g: 150, b: 255 // ฟ้าสว่างสำหรับ queue
            }));
            
            fetch('/api/led', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    positions,
                    clear_first: true 
                })
            })
                .then(response => {
                    if (!response.ok) {
                        console.error('💡 LED Queue batch failed:', response.status);
                        return response.text().then(text => console.error('Details:', text));
                    }
                    return response.json();
                })
                .then(data => {
                    if (data) {
                        console.log('💡 LED Queue batch success:', data);
                    }
                })
                .catch(error => {
                    console.error('💡 LED Queue batch error:', error);
                });
        }
        const ACTIVE_JOB_KEY = 'activeJob';
        const GLOBAL_SHELF_STATE_KEY = 'globalShelfState';
        const QUEUE_KEY = 'shelfQueue';

        // เพิ่มตัวแปรสำหรับจัดการโหมด main-with-queue และ auto-return timer
        let showMainWithQueue = false;
        let autoReturnTimer = null;
        let activityDetectionActive = false;

        const queueSelectionView = document.getElementById('queueSelectionView');
        const activeJobView = document.getElementById('activeJobView');
        const queueListContainer = document.getElementById('queueListContainer');
        const mainView = document.getElementById('mainView');
        const shelfGrid = document.getElementById('shelfGrid');
        const mainContainer = document.getElementById('mainContainer');        localStorage.removeItem(ACTIVE_JOB_KEY);

        let SHELF_CONFIG = {};
        let TOTAL_LEVELS = 0;
        let MAX_BLOCKS = 0;
        let shelf_id = null; // เพิ่มตัวแปรสำหรับเก็บ shelf_id

        // Flag เพื่อป้องกันการเรียก pending jobs ซ้ำ
        let pendingJobsLoaded = false;

        // ฟังก์ชันสำหรับ Force Refresh Shelf Grid Structure
        function refreshShelfGrid() {
            console.log('🔄 Force refreshing shelf grid with config:', SHELF_CONFIG);
            
            // เคลียร์ localStorage เพื่อให้สร้าง state ใหม่
            localStorage.removeItem(GLOBAL_SHELF_STATE_KEY);
            
            if (shelfGrid) {
                createShelfGridStructure();
                initializeShelfState(); // สร้าง state ใหม่ตาม config ปัจจุบัน
                renderShelfGrid();
                console.log('✅ Shelf grid refreshed successfully');
            }
        }

        // ตัวแปรสำหรับเก็บความจุรายช่อง
        let CELL_CAPACITIES = {};

        // ฟังก์ชันโหลดการกำหนดค่าจาก Server
        async function loadShelfConfig() {
            try {
                // ลองโหลด layout จาก Gateway ก่อน
                const layoutLoaded = await loadLayoutFromGateway();
                
                // ถ้าโหลด layout จาก Gateway ไม่สำเร็จ ให้ใช้ config ปกติ
                if (!layoutLoaded) {
                    const response = await fetch('/api/shelf/config');
                    const data = await response.json();
                    SHELF_CONFIG = data.config;
                    TOTAL_LEVELS = data.total_levels;
                    MAX_BLOCKS = data.max_blocks;
                    CELL_CAPACITIES = data.cell_capacities || {}; // เพิ่มข้อมูลความจุ
                    console.log('📐 Shelf configuration loaded from server:', SHELF_CONFIG);
                    console.log('📏 Cell capacities loaded:', CELL_CAPACITIES);
                }
                
                // สร้าง grid structure ใหม่หลังจากโหลด config
                if (shelfGrid) {
                    refreshShelfGrid(); // ใช้ refreshShelfGrid แทน
                }
            } catch (error) {
                console.warn('⚠️ Failed to load shelf config from server, using local config:', SHELF_CONFIG);
                // Fallback capacities
                CELL_CAPACITIES = {
                    '1-1': 22, '1-2': 24, '1-3': 24, '1-4': 24, '1-5': 24, '1-6': 24
                };
                console.log('📏 Using fallback cell capacities:', CELL_CAPACITIES);
                // ใช้ config ท้องถิ่นแทน และสร้าง grid
                if (shelfGrid) {
                    refreshShelfGrid();
                }
            }
        }

        // ฟังก์ชันโหลด layout จาก Gateway
        async function loadLayoutFromGateway() {
            try {
                console.log('🔄 Loading layout from Gateway...');
                
                const response = await fetch('/api/shelf/layout', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        shelf_id: shelf_id || "PC2", // ใช้ shelf_id ที่มีหรือค่าเริ่มต้น
                        update_flg: "0", // อ่านข้อมูล
                        slots: {}
                    })
                });

                if (response.ok) {
                    const layoutData = await response.json();
                    
                    if (layoutData.status === "success" && layoutData.layout) {
                        console.log('✅ Gateway layout loaded:', layoutData.layout);
                        
                        // แปลงข้อมูล Gateway layout เป็น format ที่ Frontend ใช้
                        const gatewayLayout = layoutData.layout;
                        const newShelfConfig = {};
                        const newCellCapacities = {};
                        
                        for (const [positionKey, slotInfo] of Object.entries(gatewayLayout)) {
                            if (!slotInfo.active) continue; // ข้าม slot ที่ไม่ active
                            
                            const level = parseInt(slotInfo.level);
                            const block = parseInt(slotInfo.block);
                            const capacity = parseInt(slotInfo.capacity);
                            
                            // อัปเดต shelf config
                            if (!newShelfConfig[level]) {
                                newShelfConfig[level] = 0;
                            }
                            newShelfConfig[level] = Math.max(newShelfConfig[level], block);
                            
                            // อัปเดต cell capacities
                            const cellKey = `${level}-${block}`;
                            newCellCapacities[cellKey] = capacity;
                        }
                        
                        // อัปเดต global variables
                        SHELF_CONFIG = newShelfConfig;
                        CELL_CAPACITIES = newCellCapacities;
                        TOTAL_LEVELS = Object.keys(newShelfConfig).length;
                        MAX_BLOCKS = Math.max(...Object.values(newShelfConfig));
                        
                        console.log('📊 Updated config from Gateway:', {
                            SHELF_CONFIG,
                            CELL_CAPACITIES,
                            TOTAL_LEVELS,
                            MAX_BLOCKS
                        });
                        
                        // แสดง notification
                        showNotification(`Layout โหลดจาก Gateway สำเร็จ (${Object.keys(gatewayLayout).length} ช่อง)`, 'success');
                        
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
        
        // 🔼 END OF FLEXIBLE CONFIGURATION 🔼

        // 🔽 ADD THIS FUNCTION 🔽
        function showNotification(message, type = 'info', options = {}) {
            console.log(`📢 ${type.toUpperCase()}: ${message}`);
            
            // ลบ notification เก่าทั้งหมดก่อน (ยกเว้น persistent notifications ถ้าไม่ใช่ persistent notification ใหม่)
            if (!options.persistent) {
                const existingNotifications = document.querySelectorAll('.notification:not(.persistent):not(#persistent-correct-shelf):not([data-persistent="true"])');
                existingNotifications.forEach(notification => {
                    notification.remove();
                });
            } else {
                // ถ้าเป็น persistent notification ให้ลบ persistent เก่าก่อน
                const existingPersistent = document.querySelectorAll('.notification.persistent, #persistent-correct-shelf');
                existingPersistent.forEach(notification => {
                    notification.remove();
                });
            }
            
            const notification = document.createElement('div');
            notification.className = `notification ${type} ${options.persistent ? 'persistent' : ''}`;
            notification.textContent = message;
            
            // Basic styling with larger text for persistent notifications
            const fontSize = options.persistent ? '18px' : '14px';
            const fontWeight = options.persistent ? '900' : 'bold';
            const padding = options.persistent ? '20px 25px' : '15px 20px';
            
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: ${padding};
                border-radius: 8px;
                color: white;
                font-weight: ${fontWeight};
                font-size: ${fontSize};
                z-index: 1000;
                opacity: 0;
                transition: all 0.3s ease-in-out;
                transform: translateX(100%);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                max-width: 350px;
                word-wrap: break-word;
            `;
            
            // Colors based on type
            switch (type) {
                case 'success': notification.style.backgroundColor = '#28a745'; break;
                case 'error': notification.style.backgroundColor = '#dc3545'; break;
                case 'warning': notification.style.backgroundColor = '#ffc107'; notification.style.color = '#212529'; break;
                case 'info': notification.style.backgroundColor = '#17a2b8'; break;
                default: notification.style.backgroundColor = '#6c757d';
            }
            
            document.body.appendChild(notification);
            
            // Animate in
            setTimeout(() => {
                notification.style.opacity = '1';
                notification.style.transform = 'translateX(0)';
            }, 100);
            
            // Auto-remove only if not persistent
            if (!options.persistent) {
                setTimeout(() => {
                    notification.style.opacity = '0';
                    notification.style.transform = 'translateX(100%)';
                    setTimeout(() => notification.remove(), 300);
                }, 3000);
            }
        }
        
        // Function to clear persistent notifications
        function clearPersistentNotifications() {
            // ล้าง notification แบบเก่าและแบบใหม่
            const persistentNotifications = document.querySelectorAll('.notification.persistent, #persistent-correct-shelf, [data-persistent="true"]');
            persistentNotifications.forEach(notification => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            });
            console.log('🧹 Cleared persistent notifications');
        }

        // Function to protect persistent notifications from being removed
        function protectPersistentNotifications() {
            const persistentNotification = document.getElementById('persistent-correct-shelf');
            if (persistentNotification) {
                // ป้องกันการลบโดยการ override remove method
                const originalRemove = persistentNotification.remove;
                persistentNotification.remove = function() {
                    console.log('🛡️ Prevented removal of persistent notification');
                    // ไม่ทำอะไร - ป้องกันการลบ
                };
                
                // ตรวจสอบและกู้คืน style ถ้าถูกเปลี่ยน
                setInterval(() => {
                    if (persistentNotification.parentNode && persistentNotification.style.display === 'none') {
                        persistentNotification.style.display = 'block';
                        console.log('🔧 Restored persistent notification visibility');
                    }
                }, 1000);
            }
        }

        /**
         * แสดง Rich Notification พร้อมรายละเอียด LMS
         * @param {Object} lmsData - ข้อมูลจาก LMS
         * @param {string} type - ประเภท notification
         */
        function showLMSNotification(lmsData, type = 'success') {
            console.log(`📋 LMS Notification:`, lmsData);
            
            // ลบ notification เก่าทั้งหมดก่อน (ยกเว้น persistent notifications)
            const existingNotifications = document.querySelectorAll('.notification:not(.persistent):not(#persistent-correct-shelf)');
            existingNotifications.forEach(notification => {
                notification.remove();
            });
            
            const notification = document.createElement('div');
            notification.className = `notification lms-notification ${type}`;
            
            // สร้าง HTML สำหรับ rich notification
            notification.innerHTML = `
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 16px; margin-right: 8px;">📋</span>
                    <strong>ข้อมูลจาก LMS</strong>
                </div>
                <div style="font-size: 14px; line-height: 1.4;">
                    <div>• LOT: <strong>${lmsData.lotNo}</strong></div>
                    <div>• ชั้นวาง: <strong>${lmsData.correctShelf}</strong></div>
                    <div>• ประเภท: <strong>${lmsData.placeFlg === "1" ? "วางของ" : "หยิบของ"}</strong></div>
                </div>
            `;
            
            // Styling
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 20px;
                border-radius: 12px;
                color: white;
                z-index: 1000;
                opacity: 0;
                transition: all 0.3s ease-in-out;
                transform: translateX(100%);
                box-shadow: 0 6px 20px rgba(0,0,0,0.15);
                max-width: 380px;
                min-width: 300px;
                border-left: 4px solid rgba(255,255,255,0.3);
            `;
            
            // Colors based on type
            switch (type) {
                case 'success': 
                    notification.style.background = 'linear-gradient(135deg, #28a745, #20c997)'; 
                    break;
                case 'error': 
                    notification.style.background = 'linear-gradient(135deg, #dc3545, #e74c3c)'; 
                    break;
                case 'warning': 
                    notification.style.background = 'linear-gradient(135deg, #ffc107, #f39c12)';
                    notification.style.color = '#212529';
                    break;
                case 'info': 
                    notification.style.background = 'linear-gradient(135deg, #17a2b8, #3498db)'; 
                    break;
                default: 
                    notification.style.background = 'linear-gradient(135deg, #6c757d, #95a5a6)';
            }
            
            document.body.appendChild(notification);
            
            // Animate in
            setTimeout(() => {
                notification.style.opacity = '1';
                notification.style.transform = 'translateX(0)';
            }, 100);
            
            // Animate out and remove (longer duration for rich content)
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => notification.remove(), 300);
            }, 5000); // 5 seconds for rich notification
        }
        // 🔼 END OF ADDED FUNCTION 🔼

        function initializeShelfState() {
            if (!localStorage.getItem(GLOBAL_SHELF_STATE_KEY)) {
                const defaultState = [];
                // สร้างสถานะเริ่มต้นตาม SHELF_CONFIG
                for (let level = 1; level <= TOTAL_LEVELS; level++) {
                    const blocksInThisLevel = SHELF_CONFIG[level];
                    for (let block = 1; block <= blocksInThisLevel; block++) {
                        defaultState.push([level, block, 0]); // [level, block, hasItem]
                    }
                }
                localStorage.setItem(GLOBAL_SHELF_STATE_KEY, JSON.stringify(defaultState));
            }
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

        function getQueue() {
            return cleanInvalidJobs();
        }

        function createShelfGridStructure() {
            // เคลียร์ grid เก่าทิ้งเสมอ เพื่อให้สามารถสร้างใหม่ได้ตาม config ปัจจุบัน
            shelfGrid.innerHTML = '';
            
            // กำหนดขนาด shelf-frame แบบเดียวกันทั้งสองโหมด
            let shelfFrameWidth, shelfFrameHeight, cellHeight;
            // ใช้ขนาดเดียวกันทั้งโหมด full-shelf และ active job
            shelfFrameWidth = 500;
            shelfFrameHeight = 475;
            cellHeight = 90;
            
            // สร้าง Grid container หลัก
            shelfGrid.style.display = 'flex';
            shelfGrid.style.flexDirection = 'column';
            shelfGrid.style.gap = '14px'; // ลด gap ระหว่างชั้นเพื่อให้พอดีกับความสูง 475px
            shelfGrid.style.padding = '10px'; // ลด padding จาก 12px เป็น 10px
            shelfGrid.style.background = '#f8f9fa';
            shelfGrid.style.border = '1px solid #dee2e6';
            shelfGrid.style.width = '100%';
            shelfGrid.style.height = '100%';
            
            // คำนวณขนาดให้เหมาะสมกับ shelf-frame ตามโหมด
            const shelfFrameBorder = 16; // border รวม (8px × 2) 
            const shelfPadding = 20; // padding รวม (10px × 2)
            const availableWidth = shelfFrameWidth - shelfFrameBorder - shelfPadding;
            const gapSize = 4; // gap ระหว่าง cells
            
            // สร้างแต่ละ Level เป็น flexbox แยกกัน (เริ่มจากชั้นบนลงล่าง เพื่อให้ชั้น 1 อยู่ด้านล่าง)
            for (let level = TOTAL_LEVELS; level >= 1; level--) {
                const blocksInThisLevel = SHELF_CONFIG[level];
                
                // สร้าง container สำหรับแต่ละ level
                const levelContainer = document.createElement('div');
                levelContainer.className = 'shelf-level';
                levelContainer.style.display = 'flex';
                levelContainer.style.gap = `${gapSize}px`;
                levelContainer.style.height = `${cellHeight}px`;
                levelContainer.style.width = '100%';
                levelContainer.style.justifyContent = 'stretch'; // กระจายพื้นที่เต็มความกว้าง
                
                // สร้าง cells สำหรับ level นี้
                for (let block = 1; block <= blocksInThisLevel; block++) {
                    const cell = document.createElement('div');
                    cell.id = `cell-${level}-${block}`;
                    cell.className = 'shelf-cell';
                    cell.style.flex = '1'; // ให้ทุก cell มีขนาดเท่ากันและเต็มพื้นที่
                    cell.style.height = '100%';
                    cell.style.cursor = 'pointer';
                    cell.style.borderRadius = '4px';
                    cell.style.boxShadow = '0 1px 2px rgba(0,0,0,0.1)';
                    
                    // ไม่ใส่ minWidth หรือ maxWidth เพื่อให้ flex ทำงานเต็มที่
                    
                    // เพิ่ม click event สำหรับแสดง cell preview
                    cell.addEventListener('click', () => {
                        const lots = getLotsInCell(level, block);
                        const activeJob = getActiveJob();
                        const targetLotNo = activeJob ? activeJob.lot_no : null;
                        renderCellPreview({ level, block, lots, targetLotNo });
                    });
                    
                    levelContainer.appendChild(cell);
                }
                
                shelfGrid.appendChild(levelContainer);
            }
            
            console.log(`📐 Created flexible shelf grid: ${TOTAL_LEVELS} levels with configuration:`, SHELF_CONFIG);
            console.log(`📏 Shelf frame: ${shelfFrameWidth}×${shelfFrameHeight}px | Available width: ${availableWidth}px | Cell height: ${cellHeight}px | Gap: ${gapSize}px`);
        }

        function getActiveJob() {
            const activeJobData = localStorage.getItem(ACTIVE_JOB_KEY);
            
            if (!activeJobData || activeJobData === 'null') {
                return null;
            }
            
            try {
                const job = JSON.parse(activeJobData);
                return job;
            } catch (error) {
                console.error('❌ Error parsing active job:', error);
                localStorage.removeItem(ACTIVE_JOB_KEY);
                return null;
            }
        }

        function setActiveJob(job) {
            localStorage.setItem(ACTIVE_JOB_KEY, JSON.stringify(job));
        }

        // 🔽 FIX goBackToQueue FUNCTION 🔽
        function goBackToQueue() {
            const activeJob = getActiveJob();
            if (activeJob) {
                console.log(`📋 Returning job to queue: ${activeJob.lot_no} (ID: ${activeJob.jobId})`);
                
                // ใส่ job กลับเข้า queue
                const queue = getQueue();
                // ตรวจสอบว่า job ไม่ได้อยู่ใน queue แล้ว
                if (!queue.some(job => job.jobId === activeJob.jobId)) {
                    queue.push(activeJob);
                    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
                    console.log(`✅ Job ${activeJob.lot_no} returned to queue. Queue size: ${queue.length}`);
                }
            }
            
            // Clear persistent notifications when leaving Active Job view
            clearPersistentNotifications();
            
            localStorage.removeItem(ACTIVE_JOB_KEY);
            renderAll();
        }

        // 🔽 ADD NEW FUNCTIONS FOR MAIN-WITH-QUEUE MODE 🔽
        /**
         * กลับไปหน้า Main แต่ยังคง queue ไว้ (จากหน้า Queue Selection)
         */
        function goBackToMain() {
            console.log('🏠 Going back to main view with queue preserved');
            showMainWithQueue = true;
            stopAutoReturnTimer(); // หยุด timer เก่าถ้ามี
            startActivityDetection(); // เริ่มตรวจจับกิจกรรม
            startAutoReturnTimer(); // เริ่ม timer ใหม่
            renderAll();
        }

        /**
         * ไปหน้า Queue Selection (จากปุ่ม notification ในหน้า Main)
         */
        function goToQueueSelection() {
            console.log('📋 Going to queue selection view');
            showMainWithQueue = false;
            stopAutoReturnTimer();
            stopActivityDetection();
            renderAll();
        }

        /**
         * เริ่ม Auto Return Timer (7 วินาที)
         */
        function startAutoReturnTimer() {
            if (autoReturnTimer) {
                clearTimeout(autoReturnTimer);
            }
            
            console.log('⏱️ Starting auto-return timer (7 seconds)');
            autoReturnTimer = setTimeout(() => {
                console.log('🔄 Auto-returning to queue selection due to inactivity');
                const queue = getQueue();
                if (queue.length > 0) {
                    showMainWithQueue = false;
                    stopActivityDetection();
                    renderAll();
                    showNotification('Returned to queue due to inactivity', 'info');
                }
            }, 7000); // 7 seconds
        }

        /**
         * หยุด Auto Return Timer
         */
        function stopAutoReturnTimer() {
            if (autoReturnTimer) {
                clearTimeout(autoReturnTimer);
                autoReturnTimer = null;
                console.log('⏹️ Auto-return timer stopped');
            }
        }

        /**
         * Reset Auto Return Timer (เมื่อมีกิจกรรม)
         */
        function resetAutoReturnTimer() {
            if (showMainWithQueue && autoReturnTimer) {
                console.log('🔄 Resetting auto-return timer due to activity');
                startAutoReturnTimer(); // รีสตาร์ท timer
            }
        }

        /**
         * เริ่มตรวจจับกิจกรรมของผู้ใช้
         */
        function startActivityDetection() {
            if (activityDetectionActive) return;
            
            activityDetectionActive = true;
            console.log('👁️ Starting activity detection');
            
            // Event listeners สำหรับตรวจจับกิจกรรม
            const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
            
            activityEvents.forEach(event => {
                document.addEventListener(event, resetAutoReturnTimer, { passive: true });
            });
        }

        /**
         * หยุดตรวจจับกิจกรรมของผู้ใช้
         */
        function stopActivityDetection() {
            if (!activityDetectionActive) return;
            
            activityDetectionActive = false;
            console.log('🛑 Stopping activity detection');
            
            const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
            
            activityEvents.forEach(event => {
                document.removeEventListener(event, resetAutoReturnTimer, { passive: true });
            });
        }

        /**
         * อัปเดตปุ่ม Queue Notification และ Back to Queue
         */
        function updateQueueNotificationButton() {
            const queueBtn = document.getElementById('queueNotificationBtn');
            const queueCountBadge = document.getElementById('queueCountBadge');
            const backToQueueBtn = document.getElementById('backToQueueBtn');
            
            if (!queueBtn || !queueCountBadge) return;
            
            const queue = getQueue();
            const queueCount = queue.length;
            const activeJob = getActiveJob();
            
            // จัดการปุ่ม Queue Notification (แสดงในหน้า main เมื่อมี queue)
            if (showMainWithQueue && queueCount > 0) {
                queueBtn.style.display = 'flex';
                queueCountBadge.textContent = queueCount;
                
                // เพิ่ม pulse effect ถ้ามี queue มาก
                if (queueCount >= 3) {
                    queueBtn.classList.add('pulse');
                } else {
                    queueBtn.classList.remove('pulse');
                }
            } else {
                queueBtn.style.display = 'none';
                queueBtn.classList.remove('pulse');
            }
            
            // จัดการปุ่ม Back to Queue (แสดงเมื่อมี active job และไม่อยู่ใน mainView)
            if (backToQueueBtn) {
                if (activeJob && !showMainWithQueue) {
                    backToQueueBtn.style.display = 'block';
                } else {
                    backToQueueBtn.style.display = 'none';
                }
            }
        }
        // 🔼 END OF FIX 🔼

        // --- Global: Track which cells have been logged for lots (persist across renderShelfGrid calls) ---
        if (!window.__rfid_loggedCells) window.__rfid_loggedCells = new Set();
        function renderShelfGrid() {
            // Expect shelfState as array of {level, block, lots}
            const shelfState = JSON.parse(localStorage.getItem(GLOBAL_SHELF_STATE_KEY) || '[]');
            const activeJob = getActiveJob();
            
            console.log(`🔄 renderShelfGrid called with activeJob:`, activeJob);
            if (activeJob) {
                console.log(`🎯 Target position: L${activeJob.level}B${activeJob.block} for lot ${activeJob.lot_no}`);
            }

            // เตรียมตำแหน่ง error (ถ้ามี)
            let wrongLevel = null, wrongBlock = null;
            if (activeJob && activeJob.error && activeJob.errorType === 'WRONG_LOCATION' && activeJob.errorMessage) {
                const match = activeJob.errorMessage.match(/L(\d+)-B(\d+)/);
                if (match) {
                    wrongLevel = Number(match[1]);
                    wrongBlock = Number(match[2]);
                }
            }

            // Clear all cells first
            for (let level = 1; level <= TOTAL_LEVELS; level++) {
                const blocksInThisLevel = SHELF_CONFIG[level];
                for (let block = 1; block <= blocksInThisLevel; block++) {
                    const cellId = `cell-${level}-${block}`;
                    const cell = document.getElementById(cellId);
                    if (!cell) continue;
                    cell.className = 'shelf-cell';
                    cell.innerHTML = '';
                }
            }

            // Render stacked lots in each cell (bottom-to-top: index 0 = bottom)
            const loggedCells = window.__rfid_loggedCells;
            if (Array.isArray(shelfState)) {
                shelfState.forEach(cellData => {
                    let level, block, lots;
                    if (Array.isArray(cellData)) {
                        level = cellData[0];
                        block = cellData[1];
                        lots = cellData[2];
                    } else if (cellData && typeof cellData === 'object') {
                        ({ level, block, lots } = cellData);
                    } else {
                        console.warn('⚠️ Invalid cellData in shelfState:', cellData);
                        return;
                    }
                    if (!Array.isArray(lots)) lots = [];
                    // Debug: log lots in every cell (index 0 = bottom, last = top) แบบละเอียด
                    if (lots.length > 0) {
                        // คำนวณเปอร์เซ็นต์การใช้งานของ cell
                        const totalTrayInCell = lots.reduce((sum, lot) => sum + (parseInt(lot.tray_count) || 1), 0);
                        const maxCapacity = getCellCapacity(level, block); // ใช้ความจุจริงของ cell
                        const usagePercentage = Math.round((totalTrayInCell / maxCapacity) * 100);
                        
                        console.log(`🟫 [Grid] Lots in cell (Level: ${level}, Block: ${block}) [index 0 = bottom, last = top] - Usage: ${usagePercentage}% (${totalTrayInCell}/${maxCapacity}):`);
                        lots.forEach((lot, idx) => {
                            const lotTrayCount = parseInt(lot.tray_count) || 1;
                            const lotPercentage = Math.round((lotTrayCount / maxCapacity) * 100);
                            console.log(`   [${idx}] LotNo: ${lot.lot_no}, Tray: ${lot.tray_count}, ${lotPercentage}%`);
                        });
                        console.log(`   All lots:`, JSON.stringify(lots));
                    }
                    const cellId = `cell-${level}-${block}`;
                    const cell = document.getElementById(cellId);
                    if (!cell) return;

                    // --- Visual stacked lots (FIFO bottom-to-top: index 0 = bottom, last = top) ---
                    const safeLots = Array.isArray(lots) ? lots : [];
                    let totalTray = safeLots.reduce((sum, lot) => sum + (parseInt(lot.tray_count) || 1), 0);
                    totalTray = Math.max(totalTray, 1);
                    
                    // ปรับการคำนวณขนาดให้เหมาะสมกับ cell ที่เล็กลง
                    const maxCellHeight = 66; // ความสูงสูงสุดของ cell (70px - padding 4px)
                    
                    // Render lots in REVERSE order (last to first) เพื่อให้แสดงผลถูกต้อง
                    // เนื่องจาก flex-end จะแสดงจากล่างขึ้นบน การใส่จากท้ายไปหน้าจะทำให้ลำดับถูกต้อง
                    for (let idx = safeLots.length - 1; idx >= 0; idx--) {
                        const lot = safeLots[idx];
                        const lotDiv = document.createElement('div');
                        let isTarget = false;
                        if (activeJob && String(activeJob.level) === String(level) && String(activeJob.block) === String(block)) {
                            isTarget = (String(lot.lot_no) === String(activeJob.lot_no));
                        }
                        lotDiv.className = 'stacked-lot' + (isTarget ? ' target-lot' : '');
                        
                        // คำนวณความสูงตาม tray_count แบบสัดส่วนที่ชัดเจน
                        const trayCount = parseInt(lot.tray_count) || 1;
                        const maxCapacity = 24;
                        const maxCellHeight = 85; // ใช้ความสูงสูงสุดที่เหมาะสมกับ cell height 90px
                        const heightRatio = trayCount / maxCapacity;
                        const trayHeight = Math.max(heightRatio * maxCellHeight, 2); // ขั้นต่ำ 2px เพื่อให้เห็น
                        lotDiv.style.height = Math.round(trayHeight) + 'px';
                        
                        // เก็บข้อมูลใน title สำหรับ tooltip เท่านั้น
                        lotDiv.title = `Lot: ${lot.lot_no}, Tray: ${trayCount}, Height: ${Math.round(trayHeight)}px`;
                        
                        // ไม่ใส่ข้อความ (แสดงเป็นกล่องสีเทาเท่านั้น)
                        
                        cell.appendChild(lotDiv);
                    }

                    // เพิ่ม has-item class ถ้ามีของ
                    if (Array.isArray(lots) && lots.length > 0) {
                        cell.classList.add('has-item');
                    }
                });
            } else {
                console.error('❌ shelfState is not an array:', shelfState);
            }

            // --- Apply activeJob และ error state classes ให้ทุก cell หลังจาก render lots แล้ว ---
            console.log(`🔍 Checking activeJob:`, activeJob);
            if (activeJob) {
                console.log(`🔍 ActiveJob found - Target: L${activeJob.level}B${activeJob.block} for lot ${activeJob.lot_no}`);
                // ตรวจสอบทุก cell ในชั้นวาง
                for (let level = 1; level <= TOTAL_LEVELS; level++) {
                    const blocksInThisLevel = SHELF_CONFIG[level];
                    for (let block = 1; block <= blocksInThisLevel; block++) {
                        const cellId = `cell-${level}-${block}`;
                        const cell = document.getElementById(cellId);
                        if (!cell) continue;

                        const isTargetCell = (String(activeJob.level) === String(level) && String(activeJob.block) === String(block));
                        const isWrongCell = (wrongLevel === Number(level) && wrongBlock === Number(block));

                        // เพิ่ม selected-task class สำหรับ target cell
                        if (isTargetCell) {
                            cell.classList.add('selected-task');
                            console.log(`🎯 Added selected-task to L${level}B${block} (Cell ID: ${cellId})`);
                            console.log(`🎯 Cell classes after adding:`, cell.classList.toString());
                            
                            // Verify CSS styles are applied
                            const styles = window.getComputedStyle(cell);
                            console.log(`🎯 Background color:`, styles.backgroundColor);
                            console.log(`🎯 Border:`, styles.border);
                        }

                        // เพิ่ม wrong-location class สำหรับ wrong cell และลบ selected-task ออก
                        if (isWrongCell) {
                            cell.classList.add('wrong-location');
                            cell.classList.remove('selected-task');
                            console.log(`❌ Added wrong-location to L${level}B${block}`);
                        }
                    }
                }
            }
        }

        function renderActiveJob() {
    const activeJob = getActiveJob();
    const queue = getQueue();
    const cellPreviewContainer = document.getElementById('cellPreviewContainer');
    const mainContainer = document.querySelector('.main-container');

    if (activeJob) {
        // ถ้ามี active job, แสดง cell preview
        cellPreviewContainer.style.display = 'flex';
        mainContainer.classList.remove('full-shelf-mode');
    } else {
        // ถ้าไม่มี active job, ซ่อน cell preview และแสดง shelf ตรงกลาง
        cellPreviewContainer.style.display = 'none';
        mainContainer.classList.add('full-shelf-mode');
    }

    // สร้าง shelf grid ใหม่
    createShelfGridStructure();

    // Log clearly which lot is currently selected as active job, and lots in that cell
    if (activeJob) {
        const lotsInCell = getLotsInCell(activeJob.level, activeJob.block);
        console.log(`ActiveJobLot: ${activeJob.lot_no} (Level: ${activeJob.level}, Block: ${activeJob.block})`);
        console.log(`Lots in cell (${activeJob.level}, ${activeJob.block}):`, lotsInCell);

        // แสดง Cell Preview สำหรับ active job
        const isPlaceJob = activeJob.place_flg === '1';
        const actualTrayCount = parseInt(activeJob.tray_count) || 1; // ใช้ค่าจริงจาก activeJob
        renderCellPreview({
            level: activeJob.level,
            block: activeJob.block,
            lots: lotsInCell,
            targetLotNo: activeJob.lot_no,
            isPlaceJob: isPlaceJob,
            newLotTrayCount: isPlaceJob ? actualTrayCount : 0 // ใช้ค่าจริงแทนค่าคงที่ 12
        });
    } else {
        // ถ้าไม่มี active job ให้แสดงข้อความเริ่มต้น (ตอนนี้ถูกซ่อนอยู่ แต่เผื่อกลับมาใช้)
        const cellPreviewContent = document.getElementById('cellPreviewContent');
        if (cellPreviewContent) {
            cellPreviewContent.innerHTML = '<p>No active job. Select a job from the queue.</p>';
        }
    }

    renderShelfGrid();
}

        function renderQueueSelectionView(queue) {
            // ล้าง containers
            queueListContainer.innerHTML = '';
            
            // หา containers สำหรับแต่ละฝั่ง
            const placeContainer = document.getElementById('placeQueueContainer');
            const pickContainer = document.getElementById('pickQueueContainer');
            
            if (placeContainer) placeContainer.innerHTML = '';
            if (pickContainer) pickContainer.innerHTML = '';

            // แยกงานตาม place_flg
            const placeJobs = queue.filter(job => job.place_flg === '1'); // วาง
            const pickJobs = queue.filter(job => job.place_flg === '0');  // หยิบ

            // ฟังก์ชันสำหรับสร้าง job item
            function createJobItem(job) {
                const li = document.createElement('li');
                li.className = 'queue-list-item';
                
                // เลือก arrow ตาม place_flg เหมือนเดิม
                let arrowHtml = '';
                if (job.place_flg === '0') {
                    arrowHtml = `<span class="arrow up"></span>`;
                } else {
                    arrowHtml = `<span class="arrow down"></span>`;
                }
                
                li.innerHTML = `
                    <div class="info">
                        <div class="lot">${arrowHtml} ${job.lot_no}</div>
                        <div class="action">Action: ${job.place_flg === '1' ? 'Place' : 'Pick'} at L:${job.level}, B:${job.block}</div>
                    </div>
                    <button class="select-btn" onclick="selectJob('${job.jobId}')">Select</button>
                `;
                return li;
            }

            // เพิ่มงานวางในฝั่งซ้าย
            if (placeContainer) {
                placeJobs.forEach(job => {
                    placeContainer.appendChild(createJobItem(job));
                });
                
                // แสดงข้อความถ้าไม่มีงาน
                if (placeJobs.length === 0) {
                    const emptyMessage = document.createElement('li');
                    emptyMessage.innerHTML = '<div style="text-align: center; color: #6c757d; padding: 20px; font-style: italic;">No job placed</div>';
                    placeContainer.appendChild(emptyMessage);
                }
            }

            // เพิ่มงานหยิบในฝั่งขวา
            if (pickContainer) {
                pickJobs.forEach(job => {
                    pickContainer.appendChild(createJobItem(job));
                });
                
                // แสดงข้อความถ้าไม่มีงาน
                if (pickJobs.length === 0) {
                    const emptyMessage = document.createElement('li');
                    emptyMessage.innerHTML = '<div style="text-align: center; color: #6c757d; padding: 20px; font-style: italic;">No job picked</div>';
                    pickContainer.appendChild(emptyMessage);
                }
            }

            // Fallback: ใช้ container เดิมถ้าไม่มี container ใหม่
            if (!placeContainer || !pickContainer) {
                queue.forEach(job => {
                    const li = document.createElement('li');
                    li.className = 'queue-list-item';
                    // เลือก icon ตาม action
                    let arrowHtml = '';
                    if (job.place_flg === '0') {
                        arrowHtml = `<span class="arrow up"></span>`;
                    } else {
                        arrowHtml = `<span class="arrow down"></span>`;
                    }
                    li.innerHTML = `
                        <div class="info">
                            <div class="lot">${arrowHtml}Lot: ${job.lot_no}</div>
                            <div class="action">Action: ${job.place_flg === '1' ? 'Place' : 'Pick'} at L:${job.level}, B:${job.block}</div>
                        </div>
                        <button class="select-btn" onclick="selectJob('${job.jobId}')">Select</button>
                    `;
                    queueListContainer.appendChild(li);
                });
            }

            // Logic focus เดิม
            const lotInput = document.getElementById('lot-no-input');
            if (lotInput) {
                lotInput.focus();
                lotInput.onkeyup = function(event) {
                    if (event.key === 'Enter') {
                        handleLotSearch();
                    }
                };
            }
        }

        // --- START: ลบฟังก์ชันที่ไม่จำเป็นออก ---
        /*
        function ensureLotInputFocus() { ... }
        function setupLotInputBehavior(lotInput) { ... }
        function handleLotKeyUp(event) { ... }
        */
        // --- END: ลบฟังก์ชันที่ไม่จำเป็นออก ---

        function selectJob(jobId) {
            const queue = getQueue();
            const selectedJob = queue.find(job => job.jobId === jobId);
            
            if (selectedJob) {
                console.log(`📋 Selecting job: ${selectedJob.lot_no} (ID: ${jobId})`);
                
                // รีเซ็ตโหมด main-with-queue เมื่อเลือก job
                showMainWithQueue = false;
                stopAutoReturnTimer();
                stopActivityDetection();
                
                // ลบ job ที่เลือกออกจาก queue
                const updatedQueue = queue.filter(job => job.jobId !== jobId);
                localStorage.setItem(QUEUE_KEY, JSON.stringify(updatedQueue));
                
                // ตั้งเป็น active job
                setActiveJob(selectedJob);
                renderAll();
                
                console.log(`✅ Job ${selectedJob.lot_no} activated. Remaining queue size: ${updatedQueue.length}`);
            } else {
                console.error('❌ Job not found:', jobId);
            }
        }

        // --- START: คืนค่าฟังก์ชันให้เป็นแบบง่าย ---
        /**
         * ค้นหา Job จาก Lot No. แล้วทำการเลือกโดยอัตโนมัติ
         * @param {string} lotNo - The Lot No. to search for.
         */
        function findAndSelectJobByLot(lotNo) {
            if (!lotNo) return;

            // ตรวจสอบรูปแบบ LOT number ก่อนค้นหา
            if (!isValidLotNumberFormat(lotNo)) {
                showLotFormatWarningPopup(lotNo);
                return;
            }

            const queue = getQueue();
            const foundJob = queue.find(job => job.lot_no === lotNo);

            if (foundJob) {
                selectJob(foundJob.jobId);
                // รอให้ renderAll() เสร็จแล้วค่อยแสดง notification ที่จะติดยาว
                setTimeout(() => {
                    // ล้าง notification เก่าทั้งหมดก่อน (ยกเว้น persistent ที่มีอยู่แล้ว)
                    const existingNotifications = document.querySelectorAll('.notification:not(#persistent-correct-shelf)');
                    existingNotifications.forEach(n => n.remove());
                    
                    // ลบ persistent notification เก่าถ้ามี
                    const oldPersistent = document.getElementById('persistent-correct-shelf');
                    if (oldPersistent) oldPersistent.remove();
                    
                    // สร้าง notification แบบคงทนที่ไม่หายไป
                    const notification = document.createElement('div');
                    notification.className = 'notification success persistent';
                    notification.textContent = '✅ Correct shelf';
                    notification.id = 'persistent-correct-shelf';
                    
                    notification.style.cssText = `
                        position: fixed !important;
                        top: 20px !important;
                        right: 20px !important;
                        padding: 20px 25px !important;
                        border-radius: 8px !important;
                        color: white !important;
                        font-weight: 900 !important;
                        font-size: 18px !important;
                        z-index: 99999 !important;
                        background-color: #28a745 !important;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
                        max-width: 350px !important;
                        word-wrap: break-word !important;
                        opacity: 1 !important;
                        transform: translateX(0) !important;
                        transition: all 0.3s ease-in-out !important;
                        pointer-events: auto !important;
                    `;
                    
                    document.body.appendChild(notification);
                    console.log('✅ Persistent notification created with !important styles:', notification);
                    
                    // เพิ่มการป้องกันการลบ
                    notification.setAttribute('data-persistent', 'true');
                    
                    // เปิดใช้งานการป้องกัน
                    setTimeout(() => {
                        protectPersistentNotifications();
                    }, 100);
                    
                }, 800); // เพิ่ม delay เป็น 800ms
            } else {
                showNotification(`❌ Lot No. ${lotNo} not found in queue.`, 'error');
                const lotInput = document.getElementById('lot-no-input');
                if (lotInput) {
                    lotInput.classList.add('shake');
                    setTimeout(() => lotInput.classList.remove('shake'), 1000);
                }
            }
        }

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
         * แสดง popup ยืนยันการเปลี่ยน job
         */
        function showJobConfirmationPopup(currentJob, newJob, scannedLot) {
            const overlay = document.createElement('div');
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.6);
                z-index: 10000;
                display: flex;
                justify-content: center;
                align-items: center;
                animation: fadeIn 0.3s ease-in-out;
            `;

            const popup = document.createElement('div');
            popup.style.cssText = `
                background: linear-gradient(135deg, #17a2b8, #3498db);
                border: none;
                border-radius: 20px;
                padding: 40px;
                max-width: 650px;
                width: 90%;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideIn 0.4s ease-in-out;
                position: relative;
                overflow: hidden;
            `;

            popup.innerHTML = `
                <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
                <div style="font-size: 28px; font-weight: bold; color: white; margin-bottom: 15px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
                    Job Confirmation Required
                </div>
                <div style="font-size: 20px; color: white; margin-bottom: 25px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                    Current job: <strong>${currentJob.lot_no}</strong><br>
                    Scanned lot: <strong>${scannedLot}</strong>
                </div>
                <div style="font-size: 18px; color: white; margin-bottom: 30px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                    Is job <strong>${currentJob.lot_no}</strong> completed?
                </div>
                <div style="display: flex; gap: 20px; justify-content: center; margin-top: 30px;">
                    <button id="confirmYes" style="
                        padding: 15px 30px;
                        font-size: 18px;
                        font-weight: bold;
                        background: #28a745;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        cursor: pointer;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                        transition: all 0.2s;
                    ">✅ Yes, Complete</button>
                    <button id="confirmNo" style="
                        padding: 15px 30px;
                        font-size: 18px;
                        font-weight: bold;
                        background: #dc3545;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        cursor: pointer;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                        transition: all 0.2s;
                    ">❌ No, Continue</button>
                </div>
            `;

            overlay.appendChild(popup);
            document.body.appendChild(overlay);

            // เพิ่ม CSS animations
            const style = document.createElement('style');
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideIn {
                    from { transform: scale(0.7) translateY(-30px); opacity: 0; }
                    to { transform: scale(1) translateY(0); opacity: 1; }
                }
                @keyframes fadeOut {
                    from { opacity: 1; transform: scale(1); }
                    to { opacity: 0; transform: scale(0.8); }
                }
            `;
            document.head.appendChild(style);

            const closePopup = () => {
                overlay.style.animation = 'fadeOut 0.3s ease-in-out forwards';
                setTimeout(() => {
                    if (document.body.contains(overlay)) {
                        document.body.removeChild(overlay);
                    }
                    if (document.head.contains(style)) {
                        document.head.removeChild(style);
                    }
                }, 300);
            };

            // จัดการเมื่อกดปุ่ม Yes - Complete current job
            const yesBtn = popup.querySelector('#confirmYes');
            yesBtn.addEventListener('click', async () => {
                closePopup();
                console.log(`✅ User confirmed completion of job ${currentJob.lot_no}`);
                
                // แสดง loading notification
                showNotification(`🔄 Completing job ${currentJob.lot_no}...`, 'info');
                
                try {
                    // ส่งคำสั่ง complete ผ่าน HTTP API โดยตรง
                    const response = await fetch(`/command/${currentJob.jobId}/complete`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        console.log('✅ Job completed successfully:', data);
                        
                        // Clear persistent notifications และ active job
                        clearPersistentNotifications();
                        localStorage.removeItem(ACTIVE_JOB_KEY);
                        
                        // ดับไฟ LED
                        fetch('/api/led/clear', { method: 'POST' });
                        
                        // เลือก job ใหม่
                        selectJob(newJob.jobId);
                        showNotification(`✅ Job ${currentJob.lot_no} completed. Switched to ${scannedLot}`, 'success');
                        
                        // Render UI ใหม่
                        renderAll();
                    } else {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                } catch (error) {
                    console.error('❌ Error completing job:', error);
                    showNotification(`❌ Failed to complete job: ${error.message}`, 'error');
                    
                    // ถ้า complete ไม่สำเร็จ ให้เลือก job ใหม่แทน
                    selectJob(newJob.jobId);
                    showNotification(`⚠️ Switched to ${scannedLot} (previous job not completed)`, 'warning');
                }
            });

            // จัดการเมื่อกดปุ่ม No - Continue current job
            const noBtn = popup.querySelector('#confirmNo');
            noBtn.addEventListener('click', () => {
                closePopup();
                console.log(`❌ User chose to continue current job ${currentJob.lot_no}`);
                showNotification(`Continue working on ${currentJob.lot_no}`, 'info');
                
                // Focus กลับไปที่ barcode input
                const barcodeInput = document.getElementById('barcode-scanner-input');
                if (barcodeInput) {
                    setTimeout(() => barcodeInput.focus(), 100);
                }
            });

            // เพิ่ม hover effects
            yesBtn.addEventListener('mouseenter', () => {
                yesBtn.style.transform = 'translateY(-2px)';
                yesBtn.style.boxShadow = '0 6px 12px rgba(0,0,0,0.3)';
            });
            yesBtn.addEventListener('mouseleave', () => {
                yesBtn.style.transform = 'translateY(0)';
                yesBtn.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
            });

            noBtn.addEventListener('mouseenter', () => {
                noBtn.style.transform = 'translateY(-2px)';
                noBtn.style.boxShadow = '0 6px 12px rgba(0,0,0,0.3)';
            });
            noBtn.addEventListener('mouseleave', () => {
                noBtn.style.transform = 'translateY(0)';
                noBtn.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
            });

            // กด Escape เพื่อปิด (เหมือนกด No)
            const escapeHandler = (e) => {
                if (e.key === 'Escape') {
                    document.removeEventListener('keydown', escapeHandler);
                    noBtn.click();
                }
            };
            document.addEventListener('keydown', escapeHandler);
        }

        /**
         * แสดง popup เตือนรูปแบบ LOT number
         */
        function showLotFormatWarningPopup(invalidLotNo = '') {
            const overlay = document.createElement('div');
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.6);
                z-index: 10000;
                display: flex;
                justify-content: center;
                align-items: center;
                animation: fadeIn 0.3s ease-in-out;
            `;

            const popup = document.createElement('div');
            popup.style.cssText = `
                background: linear-gradient(135deg, #FF8C00, #FFA500, #FFD700);
                border: none;
                border-radius: 20px;
                padding: 40px;
                max-width: 600px;
                width: 90%;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideIn 0.4s ease-in-out;
                position: relative;
                overflow: hidden;
            `;

            // สร้าง progress bar
            const progressBar = document.createElement('div');
            progressBar.style.cssText = `
                position: absolute;
                bottom: 0;
                left: 0;
                height: 4px;
                background-color: rgba(255,255,255,0.8);
                width: 100%;
                transform-origin: left;
                animation: progressBarAnimation 3s linear forwards;
            `;

            // แสดงข้อความแตกต่างกันตาม LOT ที่ป้อน
            const displayLot = invalidLotNo || 'ABC123DEF.01';
            const titleText = invalidLotNo ? 'Invalid LOT Format' : 'LOT Not in Job Queue';
            const messageText = invalidLotNo 
                ? 'Please scan only Lot No. data (Format: xxxxxxxxx.xx)' 
                : `LOT ${displayLot} not found in current job queue`;

            popup.innerHTML = `
                <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
                <div style="font-size: 32px; font-weight: bold; color: white; margin-bottom: 15px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);">
                    ${titleText}
                </div>
                <div style="font-size: 22px; color: white; margin-bottom: 25px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                    ${messageText}
                </div>
                <div style="font-size: 18px; color: white; margin-bottom: 30px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">
                    This window will close in <span id="countdown">3</span> seconds
                </div>
            `;

            popup.appendChild(progressBar);

            overlay.appendChild(popup);
            document.body.appendChild(overlay);

            // เพิ่ม CSS animations
            const style = document.createElement('style');
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes slideIn {
                    from { transform: scale(0.7) translateY(-30px); opacity: 0; }
                    to { transform: scale(1) translateY(0); opacity: 1; }
                }
                @keyframes progressBarAnimation {
                    from { transform: scaleX(1); }
                    to { transform: scaleX(0); }
                }
                @keyframes fadeOut {
                    from { opacity: 1; transform: scale(1); }
                    to { opacity: 0; transform: scale(0.8); }
                }
            `;
            document.head.appendChild(style);

            // Countdown และ auto-close
            let countdown = 3;
            const countdownElement = popup.querySelector('#countdown');
            
            const closePopup = () => {
                // เพิ่ม animation ก่อนปิด
                overlay.style.animation = 'fadeOut 0.3s ease-in-out forwards';
                setTimeout(() => {
                    if (document.body.contains(overlay)) {
                        document.body.removeChild(overlay);
                    }
                    if (document.head.contains(style)) {
                        document.head.removeChild(style);
                    }
                    
                    // Focus กลับไปที่ input field
                    const lotInput = document.getElementById('lot-no-input');
                    if (lotInput) {
                        setTimeout(() => lotInput.focus(), 100);
                    }
                }, 300);
            };

            // เริ่ม countdown
            const countdownInterval = setInterval(() => {
                countdown--;
                if (countdownElement) {
                    countdownElement.textContent = countdown;
                }
                
                if (countdown <= 0) {
                    clearInterval(countdownInterval);
                    closePopup();
                }
            }, 1000);

            // Click เพื่อปิดก่อนเวลา
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    clearInterval(countdownInterval);
                    closePopup();
                }
            });

            // กด Escape เพื่อปิด
            const escapeHandler = (e) => {
                if (e.key === 'Escape') {
                    clearInterval(countdownInterval);
                    document.removeEventListener('keydown', escapeHandler);
                    closePopup();
                }
            };
            document.addEventListener('keydown', escapeHandler);
        }

        /**
         * ดึงค่าจากช่อง input แล้วส่งไปให้ฟังก์ชันค้นหา
         */
        function handleLotSearch() {
            const lotInput = document.getElementById('lot-no-input');
            if (lotInput) {
                const lotNoToSearch = lotInput.value.trim();
                
                if (lotNoToSearch.length > 0) {
                    // ตรวจสอบรูปแบบ LOT number ก่อน
                    if (!isValidLotNumberFormat(lotNoToSearch)) {
                        // แสดง popup เตือนรูปแบบ LOT พร้อมส่ง LOT ที่ไม่ถูกต้อง
                        showLotFormatWarningPopup(lotNoToSearch);
                        lotInput.value = ''; // เคลียร์ input
                        return;
                    }
                    
                    event?.stopPropagation();
                    event?.preventDefault();
                    
                    findAndSelectJobByLot(lotNoToSearch);
                    lotInput.value = '';
                }
            }
        }
        // --- END: คืนค่าฟังก์ชันให้เป็นแบบง่าย ---

        // 🔽 ADD BARCODE SCANNING FUNCTIONALITY 🔽
        /**
         * ตั้งค่าการทำงานของช่องสแกนบาร์โค้ดในหน้า Active Job
         */
        function setupBarcodeScanner() {
            const barcodeInput = document.getElementById('barcode-scanner-input');
            if (!barcodeInput) return;

            // ให้ focus ที่ช่องสแกนบาร์โค้ดเมื่อแสดงหน้า Active Job
            barcodeInput.focus();

            // จัดการเมื่อมีการสแกนบาร์โค้ด (Enter key)
            barcodeInput.onkeyup = function(event) {
                if (event.key === 'Enter') {
                    handleBarcodeScanned();
                }
            };

            // ให้ focus กลับมาที่ช่องสแกนเสมอ
            barcodeInput.onblur = function() {
                setTimeout(() => {
                    if (document.getElementById('mainView').style.display !== 'none') {
                        barcodeInput.focus();
                    }
                }, 100);
            };
        }

        /**
         * จัดการเมื่อมีการสแกนบาร์โค้ด
         */
        function handleBarcodeScanned() {
            const barcodeInput = document.getElementById('barcode-scanner-input');
            if (!barcodeInput) return;

            const scannedData = barcodeInput.value.trim();
            barcodeInput.value = '';

            if (!scannedData) return;

            console.log(`📱 Barcode scanned: ${scannedData}`);
            
            const activeJob = getActiveJob();
            if (!activeJob) {
                showNotification('❌ No active job to process barcode.', 'error');
                return;
            }

            // ตรวจสอบว่าเป็นการสแกน lot number ใหม่ที่อยู่ใน queue หรือไม่
            if (isValidLotNumberFormat(scannedData)) {
                const queue = getQueue();
                const queueJob = queue.find(job => job.lot_no === scannedData);
                
                if (queueJob && scannedData !== activeJob.lot_no) {
                    // แสดง popup ยืนยันการเปลี่ยน job
                    showJobConfirmationPopup(activeJob, queueJob, scannedData);
                    return;
                }
                
                // ถ้าสแกน lot เดียวกับ active job แต่เป็นการ confirm
                if (scannedData === activeJob.lot_no) {
                    showNotification(`✅ Confirmed current job: ${activeJob.lot_no}`, 'success');
                    return;
                }
            }

            const locationMatch = parseLocationFromBarcode(scannedData);
            
            if (!locationMatch) {
                showNotification(`❌ Invalid barcode format: ${scannedData}`, 'error');
                return;
            }

            const { level, block } = locationMatch;
            const correctLevel = Number(activeJob.level);
            const correctBlock = Number(activeJob.block);

            // ก่อนอัปเดต UI ให้ลบ class error เดิมออกจากทุก cell
            const allCells = document.querySelectorAll('.shelf-cell');
            allCells.forEach(cell => {
                cell.classList.remove('wrong-location');
                // ไม่ลบ selected-task ที่ cell เป้าหมาย
                const cellId = cell.id;
                if (cellId !== `cell-${correctLevel}-${correctBlock}`) {
                    cell.classList.remove('selected-task');
                }
            });

            if (Number(level) === correctLevel && Number(block) === correctBlock) {
                if (activeJob.error) {
                    const cleanJob = { ...activeJob };
                    delete cleanJob.error;
                    delete cleanJob.errorType;
                    delete cleanJob.errorMessage;
                    setActiveJob(cleanJob);
                    renderAll();
                }
                showNotification(`✅ Correct location! Completing job for Lot ${activeJob.lot_no}...`, 'success');
                completeCurrentJob();
            } else {
                // แสดง error UI ให้เหมือน LED: ช่องถูกต้อง (selected-task, ฟ้า), ช่องที่ผิด (wrong-location, แดง)
                //showNotification(`❌ Wrong location! Expected: L${correctLevel}-B${correctBlock}, Got: L${level}-B${block}`, 'error');

                // อัปเดต UI: ช่องถูกต้อง (selected-task)
                const correctCell = document.getElementById(`cell-${correctLevel}-${correctBlock}`);
                if (correctCell) {
                    correctCell.classList.add('selected-task');
                }
                // ช่องผิด (wrong-location)
                const wrongCell = document.getElementById(`cell-${level}-${block}`);
                if (wrongCell) {
                    wrongCell.classList.add('wrong-location');
                    wrongCell.classList.remove('selected-task');
                }
                // อัปเดต state error ใน activeJob
                reportJobError('WRONG_LOCATION', `Scanned wrong location: L${level}-B${block}, Expected: L${correctLevel}-B${correctBlock}`);
            }
        }

        /**
         * แยกข้อมูลตำแหน่งจากบาร์โค้ด
         * รูปแบบที่รองรับ: L1-B2, 1-2, L1B2, 1,2 เป็นต้น
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
                    const level = parseInt(match[1]);
                    const block = parseInt(match[2]);
                    
                    // ตรวจสอบว่า Level และ Block ที่สแกนมาอยู่ในช่วงที่ถูกต้องหรือไม่
                    if (level >= 1 && level <= TOTAL_LEVELS && 
                        block >= 1 && block <= SHELF_CONFIG[level]) {
                        return { level, block };
                    }
                }
            }

            return null;
        }

        /**
         * ส่งคำสั่ง Complete Job ไปยัง Server
         */
        function completeCurrentJob() {
            let activeJob = getActiveJob();
            if (!activeJob) {
                showNotification('❌ No active job to complete.', 'error');
                return;
            }

            // ตรวจสอบและเคลียร์ error state ถ้ามี
            if (activeJob.error) {
                activeJob = { ...activeJob };
                delete activeJob.error;
                delete activeJob.errorType;  
                delete activeJob.errorMessage;
                setActiveJob(activeJob);
            }

            console.log('🚀 Completing job:', activeJob.jobId, 'Lot:', activeJob.lot_no);
            console.log(`📝 Job details:`, {
                level: activeJob.level,
                block: activeJob.block,
                place_flg: activeJob.place_flg,
                biz: activeJob.biz,
                shelf_id: activeJob.shelf_id
            });
            console.log(`🎯 Target API endpoint: POST /command/${activeJob.jobId}/complete`);

            // Clear loggedCells so next render logs new state
            if (window.__rfid_loggedCells) window.__rfid_loggedCells.clear();

            // 🔄 ใช้ HTTP API เป็นหลักเพื่อความเสถียร (แทนที่ WebSocket)
            console.log('📤 Sending complete job request via HTTP API...');
            
            fetch(`/command/${activeJob.jobId}/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => {
                console.log('� Complete job response status:', response.status);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(async data => {
                console.log('✅ Job completed successfully via HTTP API:', data);
                
                if (data.status === 'success') {
                    // แสดง notification พร้อมรายละเอียด
                    const action = data.action || 'processed';
                    const location = data.location || `L${activeJob.level}B${activeJob.block}`;
                    showNotification(`✅ Job completed for Lot ${data.lot_no || activeJob.lot_no} - ${action} at ${location}!`, 'success');
                    
                    // Validate job completion
                    const isValid = await validateJobCompletion(activeJob.jobId, activeJob.lot_no);
                    if (isValid) {
                        console.log('🎯 Job completion validated successfully');
                    } else {
                        console.warn('⚠️ Job completion validation failed, but continuing...');
                    }
                    
                    // Clear active job
                    clearPersistentNotifications();
                    localStorage.removeItem(ACTIVE_JOB_KEY);
                    
                    // รีเฟรช shelf state จาก server
                    await refreshShelfStateFromServer();
                    renderAll();

                    // ดับไฟ LED หลังงานเสร็จ
                    fetch('/api/led/clear', { method: 'POST' });
                } else {
                    throw new Error(data.message || 'Job completion failed');
                }
            })
            .catch(error => {
                console.error('❌ Error completing job:', error);
                showNotification(`❌ Error completing job: ${error.message}. Please try again.`, 'error');
            });
        }

        /**
         * รีเฟรช shelf state จาก server หลังจาก complete job
         */
        async function refreshShelfStateFromServer() {
            try {
                console.log('🔄 Refreshing shelf state from server...');
                
                const response = await fetch('/api/shelf/state', {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json'
                    }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('📦 Updated shelf state from server:', data);
                    
                    // อัปเดต global shelf state
                    window.shelfState = data.shelf_state || [];
                    
                    // ลบ job ออกจาก queue ใน localStorage ด้วย
                    const currentQueue = getQueue();
                    const activeJob = getActiveJob();
                    if (activeJob) {
                        const updatedQueue = currentQueue.filter(job => job.jobId !== activeJob.jobId);
                        localStorage.setItem(QUEUE_KEY, JSON.stringify(updatedQueue));
                        console.log(`🗑️ Removed completed job ${activeJob.jobId} from local queue`);
                    }
                    
                    console.log('✅ Shelf state refreshed successfully');
                } else {
                    console.error('❌ Failed to refresh shelf state:', response.status);
                }
            } catch (error) {
                console.error('💥 Error refreshing shelf state:', error);
            }
        }

        /**
         * ตรวจสอบสถานะงานจาก backend เพื่อป้องกัน desync
         */
        async function validateJobCompletion(jobId, lotNo) {
            try {
                console.log(`🔍 Validating job completion: ${jobId} (${lotNo})`);
                
                // ตรวจสอบว่างานยังอยู่ใน backend queue หรือไม่
                const queueResponse = await fetch('/command', {
                    method: 'GET',
                    headers: { 'Accept': 'application/json' }
                });
                
                if (queueResponse.ok) {
                    const queueData = await queueResponse.json();
                    const jobStillExists = queueData.jobs.some(job => job.jobId === jobId);
                    
                    if (jobStillExists) {
                        console.warn(`⚠️ Job ${jobId} still exists in backend queue after completion`);
                        return false;
                    } else {
                        console.log(`✅ Job ${jobId} successfully removed from backend queue`);
                        return true;
                    }
                }
            } catch (error) {
                console.error('💥 Error validating job completion:', error);
                return false;
            }
        }

        /**
         * รายงานข้อผิดพลาดของงาน
         */
        function reportJobError(errorType, errorMessage) {
            const activeJob = getActiveJob();
            if (!activeJob) return;

            console.log(`🚨 Reporting job error: ${errorType}`);
            
            const errorJob = { ...activeJob, error: true, errorType, errorMessage };
            setActiveJob(errorJob);
            renderAll();

            if (websocketConnection && websocketConnection.readyState === WebSocket.OPEN) {
                const message = {
                    type: 'job_error',
                    payload: {
                        jobId: activeJob.jobId,
                        errorType,
                        errorMessage,
                        lot_no: activeJob.lot_no
                    }
                };
                websocketConnection.send(JSON.stringify(message));
            }
        }
        // 🔼 END OF BARCODE SCANNING FUNCTIONALITY 🔼

        function renderAll() {
            const queue = getQueue();
            const activeJob = getActiveJob();

            // อัปเดตปุ่ม Queue Notification
            updateQueueNotificationButton();

            // Logic สำหรับแสดงหน้าที่เหมาะสม
            if (showMainWithQueue) {
                // โหมด Main with Queue - แสดงหน้า Main แต่มี notification button
                console.log('🏠 Rendering Main view with queue notification');
                queueSelectionView.style.display = 'none';
                mainView.style.display = 'flex';
                renderActiveJob(); // แสดง shelf แบบ full mode
                renderShelfGrid();
            } else if (queue.length > 0 && !activeJob) {
                // แสดงหน้า Queue Selection
                console.log('📋 Rendering Queue Selection view');
                mainView.style.display = 'none';
                queueSelectionView.style.display = 'block';
                renderQueueSelectionView(queue);
                // controlLEDByQueue(); ปิดการควบคุม LED ในหน้า Queue
            } else if (activeJob) {
                // แสดงหน้า Active Job
                console.log('🎯 Rendering Active Job view');
                showMainWithQueue = false; // รีเซ็ต flag
                stopAutoReturnTimer(); // หยุด timer
                stopActivityDetection(); // หยุดตรวจจับกิจกรรม
                controlLEDByActiveJob();
                queueSelectionView.style.display = 'none';
                mainView.style.display = 'flex';
                renderActiveJob();
                renderShelfGrid();
                setupBarcodeScanner();
            } else {
                // ไม่มี queue และไม่มี active job - แสดงหน้า Main แบบปกติ
                console.log('🏠 Rendering Main view (no queue, no active job)');
                showMainWithQueue = false;
                stopAutoReturnTimer();
                stopActivityDetection();
                queueSelectionView.style.display = 'none';
                mainView.style.display = 'flex';
                renderActiveJob();
                renderShelfGrid();
            }
        }

        // --- Initial Load ---
        document.addEventListener('DOMContentLoaded', async () => {
            console.log('📄 DOM Content Loaded - เริ่มต้นระบบ');
            
            try {
                console.log('⏳ Loading shelf config...');
                await loadShelfConfig();
                console.log('✅ Shelf config loaded');
                
                console.log('⏳ Initializing shelf name...');
                await initializeShelfName(); // เพิ่มการดึงข้อมูล shelf name
                console.log('✅ Shelf name initialized');
                
                // 🔄 เพิ่มการดึงงานที่ค้างอยู่จาก Gateway หลังจากได้ shelf_id แล้ว
                console.log('🔄 เริ่มดึงงานที่ค้างอยู่จาก Gateway...');
                try {
                    const pendingResult = await loadPendingJobsFromGateway();
                    if (pendingResult && pendingResult.success) {
                        console.log(`✅ การดึงงานที่ค้างอยู่เสร็จสิ้น: เพิ่ม ${pendingResult.added}/${pendingResult.total} งาน`);
                        if (pendingResult.skipped > 0) {
                            console.log(`⚠️ ข้ามงานซ้ำ: ${pendingResult.skipped} งาน`);
                        }
                    } else {
                        console.log(`⚠️ การดึงงานที่ค้างอยู่ล้มเหลว: ${pendingResult?.error || 'Unknown error'}`);
                    }
                } catch (pendingError) {
                    console.error('💥 ข้อผิดพลาดในการดึงงานที่ค้างอยู่:', pendingError);
                    showNotification('❌ ไม่สามารถดึงงานที่ค้างอยู่ได้', 'error');
                }
                
                console.log('⏳ Initializing shelf state...');
                initializeShelfState();
                console.log('✅ Shelf state initialized');
                
                console.log('⏳ Setting up WebSocket...');
                setupWebSocket();
                console.log('✅ WebSocket setup completed');
                
                // Sync queue จาก backend เพื่อให้แน่ใจว่าข้อมูลตรงกัน
                console.log('⏳ Syncing queue from backend...');
                try {
                    const syncResult = await syncQueueFromBackend();
                    if (syncResult.success) {
                        console.log(`✅ Queue synced: ${syncResult.jobs.length} jobs`);
                    } else {
                        console.warn('⚠️ Queue sync failed:', syncResult.error);
                    }
                } catch (syncError) {
                    console.warn('⚠️ Could not sync queue on startup:', syncError);
                }
                
                // 🔽 RESTORE SHELF STATE FROM SERVER/GATEWAY 🔽
                console.log('⏳ Restoring shelf state from server/Gateway...');
                try {
                    const restoreResult = await restoreShelfStateFromServer();
                    if (restoreResult.success) {
                        console.log(`✅ Shelf state restored: ${restoreResult.positions_count} positions`);
                    } else {
                        console.warn('⚠️ Shelf state restore failed:', restoreResult.error);
                    }
                } catch (restoreError) {
                    console.warn('⚠️ Could not restore shelf state on startup:', restoreError);
                }
                
                console.log('⏳ Rendering all components...');
                renderAll();
                console.log('✅ Initial setup completed successfully');
                
            } catch (error) {
                console.error('💥 ข้อผิดพลาดในการเริ่มต้นระบบ:', error);
                showNotification('❌ เกิดข้อผิดพลาดในการเริ่มต้นระบบ', 'error');
            }
        });
        
        // ลบ Event Listener ของ 'storage' เก่าออก เพราะเราจะใช้ WebSocket แทน
        window.removeEventListener('storage', renderAll);

        // 🔽 EXPOSE FUNCTIONS TO GLOBAL SCOPE FOR HTML ONCLICK 🔽
        window.goBackToMain = goBackToMain;
        window.goToQueueSelection = goToQueueSelection;
        window.selectJob = selectJob;
        window.handleLotSearch = handleLotSearch;
        window.findAndSelectJobByLot = findAndSelectJobByLot;
        // 🔼 END OF EXPOSED FUNCTIONS 🔼
        
        // *** START: WebSocket Integration ***
        let websocketConnection = null; // เก็บ WebSocket connection

        function setupWebSocket() {
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            websocketConnection = ws;

            ws.onopen = function(event) {
                console.log("✅ WebSocket connected");
            };

            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);

                    switch (data.type) {
                        case "initial_state":
                            localStorage.setItem(QUEUE_KEY, JSON.stringify(data.payload.jobs));
                            localStorage.setItem(GLOBAL_SHELF_STATE_KEY, JSON.stringify(data.payload.shelf_state));
                            renderAll();
                            break;
                        case "new_job":
                            const queue = getQueue();
                            if (!queue.some(job => job.jobId === data.payload.jobId)) {
                                queue.push(data.payload);
                                localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
                                
                                // ถ้าอยู่ในโหมด main-with-queue ให้กลับไปหน้า queue เมื่อมี job ใหม่
                                if (showMainWithQueue) {
                                    console.log('📋 New job arrived, returning to queue selection');
                                    showMainWithQueue = false;
                                    stopAutoReturnTimer();
                                    stopActivityDetection();
                                }
                                
                                renderAll();
                                showNotification(`New Lot: ${data.payload.lot_no}`);
                            }
                            break;
                        case "jobs_reloaded":
                            console.log('🔄 Received jobs_reloaded message:', data.payload);
                            
                            // Sync queue จาก backend เพื่อให้แน่ใจว่าข้อมูลตรงกัน (async)
                            syncQueueFromBackend().then(syncResult => {
                                if (syncResult.success) {
                                    console.log('✅ Queue synced successfully');
                                    renderAll(); // อัปเดต UI หลัง sync
                                } else {
                                    console.warn('⚠️ Queue sync failed:', syncResult.error);
                                    renderAll(); // อัปเดต UI แม้ sync ล้มเหลว
                                }
                            }).catch(syncError => {
                                console.error('💥 Error during queue sync:', syncError);
                                renderAll(); // อัปเดต UI แม้เกิด error
                            });
                            
                            // แสดง notification ตามสถานการณ์
                            const payload = data.payload;
                            let notificationType = 'info';
                            if (payload.loaded_count > 0) {
                                notificationType = 'success';
                            } else if (payload.skipped_count > 0) {
                                notificationType = 'warning';
                            }
                            
                            showNotification(`🔄 ${payload.message}`, notificationType);
                            
                            // Debug log
                            console.log(`📊 Jobs status - Loaded: ${payload.loaded_count}, Skipped: ${payload.skipped_count}, Total Pending: ${payload.total_pending}, Queue Size: ${payload.total_queue_size}`);
                            break;
                        case "job_completed":
                            console.log('📦 Received job_completed message:', data.payload);
                            
                            // รับข้อมูลจาก Gateway แต่ไม่ต้องเช็ค job ID ให้ตรงกัน
                            // เพียงแค่ลบ active job และอัปเดต shelf state ตามข้อมูลที่ได้รับ
                            
                            let currentQueue = getQueue();
                            console.log(`📋 Queue before removal (size: ${currentQueue.length}):`, currentQueue.map(j => `${j.lot_no}(${j.jobId})`));
                            
                            currentQueue = currentQueue.filter(j => j.jobId !== data.payload.completedJobId);
                            console.log(`📋 Queue after removal (size: ${currentQueue.length}):`, currentQueue.map(j => `${j.lot_no}(${j.jobId})`));
                            
                            localStorage.setItem(QUEUE_KEY, JSON.stringify(currentQueue));
                            
                            // ตรวจสอบ shelf state ก่อนและหลังการอัปเดต
                            const oldShelfState = JSON.parse(localStorage.getItem(GLOBAL_SHELF_STATE_KEY) || '[]');
                            console.log('📦 Shelf state before update:', oldShelfState);
                            console.log('📦 New shelf state from server:', data.payload.shelf_state);
                            
            localStorage.setItem(GLOBAL_SHELF_STATE_KEY, JSON.stringify(data.payload.shelf_state));
            clearPersistentNotifications(); // Clear persistent notifications on job completion
            localStorage.removeItem(ACTIVE_JOB_KEY);
            renderAll();
            showNotification(`✅ Job completed for Lot ${data.payload.lot_no || 'Unknown'}!`, 'success');
            fetch('/api/led/clear', { method: 'POST' });
            
            // 🔽 AUTO-SYNC SHELF STATE AFTER JOB COMPLETION 🔽
            // ไม่ต้อง await เพื่อไม่ให้ block UI
            autoSyncAfterJobComplete({
                lot_no: data.payload.lot_no,
                action: data.payload.action,
                level: data.payload.level,
                block: data.payload.block
            }).catch(error => {
                console.error('❌ Auto-sync failed after job completion:', error);
            });
                            break;
                        case "job_warning":
                            console.log('⚠️ Received job warning:', data.payload);
                            showNotification(`⚠️ ${data.payload.message}`, 'warning');
                            
                            // ถ้า warning เป็น JOB_ALREADY_COMPLETED ให้ลบ active job และ render ใหม่
                            if (data.payload.warning === 'JOB_ALREADY_COMPLETED') {
                                localStorage.removeItem(ACTIVE_JOB_KEY);
                                renderAll();
                            }
                            break;
                        case "job_error":
                            localStorage.setItem(ACTIVE_JOB_KEY, JSON.stringify(data.payload)); // ใช้ Key ที่ถูกต้อง
                            renderAll();
                            showNotification(`❌ Lot ${data.payload.lot_no} Must place at L${data.payload.level}-B${data.payload.block}`, 'error');
                            break;
                        case "system_reset":
                            localStorage.clear();
                            initializeShelfState();
                            renderAll();
                            showNotification('System has been reset.', 'warning');
                            break;
                        case "job_canceled":
                            console.log('Job canceled :', data.payload);
                            
                            // ลบ active job ถ้า lot_no ตรงกัน
                            const activeJob = localStorage.getItem(ACTIVE_JOB_KEY);
                            if (activeJob) {
                                try {
                                    const activeJobData = JSON.parse(activeJob);
                                    if (activeJobData.lot_no === data.payload.lot_no) {
                                        localStorage.removeItem(ACTIVE_JOB_KEY);
                                        console.log(`Removed active job for lot ${data.payload.lot_no}`);
                                    }
                                } catch (e) {
                                    console.error('Error parsing active job:', e);
                                    localStorage.removeItem(ACTIVE_JOB_KEY); // Remove corrupted data
                                }
                            }
                            
                            // Sync queue จาก backend เพื่อให้แน่ใจว่า UI ตรงกับ backend
                            syncQueueFromBackend().then(() => {
                                // Render all components ใหม่หลังจาก sync เสร็จ
                                renderAll();
                            }).catch(error => {
                                console.error('Error syncing queue after job canceled:', error);
                                // Render ทันทีแม้ sync ไม่สำเร็จ
                                renderAll();
                            });
                            
                            // แสดง notification
                            showNotification(`🗑️ Job canceled for Lot ${data.payload.lot_no || 'Unknown'} by Gateway`, 'warning');
                            break;
                    }
                } catch (e) {
                    console.error("Error parsing message from server:", e);
                }
            };

            ws.onclose = function(event) {
                console.log("❌ WebSocket disconnected. Reconnecting in 3 seconds...");
                setTimeout(setupWebSocket, 3000);
            };

            ws.onerror = function(error) {
                console.error("💥 WebSocket error:", error);
            };
        }

        // ฟังก์ชันสำหรับอัปเดตขนาด cell 
        function updateCellSizes() {
            // ใช้ขนาดเดียวกันทั้งสองโหมด
            let cellHeight = 90;
            
            // อัปเดต level containers
            const levelContainers = document.querySelectorAll('.shelf-level');
            levelContainers.forEach(container => {
                container.style.height = `${cellHeight}px`;
            });
            
            // อัปเดตขนาดของ cell ทั้งหมด แต่เก็บ state classes ไว้
            const allCells = document.querySelectorAll('.shelf-cell');
            allCells.forEach(cell => {
                // เก็บ state classes ที่สำคัญไว้
                const hasItem = cell.classList.contains('has-item');
                const isSelectedTask = cell.classList.contains('selected-task');
                const isWrongLocation = cell.classList.contains('wrong-location');
                const hasHighlightError = cell.classList.contains('highlight-error');
                
                // cells ใช้ flex: 1 แล้ว ไม่ต้องกำหนดขนาดเฉพาะ
                
                // เพิ่ม state classes กลับคืน
                if (hasItem) cell.classList.add('has-item');
                if (isSelectedTask) cell.classList.add('selected-task');
                if (isWrongLocation) cell.classList.add('wrong-location');
                if (hasHighlightError) cell.classList.add('highlight-error');
            });
        }

        // เพิ่ม event listeners สำหรับ window resize และ full-shelf mode toggle
        window.addEventListener('resize', updateCellSizes);
        
        // ฟังการเปลี่ยนแปลง full-shelf mode
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    updateCellSizes();
                }
            });
        });
        
        // เฝ้าดู main-container สำหรับการเปลี่ยนแปลง class
        const mainContainerElement = document.querySelector('.main-container');
        if (mainContainerElement) {
            observer.observe(mainContainerElement, { attributes: true, attributeFilter: ['class'] });
        }

        /**
         * ฟังก์ชันควบคุม LED ตามสถานะ active job (logic อยู่ฝั่ง frontend)
         * สามารถปรับ mapping สี/สถานะได้ที่นี่
         */
        function controlLEDByActiveJob(wrongLocation = null) {
            const activeJob = getActiveJob();
            if (!activeJob) {
                console.log('💡 No active job - clearing LEDs');
                fetch('/api/led/clear', { method: 'POST' });
                return;
            }

            const level = Number(activeJob.level);
            const block = Number(activeJob.block);
            
            // ช่องเป้าหมาย: สีฟ้าสำหรับ target position
            let targetColor = { r: 0, g: 100, b: 255 }; // สีฟ้าชัดเจน
            if (activeJob.place_flg === '0') {
                targetColor = { r: 255, g: 165, b: 0 }; // สีส้มสำหรับ pick
            }

            console.log(`💡 LED Control: Active job L${level}B${block}, Place=${activeJob.place_flg}`);

            // ถ้าอยู่ใน error state และมี wrong location
            if (activeJob.error && activeJob.errorType === 'WRONG_LOCATION' && activeJob.errorMessage) {
                const match = activeJob.errorMessage.match(/L(\d+)-B(\d+)/);
                if (match) {
                    const wrongLevel = Number(match[1]);
                    const wrongBlock = Number(match[2]);
                    
                    console.log(`💡 LED Error Mode: Target L${level}B${block}, Wrong L${wrongLevel}B${wrongBlock}`);
                    
                    // ใช้ unified API สำหรับการจุดไฟหลายตำแหน่ง พร้อมการลบไฟก่อน
                    const positions = [
                        { position: `L${level}B${block}`, ...targetColor }, // ช่องเป้าหมาย (ฟ้า/ส้ม)
                        { position: `L${wrongLevel}B${wrongBlock}`, r: 255, g: 0, b: 0 } // ช่องผิด (แดง)
                    ];
                    
                    return fetch('/api/led', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            positions, 
                            clear_first: true 
                        })
                    });
                }
            }
            
            // โหมดปกติ - จุดไฟเฉพาะช่องเป้าหมาย พร้อมการลบไฟก่อน
            console.log(`💡 LED Normal Mode: Target L${level}B${block}`);
            return fetch('/api/led', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    position: `L${level}B${block}`, 
                    ...targetColor
                })
            })
                .then(response => {
                    if (!response.ok) {
                        console.error('💡 LED Control failed:', response.status);
                        return response.text().then(text => {
                            console.error('💡 LED Error details:', text);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data) {
                        console.log('💡 LED Control success:', data);
                    }
                })
                .catch(error => {
                    console.error('💡 LED Control error:', error);
                });
        }

          // 🔽 LMS Integration Functions 🔽
        
        /**
         * แสดง Location Popup สำหรับ LMS ตามรูปแบบที่กำหนด
         * @param {string} lotNo - หมายเลข Lot
         * @param {string} location - ตำแหน่งที่ต้องไป
         * @param {string} type - ประเภท popup (warning, error, success, info)
         * @param {number} duration - ระยะเวลาแสดง popup (milliseconds, 0 = ไม่ปิดอัตโนมัติ)
         */
        function showLMSLocationPopup(lotNo, location, type = 'warning', duration = 0) {
            // ลบ popup เก่าถ้ามี
            const existingPopup = document.getElementById('lmsLocationPopup');
            if (existingPopup) {
                existingPopup.remove();
            }

            // เพิ่ม CSS animations ถ้ายังไม่มี
            if (!document.getElementById('lmsLocationPopupStyles')) {
                const style = document.createElement('style');
                style.id = 'lmsLocationPopupStyles';
                style.textContent = `
                    @keyframes lmsLocationFadeIn {
                        from { opacity: 0; }
                        to { opacity: 1; }
                    }
                    @keyframes lmsLocationSlideInDown {
                        from {
                            transform: translateY(-50px);
                            opacity: 0;
                        }
                        to {
                            transform: translateY(0);
                            opacity: 1;
                        }
                    }
                    @keyframes lmsLocationPulse {
                        0% {
                            transform: scale(1);
                        }
                        50% {
                            transform: scale(1.05);
                        }
                        100% {
                            transform: scale(1);
                        }
                    }
                `;
                document.head.appendChild(style);
            }

            // สร้าง overlay
            const overlay = document.createElement('div');
            overlay.id = 'lmsLocationPopup';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.8);
                z-index: 10000;
                display: flex;
                justify-content: center;
                align-items: center;
                animation: lmsLocationFadeIn 0.3s ease-in-out;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            `;

            // กำหนดสีตาม type
            let backgroundColor, borderColor;
            switch (type) {
                case 'error':
                    backgroundColor = '#ff4757';
                    borderColor = '#ff3838';
                    break;
                case 'success':
                    backgroundColor = '#2ed573';
                    borderColor = '#1dd1a1';
                    break;
                case 'info':
                    backgroundColor = '#3742fa';
                    borderColor = '#2f3542';
                    break;
                default: // warning/default (orange like in image)
                    backgroundColor = '#ff6b35';
                    borderColor = '#e55a2b';
            }

            // สร้าง popup content
            const popup = document.createElement('div');
            popup.style.cssText = `
                background: ${backgroundColor};
                color: white;
                padding: 40px 50px;
                border-radius: 15px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
                max-width: 500px;
                width: 90%;
                text-align: center;
                position: relative;
                animation: lmsLocationSlideInDown 0.5s ease-out;
                border: 3px solid ${borderColor};
                font-weight: bold;
            `;

            // สร้าง Lot No.
            const lotElement = document.createElement('div');
            lotElement.textContent = `Lot No. ${lotNo}`;
            lotElement.style.cssText = `
                margin: 0 0 30px 0;
                font-size: 28px;
                font-weight: bold;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                line-height: 1.2;
            `;

            // สร้าง "GO TO:" label
            const goToLabel = document.createElement('div');
            goToLabel.textContent = 'GO TO:';
            goToLabel.style.cssText = `
                margin: 0 0 15px 0;
                font-size: 20px;
                font-weight: bold;
                opacity: 0.9;
            `;

            // สร้าง location
            const locationElement = document.createElement('div');
            locationElement.textContent = location;
            locationElement.style.cssText = `
                margin: 0 0 35px 0;
                font-size: 32px;
                font-weight: bold;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                line-height: 1.2;
                letter-spacing: 1px;
            `;

            // สร้างปุ่ม OK
            const okButton = document.createElement('button');
            okButton.textContent = 'OK';
            okButton.style.cssText = `
                background: rgba(255, 255, 255, 0.9);
                color: ${backgroundColor};
                border: none;
                padding: 12px 40px;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
                min-width: 120px;
            `;

            // เพิ่ม hover effect สำหรับปุ่ม OK
            okButton.addEventListener('mouseenter', () => {
                okButton.style.background = 'white';
                okButton.style.transform = 'translateY(-2px)';
                okButton.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.3)';
            });

            okButton.addEventListener('mouseleave', () => {
                okButton.style.background = 'rgba(255, 255, 255, 0.9)';
                okButton.style.transform = 'translateY(0)';
                okButton.style.boxShadow = '0 4px 15px rgba(0, 0, 0, 0.2)';
            });

            // Click event สำหรับปุ่ม OK
            okButton.addEventListener('click', () => {
                overlay.remove();
            });

            // ประกอบ popup
            popup.appendChild(lotElement);
            popup.appendChild(goToLabel);
            popup.appendChild(locationElement);
            popup.appendChild(okButton);

            overlay.appendChild(popup);
            document.body.appendChild(overlay);

            // Auto hide after duration (ถ้ากำหนด duration > 0)
            if (duration > 0) {
                setTimeout(() => {
                    if (overlay && overlay.parentNode) {
                        overlay.style.animation = 'lmsLocationFadeIn 0.3s ease-in-out reverse';
                        setTimeout(() => {
                            overlay.remove();
                        }, 300);
                    }
                }, duration);
            }

            // Click overlay to close
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    overlay.remove();
                }
            });

            // ESC to close
            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    overlay.remove();
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);

            // Focus ปุ่ม OK เพื่อให้สามารถกด Enter ได้
            setTimeout(() => {
                okButton.focus();
            }, 100);

            // Enter to close
            okButton.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    overlay.remove();
                }
            });
        }

        /**
         * แสดง Alert Popup สำหรับ LMS response (แบบเก่า)
         */
        function showLMSAlertPopup(title, message, details = null, type = 'warning', duration = 0) {
            // ลบ popup เก่าถ้ามี
            const existingPopup = document.getElementById('lmsAlertPopup');
            if (existingPopup) {
                existingPopup.remove();
            }

            // เพิ่ม CSS animations ถ้ายังไม่มี
            if (!document.getElementById('lmsPopupStyles')) {
                const style = document.createElement('style');
                style.id = 'lmsPopupStyles';
                style.textContent = `
                    @keyframes fadeIn {
                        from { opacity: 0; }
                        to { opacity: 1; }
                    }
                    @keyframes slideInDown {
                        from {
                            transform: translateY(-50px);
                            opacity: 0;
                        }
                        to {
                            transform: translateY(0);
                            opacity: 1;
                        }
                    }
                    @keyframes bounce {
                        0%, 20%, 50%, 80%, 100% {
                            transform: translateY(0);
                        }
                        40% {
                            transform: translateY(-10px);
                        }
                        60% {
                            transform: translateY(-5px);
                        }
                    }
                    @keyframes pulse {
                        0% {
                            box-shadow: 0 0 0 0 rgba(255, 87, 87, 0.7);
                        }
                        70% {
                            box-shadow: 0 0 0 20px rgba(255, 87, 87, 0);
                        }
                        100% {
                            box-shadow: 0 0 0 0 rgba(255, 87, 87, 0);
                        }
                    }
                `;
                document.head.appendChild(style);
            }

            // สร้าง overlay
            const overlay = document.createElement('div');
            overlay.id = 'lmsAlertPopup';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.8);
                z-index: 10000;
                display: flex;
                justify-content: center;
                align-items: center;
                animation: fadeIn 0.3s ease-in-out;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            `;

            // กำหนดสีตาม type
            let backgroundColor, borderColor, iconColor, icon;
            switch (type) {
                case 'error':
                    backgroundColor = 'linear-gradient(135deg, #ff4757, #ff3838)';
                    borderColor = '#ff4757';
                    iconColor = '#fff';
                    icon = '⚠️';
                    break;
                case 'success':
                    backgroundColor = 'linear-gradient(135deg, #ffa502, #ff6348)';
                    borderColor = '#ffa502';
                    //backgroundColor = 'linear-gradient(135deg, #2ed573, #1dd1a1)';
                    //borderColor = '#2ed573';
                    iconColor = '#fff';
                    icon = '✅';
                    break;
                case 'info':
                    backgroundColor = 'linear-gradient(135deg, #3742fa, #2f3542)';
                    borderColor = '#3742fa';
                    iconColor = '#fff';
                    icon = '🔍';
                    break;
                default: // warning
                    backgroundColor = 'linear-gradient(135deg, #ffa502, #ff6348)';
                    borderColor = '#ffa502';
                    iconColor = '#fff';
                    icon = '⚠️';
            }

            // สร้าง popup content
            const popup = document.createElement('div');
            popup.style.cssText = `
                background: ${backgroundColor};
                color: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 25px 80px rgba(0, 0, 0, 0.3);
                max-width: 600px;
                width: 90%;
                text-align: center;
                position: relative;
                animation: slideInDown 0.5s ease-out;
                border: 4px solid ${borderColor};
                ${type === 'error' ? 'animation: slideInDown 0.5s ease-out, pulse 2s infinite;' : ''}
            `;

            // สร้าง icon
            const iconElement = document.createElement('div');
            iconElement.innerHTML = icon;
            iconElement.style.cssText = `
                font-size: 80px;
                margin-bottom: 20px;
                animation: bounce 1s ease-in-out infinite;
                filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));
            `;

            // สร้าง title
            const titleElement = document.createElement('h2');
            titleElement.textContent = title;
            titleElement.style.cssText = `
                margin: 0 0 20px 0;
                font-size: 32px;
                font-weight: bold;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                line-height: 1.2;
            `;

            // สร้าง message
            const messageElement = document.createElement('p');
            messageElement.textContent = message;
            messageElement.style.cssText = `
                margin: 0 0 25px 0;
                font-size: 20px;
                line-height: 1.5;
                font-weight: 500;
            `;

            // สร้าง details ถ้ามี
            let detailsElement = null;
            if (details) {
                detailsElement = document.createElement('div');
                detailsElement.style.cssText = `
                    background-color: rgba(255, 255, 255, 0.2);
                    padding: 20px;
                    border-radius: 12px;
                    margin: 20px 0;
                    font-size: 16px;
                    line-height: 1.6;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                `;
                detailsElement.innerHTML = details;
            }

            // สร้าง countdown และ progress bar เฉพาะเมื่อ duration > 0
            let countdownElement = null;
            let progressBar = null;
            let progressFill = null;
            let countdownInterval = null;

            if (duration > 0) {
                // สร้าง countdown
                countdownElement = document.createElement('div');
                countdownElement.style.cssText = `
                    margin-top: 25px;
                    font-size: 14px;
                    opacity: 0.8;
                    font-weight: 500;
                `;
                
                let timeLeft = Math.floor(duration / 1000);
                countdownElement.textContent = `This window will close in ${timeLeft} second`;

                // สร้าง progress bar
                progressBar = document.createElement('div');
                progressBar.style.cssText = `
                    width: 100%;
                    height: 4px;
                    background-color: rgba(255, 255, 255, 0.3);
                    border-radius: 2px;
                    margin-top: 15px;
                    overflow: hidden;
                `;
                
                progressFill = document.createElement('div');
                progressFill.style.cssText = `
                    height: 100%;
                    background-color: rgba(255, 255, 255, 0.8);
                    width: 100%;
                    border-radius: 2px;
                    transition: width ${duration}ms linear;
                `;
                progressBar.appendChild(progressFill);
            } else {
                // เพิ่มข้อความสำหรับ manual close
                const manualCloseNote = document.createElement('div');
                manualCloseNote.style.cssText = `
                    margin-top: 25px;
                    font-size: 14px;
                    opacity: 0.8;
                    font-weight: 500;
                `;
                manualCloseNote.textContent = 'กด ESC หรือคลิกด้านนอกเพื่อปิด';
                countdownElement = manualCloseNote;
            }

            // ประกอบ popup
            popup.appendChild(iconElement);
            popup.appendChild(titleElement);
            popup.appendChild(messageElement);
            if (detailsElement) popup.appendChild(detailsElement);
            if (countdownElement) popup.appendChild(countdownElement);
            if (progressBar) popup.appendChild(progressBar);

            overlay.appendChild(popup);
            document.body.appendChild(overlay);

            // เริ่ม countdown และ progress bar เฉพาะเมื่อ duration > 0
            if (duration > 0 && progressFill) {
                setTimeout(() => {
                    progressFill.style.width = '0%';
                }, 100);

                countdownInterval = setInterval(() => {
                    let timeLeft = Math.floor((duration - (Date.now() - startTime)) / 1000);
                    if (timeLeft < 0) timeLeft = 0;
                    countdownElement.textContent = `This window will close in ${timeLeft} seconds`;

                    if (timeLeft <= 0) {
                        clearInterval(countdownInterval);
                    }
                }, 1000);

                const startTime = Date.now();
            }

            // Auto hide after duration (เฉพาะเมื่อ duration > 0)
            if (duration > 0) {
                setTimeout(() => {
                    if (overlay && overlay.parentNode) {
                        overlay.style.animation = 'fadeIn 0.3s ease-in-out reverse';
                        setTimeout(() => {
                            overlay.remove();
                        }, 300);
                    }
                    if (countdownInterval) clearInterval(countdownInterval);
                }, duration);
            }

            // Click to close
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    if (countdownInterval) clearInterval(countdownInterval);
                    overlay.remove();
                }
            });

            // ESC to close
            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    if (countdownInterval) clearInterval(countdownInterval);
                    overlay.remove();
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);
        }

        /**
         * จัดการเมื่อ scan LOT ที่ไม่อยู่ในคิว (Auto LMS check - No confirmation)
         * @param {string} scannedLot - หมายเลข LOT ที่ scan
         */
        async function handleUnknownLotScanned(scannedLot) {
            if (!scannedLot) return;

            console.log(`🔍 Processing unknown LOT: ${scannedLot}`);
            
            // ตรวจสอบว่า LOT อยู่ในคิวหรือไม่
            const queue = getQueue();
            const lotInQueue = queue.find(job => job.lot_no === scannedLot);
            
            if (lotInQueue) {
                showNotification(`✅ พบ LOT ${scannedLot} ในคิว - กำลังเลือก...`, 'success');
                findAndSelectJobByLot(scannedLot);
                return;
            }

            // ถ้าไม่อยู่ในคิว ให้แสดง popup แจ้งเตือนก่อน
            showLMSAlertPopup(
                '⚠️ LOT Not in Job Queue',
                `LOT ${scannedLot} not found in current job queue`,
                null,
                'warning',
                3000
            );

            // สมมติว่าเป็นงานวาง (place_flg = "1") - สามารถปรับได้ตามความต้องการ
            const placeFlg = "1";
            
            // รอ 1 วินาทีแล้วค่อยเรียก LMS
            setTimeout(async () => {
                const lmsResult = await checkShelfFromLMS(scannedLot, placeFlg);
                
                if (lmsResult && lmsResult.success) {
                    console.log('📊 LMS Result:', lmsResult);
                    // LMS popup จะแสดงใน checkShelfFromLMS แล้ว
                    
                    // สามารถเพิ่มการทำงานอื่นๆ ได้ที่นี่ เช่น สร้าง job ใหม่
                } else if (lmsResult && !lmsResult.success) {
                    // Error popup จะแสดงใน checkShelfFromLMS แล้ว
                    console.log('❌ LMS Error:', lmsResult);
                }
            }, 1000);
        }

        /**
         * Integration กับ barcode scanner ที่มีอยู่
         * ปรับปรุงฟังก์ชัน findAndSelectJobByLot ให้รองรับ LMS
         */
        const originalFindAndSelectJobByLot = findAndSelectJobByLot;
        
        window.findAndSelectJobByLot = function(lotNo) {
            if (!lotNo) return;

            const queue = getQueue();
            const foundJob = queue.find(job => job.lot_no === lotNo);

            if (foundJob) {
                // ใช้ฟังก์ชันเดิม
                originalFindAndSelectJobByLot(lotNo);
            } else {
                // เรียก LMS integration
                handleUnknownLotScanned(lotNo);
            }
        };

        /**
         * เรียก LMS API เพื่อตรวจสอบชั้นวางที่ถูกต้องสำหรับ LOT ที่ไม่อยู่ในคิว
         * @param {string} lotNo - หมายเลข LOT
         * @param {string} placeFlg - ประเภทงาน ("0" = หยิบ, "1" = วาง)
         */
        async function checkShelfFromLMS(lotNo, placeFlg) {
            if (!lotNo) {
                showLMSAlertPopup(
                    '❌ Incomplete Data',
                    'Please specify LOT number',
                    null,
                    'error',
                    0
                );
                return null;
            }

            try {
                // แสดง loading popup
                showNotification(`🔍 Checking LOT ${lotNo} from LMS...`, 'info');
                
                const response = await fetch('/api/shelf/askCorrectShelf', {  // api/shelf/askCorrectShelf → Gateway → LMS
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        lot_no: lotNo
                    })
                });

                console.log('📡 LMS API Response Status:', response.status);
                const result = await response.json();
                console.log('📋 LMS API Response Data:', result);

                if (response.ok && result.status === 'success') {
                    // รองรับทั้ง correct_shelf_name และ correct_shelf
                    const correctShelf = result.correct_shelf_name || result.correct_shelf || 'UNKNOWN';
                    
                    console.log('✅ LMS Success - Shelf:', correctShelf);
                    
                    // Success - แสดง location popup แบบใหม่
                    showLMSLocationPopup(result.lot_no, correctShelf, 'warning', 0);
                    
                    return {
                        success: true,
                        correctShelf: correctShelf,
                        lotNo: result.lot_no
                    };
                } else {
                    console.error('❌ LMS API Error:', result);
                    
                    // Error popup
                    showLMSAlertPopup(
                        '❌ Not found in LMS',
                        result.message || `LOT ${lotNo} is not in the system`,
                        `Status: ${result.status || 'unknown'}<br>Code: ${result.code || 'N/A'}`,
                        'error',
                        5000
                    );
                    
                    return {
                        success: false,
                        error: result.error || 'Unknown error',
                        message: result.message || 'No message provided'
                    };
                }

            } catch (error) {
                console.error('LMS API Error:', error);
                
                // Network error popup - แก้ไข parameter order
                showLMSAlertPopup(
                    '🚫 Connection Error',
                    'Cannot connect to LMS system',
                    null,
                    'error',
                    5000
                );
                
                return {
                    success: false,
                    error: 'NETWORK_ERROR',
                    message: error.message
                };
            }
        }
// --- Function สำหรับดึงข้อมูล shelf name จาก Gateway API ---
async function initializeShelfName() {
    console.log('🏷️ กำลังดึงข้อมูล shelf name และ shelf_id จาก Gateway...');
    
    try {
        const response = await fetch('/ShelfName', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log('📋 ข้อมูล Shelf:', data);
            
            // เก็บ shelf_id ใน global variable
            if (data.shelf_id) {
                shelf_id = data.shelf_id;
                console.log(`💾 เก็บ shelf_id: ${shelf_id}`);
            } else {
                console.warn('⚠️ ไม่ได้รับ shelf_id จาก Gateway');
            }
            
            if (data.success && data.shelf_name) {
                // แปลงชื่อเป็นตัวพิมพ์ใหญ่
                const shelfDisplayName = data.shelf_name.toUpperCase();
                
                // อัพเดทชื่อใน UI
                const shelfTitle = document.getElementById('shelfTitle');
                if (shelfTitle) {
                    shelfTitle.textContent = shelfDisplayName;
                    console.log(`✅ อัพเดทชื่อ Shelf เป็น: ${shelfDisplayName}`);
                } else {
                    console.warn('⚠️ ไม่พบ element #shelfTitle');
                }
            } else {
                console.warn('⚠️ ไม่ได้รับ shelf_name จาก Gateway');
                console.log('📄 Response data:', data);
            }
        } else {
            console.error('❌ Error response:', response.status);
        }
    } catch (error) {
        console.error('💥 เกิดข้อผิดพลาดในการดึงข้อมูล shelf name:', error);
    }
}

// ทำให้ function เป็น global เพื่อเรียกจาก console ได้
window.initializeShelfName = initializeShelfName;

// --- Function สำหรับดึงงานที่ค้างอยู่จาก Gateway (ใช้ API endpoint ใหม่) ---
async function loadPendingJobsFromGateway() {
    console.log('🔄 กำลังดึงงานที่ค้างอยู่จาก Gateway ผ่าน API...');
    console.log('📍 Current shelf_id:', shelf_id);
    console.log('📍 Function called at:', new Date().toISOString());
    
    // ตรวจสอบ flag เพื่อป้องกันการเรียกซ้ำ
    if (pendingJobsLoaded) {
        console.log('⚠️ งานที่ค้างอยู่ถูกโหลดไปแล้ว, ข้ามการโหลดซ้ำ');
        return {
            success: true,
            error: 'Already loaded',
            added: 0,
            skipped: 0,
            total: 0
        };
    }
    
    if (!shelf_id) {
        console.warn('⚠️ ไม่มี shelf_id สำหรับดึงงาน');
        return { success: false, error: 'No shelf_id available' };
    }
    
    try {
        console.log('📤 ส่งคำขอไปยัง: POST /api/shelf/pending/load');
        
        // เรียก API endpoint ใหม่ที่จัดการทุกอย่างให้
        const response = await fetch('/api/shelf/pending/load', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });
        
        console.log('📥 ได้รับ response:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('📦 API Response:', result);
        
        if (result.status === 'success') {
            const loadedCount = result.loaded_count || 0;
            const skippedCount = result.skipped_count || 0;
            const totalPending = result.total_pending || 0;
            
            if (loadedCount > 0) {
                console.log(`🎯 เพิ่มงานที่ค้างอยู่ ${loadedCount} งาน เข้าสู่ queue`);
                console.log(`⚠️ ข้ามงานซ้ำ ${skippedCount} งาน`);
                
                // แสดง notification
                showNotification(
                    `🔄 กู้คืนงานที่ค้างอยู่ ${loadedCount} งานจาก Gateway สำเร็จ${skippedCount > 0 ? ` (ข้ามงานซ้ำ ${skippedCount} งาน)` : ''}`,
                    'success'
                );
                
                // รีเฟรช UI (เนื่องจาก API ส่ง WebSocket broadcast แล้ว)
                renderAll();
                
                // ตั้ง flag ว่าโหลดแล้ว
                pendingJobsLoaded = true;
                return { success: true, added: loadedCount, skipped: skippedCount, total: totalPending };
            } else {
                console.log('ℹ️ ไม่มีงานใหม่ที่ต้องเพิ่ม');
                if (totalPending > 0) {
                    console.log(`ℹ️ งานทั้งหมด ${totalPending} งานมีอยู่ใน queue แล้ว`);
                }
                // ตั้ง flag ว่าโหลดแล้ว (แม้จะไม่มีงานใหม่)
                pendingJobsLoaded = true;
                return { success: true, added: 0, skipped: skippedCount, total: totalPending };
            }
        } else {
            throw new Error(result.message || 'Unknown API error');
        }
        
    } catch (error) {
        console.error('💥 เกิดข้อผิดพลาดในการดึงงานที่ค้างอยู่:', error);
        showNotification(
            `❌ ไม่สามารถดึงงานที่ค้างอยู่จาก Gateway ได้: ${error.message}`,
            'error'
        );
        
        return { success: false, error: error.message };
    }
}

// ฟังก์ชันสำหรับ sync queue จาก backend
async function syncQueueFromBackend() {
    try {
        console.log('🔄 Syncing queue from backend...');
        
        const response = await fetch('/command', {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            const backendJobs = data.jobs || [];
            
            console.log(`📦 Backend has ${backendJobs.length} jobs:`, backendJobs.map(j => `${j.lot_no}(${j.jobId})`));
            
            // อัปเดต localStorage ให้ตรงกับ backend
            localStorage.setItem(QUEUE_KEY, JSON.stringify(backendJobs));
            
            // ล้าง active job ถ้าไม่มีในคิว backend
            const activeJob = getActiveJob();
            if (activeJob && !backendJobs.some(job => job.jobId === activeJob.jobId)) {
                console.log(`🧹 Clearing orphaned active job: ${activeJob.jobId}`);
                clearActiveJob();
            }
            
            console.log(`✅ Queue synced: ${backendJobs.length} jobs`);
            return { success: true, jobs: backendJobs };
        } else {
            console.error('❌ Failed to sync queue from backend:', response.status);
            return { success: false, error: `HTTP ${response.status}` };
        }
    } catch (error) {
        console.error('💥 Error syncing queue from backend:', error);
        return { success: false, error: error.message };
    }
}

// --- Shelf State Management Functions ---

/**
 * กู้คืน shelf state จาก server ผ่าน API endpoint
 * ใช้เมื่อเริ่มต้นระบบหรือต้องการ sync กับ Gateway
 */
async function restoreShelfStateFromServer() {
    try {
        console.log('🔄 Restoring shelf state from server...');
        
        // ดึง shelf_id จาก server
        const shelfInfoResponse = await fetch('/ShelfName');
        if (!shelfInfoResponse.ok) {
            throw new Error('Failed to get shelf info');
        }
        
        const shelfInfo = await shelfInfoResponse.json();
        const shelf_id = shelfInfo.shelf_id;
        
        if (!shelf_id || shelf_id === 'ERROR') {
            throw new Error('Invalid shelf_id from server');
        }
        
        // เรียก API เพื่อ restore shelf state
        const response = await fetch('/api/shelf/shelfItem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                shelf_id: shelf_id,
                update_flg: "0", // เปลี่ยนจาก update เป็น update_flg 
                shelf_state: [] // empty array for read
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('📦 Shelf state restored:', result);
        
        // Gateway ส่งข้อมูลมาใน result.data หรือ result.shelf_state
        const serverState = result.shelf_state || result.data;
        
        if (result.status === 'success' && serverState) {
            let finalState = [];
            
            // ตรวจสอบว่าเป็น array หรือไม่
            if (Array.isArray(serverState)) {
                // ข้อมูลจาก Gateway มาในรูป array แล้ว [{level: 1, block: 1, lots: [...]}]
                finalState = serverState;
                console.log('📦 Using array format from Gateway:', finalState);
            } else if (typeof serverState === 'object') {
                // ถ้าเป็น object ให้แปลงเป็น array
                finalState = [];
                for (const [positionKey, positionData] of Object.entries(serverState)) {
                    if (positionData.level && positionData.block) {
                        finalState.push({
                            level: positionData.level,
                            block: positionData.block,
                            lots: positionData.lots || []
                        });
                    }
                }
                console.log('📦 Converted object to array format:', finalState);
            }
            
            // บันทึกลง localStorage
            localStorage.setItem(GLOBAL_SHELF_STATE_KEY, JSON.stringify(finalState));
            
            console.log(`✅ Shelf state restored: ${finalState.length} positions updated`);
            
            // Re-render UI
            renderAll();
            
            return {
                success: true,
                positions_count: finalState.length,
                message: 'Shelf state restored successfully'
            };
        } else {
            throw new Error('Invalid response format from server');
        }
        
    } catch (error) {
        console.error('❌ Failed to restore shelf state:', error);
        showNotification(`⚠️ Failed to restore shelf state: ${error.message}`, 'warning');
        
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * ส่ง current shelf state ไปบันทึกที่ server/Gateway
 * ใช้เมื่อมีการเปลี่ยนแปลง state ที่ต้องการ sync
 */
async function syncShelfStateToServer() {
    try {
        console.log('🔄 Syncing shelf state to server...');
        
        // ดึง current state จาก localStorage
        const currentState = JSON.parse(localStorage.getItem(GLOBAL_SHELF_STATE_KEY) || '[]');
        
        if (currentState.length === 0) {
            throw new Error('No shelf state data to sync');
        }
        
        // ดึง shelf_id
        const shelfInfoResponse = await fetch('/ShelfName');
        if (!shelfInfoResponse.ok) {
            throw new Error('Failed to get shelf info');
        }
        
        const shelfInfo = await shelfInfoResponse.json();
        const shelf_id = shelfInfo.shelf_id;
        
        if (!shelf_id || shelf_id === 'ERROR') {
            throw new Error('Invalid shelf_id from server');
        }
        
        // ส่งข้อมูลในรูป array format ตรงๆ (ไม่ต้องแปลง)
        // currentState อยู่ในรูป [{level: 1, block: 1, lots: [...]}] อยู่แล้ว
        // ส่งเฉพาะ position ที่มีของ
        const arrayFormat = currentState.filter(position => position.lots && position.lots.length > 0);
        
        console.log('📦 Sending shelf state array:', arrayFormat);
        
        // ส่งไป server
        const response = await fetch('/api/shelf/shelfItem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                shelf_id: shelf_id,
                update_flg: "1", // เปลี่ยนจาก update เป็น update_flg
                shelf_state: arrayFormat
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('📡 Shelf state sync result:', result);
        
        if (result.status === 'success') {
            console.log(`✅ Shelf state synced successfully. Gateway sync: ${result.gateway_sync ? '✅' : '❌'}`);
            
            return {
                success: true,
                gateway_sync: result.gateway_sync,
                message: 'Shelf state synced successfully'
            };
        } else {
            throw new Error(result.message || 'Sync failed');
        }
        
    } catch (error) {
        console.error('❌ Failed to sync shelf state:', error);
        showNotification(`⚠️ Failed to sync shelf state: ${error.message}`, 'warning');
        
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Auto-sync shelf state หลังจาก job completion
 * เรียกโดย WebSocket หรือ manual trigger
 */
async function autoSyncAfterJobComplete(completedJobData = null) {
    try {
        console.log('🔄 Auto-syncing shelf state after job completion...');
        
        if (completedJobData) {
            console.log(`📋 Job completed: ${completedJobData.lot_no} (${completedJobData.action})`);
        }
        
        // รอสักครู่ให้ local state อัปเดตเสร็จก่อน
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Sync to server/Gateway
        const syncResult = await syncShelfStateToServer();
        
        if (syncResult.success) {
            showNotification(
                `✅ Shelf state synced ${syncResult.gateway_sync ? 'to Gateway' : 'locally'}`, 
                'success'
            );
        }
        
        return syncResult;
        
    } catch (error) {
        console.error('❌ Auto-sync failed:', error);
        return { success: false, error: error.message };
    }
}

/**
 * ดึงข้อมูลความจุและสถานะการใช้งานของช่องเฉพาะ
 */
async function getCellCapacityInfo(level, block) {
    try {
        const response = await fetch(`/api/shelf/capacity/${level}/${block}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log(`📏 Cell L${level}B${block} capacity info:`, result);
        return result;
        
    } catch (error) {
        console.error(`❌ Failed to get capacity info for L${level}B${block}:`, error);
        // Fallback to local calculation
        const capacity = getCellCapacity(level, block);
        const lots = getLotsInCell(level, block);
        const currentTray = lots.reduce((sum, lot) => sum + (lot.tray_count || 1), 0);
        
        return {
            level: level,
            block: block,
            max_capacity: capacity,
            current_tray: currentTray,
            available_space: capacity - currentTray,
            usage_percentage: Math.round((currentTray / capacity) * 100),
            is_full: currentTray >= capacity,
            error: error.message
        };
    }
}

/**
 * อัปเดตความจุทุกช่องจาก Backend
 */
async function refreshCellCapacities() {
    try {
        console.log('🔄 Refreshing cell capacities from Backend...');
        await loadShelfConfig(); // โหลด config ใหม่ซึ่งรวมความจุด้วย
        console.log('✅ Cell capacities refreshed successfully');
        renderAll(); // Re-render UI
    } catch (error) {
        console.error('❌ Failed to refresh cell capacities:', error);
    }
}

/**
 * รีเซ็ต flag การโหลดงานที่ค้างอยู่ (สำหรับกรณีพิเศษ)
 */
function resetPendingJobsFlag() {
    pendingJobsLoaded = false;
    console.log('🔄 Reset pending jobs flag - สามารถโหลดงานที่ค้างอยู่ใหม่ได้');
}

// ทำให้ function เป็น global เพื่อเรียกจาก console ได้
window.loadPendingJobsFromGateway = loadPendingJobsFromGateway;
window.syncQueueFromBackend = syncQueueFromBackend;
window.restoreShelfStateFromServer = restoreShelfStateFromServer;
window.syncShelfStateToServer = syncShelfStateToServer;
window.autoSyncAfterJobComplete = autoSyncAfterJobComplete;
window.getCellCapacityInfo = getCellCapacityInfo;
window.refreshCellCapacities = refreshCellCapacities;
window.resetPendingJobsFlag = resetPendingJobsFlag;
window.loadLayoutFromGateway = loadLayoutFromGateway;
