/**
 * ui/queue.js - Queue Management, Barcode Scanning & Orchestration
 * จัดการคิวงาน, การสแกนบาร์โค้ด และการประสานงานระหว่างส่วนต่างๆ
 */

/**
 * ===================
 * RENDERING FUNCTIONS
 * ===================
 */

/**
 * แสดงผลหน้าหลักทั้งหมด (orchestration)
 */
function renderAll() {
    const queue = ShelfState.getQueue();
    const activeJob = ShelfState.getActiveJob();
    const uiState = ShelfState.getUIState();

    // อัปเดตปุ่ม Queue Notification
    updateQueueNotificationButton();

    // Logic สำหรับแสดงหน้าที่เหมาะสม
    if (uiState.showMainWithQueue) {
        // แสดงหน้า Main พร้อม notification button
        showView('main');
        ShelfUI.createShelfGridStructure();
        ShelfUI.renderShelfGrid();
        controlLEDByQueue();
    } else if (activeJob) {
        // แสดงหน้า Active Job
        showView('activeJob');
        renderActiveJob();
        controlLEDByActiveJob();
        setupBarcodeScanner();
    } else if (queue.length > 0) {
        // แสดงหน้า Queue Selection
        showView('queueSelection');
        renderQueueSelectionView(queue);
        controlLEDByQueue();
    } else {
        // แสดงหน้า Main (ไม่มี queue)
        showView('main');
        ShelfUI.createShelfGridStructure();
        ShelfUI.renderShelfGrid();
        ShelfServices.clearLED();
    }
}

/**
 * แสดงผล Queue Selection View
 */
function renderQueueSelectionView(queue) {
    // ล้าง containers
    const queueListContainer = document.getElementById('queueListContainer');
    if (queueListContainer) {
        queueListContainer.innerHTML = '';
    }
    
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
        const jobItem = document.createElement('div');
        jobItem.className = 'queue-item';
        jobItem.innerHTML = `
            <div class="job-info">
                <div class="job-lot">${job.lot_no}</div>
                <div class="job-location">L${job.level}B${job.block}</div>
            </div>
            <button onclick="selectJob('${job.jobId}')" class="select-job-btn">
                Select
            </button>
        `;
        return jobItem;
    }

    // เพิ่มงานวางในฝั่งซ้าย
    if (placeContainer) {
        if (placeJobs.length > 0) {
            placeJobs.forEach(job => {
                placeContainer.appendChild(createJobItem(job));
            });
        } else {
            placeContainer.innerHTML = '<div class="no-jobs">No place jobs</div>';
        }
    }

    // เพิ่มงานหยิบในฝั่งขวา
    if (pickContainer) {
        if (pickJobs.length > 0) {
            pickJobs.forEach(job => {
                pickContainer.appendChild(createJobItem(job));
            });
        } else {
            pickContainer.innerHTML = '<div class="no-jobs">No pick jobs</div>';
        }
    }

    // Fallback: ใช้ container เดิมถ้าไม่มี container ใหม่
    if (!placeContainer || !pickContainer) {
        if (queueListContainer) {
            queue.forEach(job => {
                const jobItem = createJobItem(job);
                // เพิ่ม badge แสดงประเภทงาน
                const typeBadge = document.createElement('span');
                typeBadge.className = `job-type-badge ${job.place_flg === '1' ? 'place' : 'pick'}`;
                typeBadge.textContent = job.place_flg === '1' ? 'PLACE' : 'PICK';
                jobItem.querySelector('.job-info').appendChild(typeBadge);
                
                queueListContainer.appendChild(jobItem);
            });
        }
    }

    // Logic focus เดิม
    const lotInput = document.getElementById('lot-no-input');
    if (lotInput) {
        lotInput.focus();
        // เคลียร์ค่าเก่า
        lotInput.value = '';
        // ตั้งค่า placeholder
        lotInput.placeholder = 'Scan or type LOT number...';
    }
}

/**
 * แสดงผล Active Job View
 */
function renderActiveJob() {
    const activeJob = ShelfState.getActiveJob();
    const queue = ShelfState.getQueue();
    const cellPreviewContainer = document.getElementById('cellPreviewContainer');
    const mainContainer = document.querySelector('.main-container');

    if (activeJob) {
        console.log(`🎯 Rendering active job: ${activeJob.lot_no} at L${activeJob.level}B${activeJob.block}`);
        // แสดงข้อมูลงานปัจจุบันใน UI
        updateActiveJobDisplay(activeJob);
    } else {
        console.log('⚠️ No active job to render');
        // ไปหน้า queue หรือ main
        goBackToQueue();
        return;
    }

    // สร้าง shelf grid ใหม่
    ShelfUI.createShelfGridStructure();

    // Log clearly which lot is currently selected as active job, and lots in that cell
    if (activeJob) {
        console.log(`🎯 Active Job Selected: ${activeJob.lot_no} (${activeJob.place_flg === '1' ? 'Place' : 'Pick'})`);
        console.log(`📍 Target Location: Level ${activeJob.level}, Block ${activeJob.block}`);
        
        // แสดงข้อมูลใน cell preview
        const lotsInCell = ShelfState.getLotsInCell(activeJob.level, activeJob.block);
        console.log(`📦 Current lots in L${activeJob.level}B${activeJob.block}:`, lotsInCell);
        
        // Render cell preview
        if (cellPreviewContainer) {
            ShelfUI.renderCellPreview({
                level: activeJob.level,
                block: activeJob.block,
                lots: lotsInCell,
                targetLotNo: activeJob.lot_no,
                isPlaceJob: activeJob.place_flg === '1'
            });
        }
    } else {
        console.log('⚠️ No active job found');
        if (queue.length > 0) {
            showView('queueSelection');
        } else {
            showView('main');
        }
    }

    ShelfUI.renderShelfGrid();
}

/**
 * อัปเดตการแสดงผลข้อมูล Active Job
 */
function updateActiveJobDisplay(activeJob) {
    // อัปเดต job info elements
    const elements = {
        'activeLotNo': activeJob.lot_no,
        'activeJobLocation': `L${activeJob.level}B${activeJob.block}`,
        'activeJobType': activeJob.place_flg === '1' ? 'PLACE' : 'PICK'
    };

    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });

    // อัปเดต progress bar ถ้ามี
    const progressBar = document.getElementById('jobProgress');
    if (progressBar) {
        const queue = ShelfState.getQueue();
        const totalJobs = queue.length + 1; // +1 สำหรับ active job
        const completedJobs = 1; // active job กำลังทำ
        const percentage = (completedJobs / totalJobs) * 100;
        progressBar.style.width = `${percentage}%`;
    }
}

/**
 * ===================
 * NAVIGATION FUNCTIONS
 * ===================
 */

/**
 * แสดงหน้าที่ระบุ
 */
function showView(viewName) {
    const views = ['mainView', 'queueSelectionView', 'activeJobView'];
    
    views.forEach(view => {
        const element = document.getElementById(view);
        if (element) {
            element.style.display = 'none';
        }
    });

    const targetView = document.getElementById(viewName + 'View');
    if (targetView) {
        targetView.style.display = 'block';
    }

    console.log(`👁️ Switched to ${viewName} view`);
}

/**
 * กลับไปหน้า Main แต่ยังคง queue ไว้ (จากหน้า Queue Selection)
 */
function goBackToMain() {
    console.log('🏠 Going back to main view with queue preserved');
    ShelfState.setShowMainWithQueue(true);
    stopAutoReturnTimer();
    startActivityDetection();
    startAutoReturnTimer();
    renderAll();
}

/**
 * ไปหน้า Queue Selection (จากปุ่ม notification ในหน้า Main)
 */
function goToQueueSelection() {
    console.log('📋 Going to queue selection view');
    ShelfState.setShowMainWithQueue(false);
    stopAutoReturnTimer();
    stopActivityDetection();
    renderAll();
}

/**
 * กลับไปหน้า Queue (จากหน้า Active Job)
 */
function goBackToQueue() {
    const activeJob = ShelfState.getActiveJob();
    if (activeJob) {
        // ใส่งานกลับเข้า queue
        console.log(`📤 Returning job ${activeJob.lot_no} to queue`);
        ShelfState.addToQueue(activeJob);
        
        // ล้าง active job
        ShelfState.removeActiveJob();
        
        // ปิดไฟ LED
        ShelfServices.clearLED();
    }
    
    // Clear persistent notifications when leaving Active Job view
    ShelfNotifications.clearPersistentNotifications();
    
    renderAll();
}

/**
 * ===================
 * JOB MANAGEMENT
 * ===================
 */

/**
 * เลือกงานจาก queue
 */
function selectJob(jobId) {
    const queue = ShelfState.getQueue();
    const selectedJob = queue.find(job => job.jobId === jobId);
    
    if (selectedJob) {
        console.log(`📋 Job selected: ${selectedJob.lot_no} at L${selectedJob.level}B${selectedJob.block}`);
        
        // ลบงานออกจาก queue
        ShelfState.removeFromQueue(jobId);
        
        // ตั้งเป็น active job
        ShelfState.setActiveJob(selectedJob);
        
        // Clear loggedCells for fresh logging
        ShelfState.clearLoggedCells();
        
        // แสดงหน้า Active Job
        renderAll();
        
        // แสดง notification
        const actionText = selectedJob.place_flg === '1' ? 'วางของ' : 'หยิบของ';
        ShelfNotifications.showNotification(
            `เลือกงาน: ${selectedJob.lot_no} (${actionText}) - L${selectedJob.level}B${selectedJob.block}`,
            'info'
        );
    } else {
        console.error('❌ Job not found:', jobId);
        ShelfNotifications.showNotification('ไม่พบงานที่เลือก', 'error');
    }
}

/**
 * ค้นหางานจาก LOT number
 */
function findAndSelectJobByLot(lotNo) {
    if (!lotNo) return;

    // ตรวจสอบรูปแบบ LOT number ก่อนค้นหา
    if (!ShelfUtils.isValidLotNumberFormat(lotNo)) {
        console.warn(`❌ Invalid LOT format: ${lotNo}`);
        ShelfNotifications.showLotFormatWarningPopup(lotNo);
        return;
    }

    const queue = ShelfState.getQueue();
    const foundJob = queue.find(job => job.lot_no === lotNo);

    if (foundJob) {
        const activeJob = ShelfState.getActiveJob();
        
        if (activeJob && activeJob.lot_no !== lotNo) {
            // มี active job อยู่แล้ว และ scan LOT ใหม่ที่แตกต่าง -> ถามก่อน
            console.log(`🤔 Current active job: ${activeJob.lot_no}, Scanned: ${lotNo}`);
            
            ShelfNotifications.showJobConfirmationPopup(
                activeJob, 
                foundJob, 
                lotNo,
                // Callback เมื่อกด Yes (Complete current job)
                async () => {
                    console.log(`✅ User confirmed completion of ${activeJob.lot_no}`);
                    
                    // Complete current job
                    const result = await ShelfServices.completeJob(activeJob.jobId);
                    
                    if (result.success) {
                        ShelfNotifications.showNotification(
                            `งาน ${activeJob.lot_no} เสร็จสิ้น`,
                            'success'
                        );
                        
                        // Refresh shelf state
                        await ShelfServices.refreshShelfStateFromServer();
                        
                        // Select new job
                        selectJob(foundJob.jobId);
                    } else {
                        ShelfNotifications.showNotification(
                            `เกิดข้อผิดพลาด: ${result.error}`,
                            'error'
                        );
                    }
                },
                // Callback เมื่อกด No (Continue current job)
                () => {
                    console.log(`➡️ User chose to continue with ${activeJob.lot_no}`);
                    ShelfNotifications.showNotification(
                        `ทำงาน ${activeJob.lot_no} ต่อ`,
                        'info'
                    );
                }
            );
        } else {
            // ไม่มี active job หรือเป็น LOT เดียวกัน -> เลือกเลย
            selectJob(foundJob.jobId);
        }
    } else {
        // ไม่พบใน queue -> เรียก LMS
        console.log(`🔍 LOT ${lotNo} not in queue, checking LMS...`);
        handleUnknownLotScanned(lotNo);
    }
}

/**
 * จัดการเมื่อ scan LOT ที่ไม่อยู่ในคิว (Auto LMS check)
 */
async function handleUnknownLotScanned(scannedLot) {
    if (!scannedLot) return;

    console.log(`🔍 Processing unknown LOT: ${scannedLot}`);
    
    // ตรวจสอบว่า LOT อยู่ในคิวหรือไม่
    const queue = ShelfState.getQueue();
    const lotInQueue = queue.find(job => job.lot_no === scannedLot);
    
    if (lotInQueue) {
        // ถ้าอยู่ในคิว ให้เลือกงานปกติ
        selectJob(lotInQueue.jobId);
        return;
    }

    // ถ้าไม่อยู่ในคิว ให้แสดง popup แจ้งเตือนก่อน
    ShelfNotifications.showLMSAlertPopup(
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
        try {
            const lmsResult = await ShelfServices.checkShelfFromLMS(scannedLot, placeFlg);
            
            if (lmsResult.success) {
                ShelfNotifications.showLMSLocationPopup(
                    lmsResult.lotNo,
                    lmsResult.correctShelf,
                    'info'
                );
            } else {
                ShelfNotifications.showLMSAlertPopup(
                    '❌ LMS Error',
                    lmsResult.error,
                    null,
                    'error',
                    5000
                );
            }
        } catch (error) {
            console.error('❌ LMS check failed:', error);
            ShelfNotifications.showNotification('เกิดข้อผิดพลาดในการตรวจสอบ LMS', 'error');
        }
    }, 1000);
}

/**
 * ===================
 * BARCODE SCANNING
 * ===================
 */

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
        if (event.key === 'Enter' && this.value.trim()) {
            handleBarcodeScanned();
        }
    };

    // ให้ focus กลับมาที่ช่องสแกนเสมอ
    barcodeInput.onblur = function() {
        setTimeout(() => {
            if (document.getElementById('barcode-scanner-input')) {
                this.focus();
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
    
    const activeJob = ShelfState.getActiveJob();
    if (!activeJob) {
        console.warn('⚠️ No active job for barcode scanning');
        return;
    }

    // ตรวจสอบว่าเป็นการสแกน lot number ใหม่ที่อยู่ใน queue หรือไม่
    if (ShelfUtils.isValidLotNumberFormat(scannedData)) {
        const isLotInQueue = ShelfState.isLotInQueue(scannedData);
        
        if (isLotInQueue && scannedData !== activeJob.lot_no) {
            // LOT อื่นที่อยู่ใน queue -> ถามว่าจะเปลี่ยนงานหรือไม่
            findAndSelectJobByLot(scannedData);
            return;
        } else if (scannedData === activeJob.lot_no) {
            // สแกน LOT ของงานปัจจุบัน -> แสดงการยืนยัน
            ShelfNotifications.showNotification(`Confirmed LOT: ${scannedData}`, 'success');
            return;
        }
    }

    const locationMatch = ShelfUtils.parseLocationFromBarcode(scannedData);
    
    if (!locationMatch) {
        ShelfNotifications.showNotification('รูปแบบบาร์โค้ดไม่ถูกต้อง', 'warning');
        return;
    }

    const { level, block } = locationMatch;
    const correctLevel = Number(activeJob.level);
    const correctBlock = Number(activeJob.block);

    // ก่อนอัปเดต UI ให้ลบ class error เดิมออกจากทุก cell
    const allCells = document.querySelectorAll('.shelf-cell');
    allCells.forEach(cell => {
        cell.classList.remove('error-source', 'error-target');
    });

    if (Number(level) === correctLevel && Number(block) === correctBlock) {
        // ตำแหน่งถูกต้อง
        console.log(`✅ Correct location scanned: L${level}B${block}`);
        ShelfNotifications.showNotification('ตำแหน่งถูกต้อง! กำลังดำเนินการ...', 'success', { persistent: true });
        
        // เรียกฟังก์ชัน complete job
        setTimeout(() => {
            completeCurrentJob();
        }, 1500);
    } else {
        // ตำแหน่งผิด
        console.log(`❌ Wrong location scanned: L${level}B${block}, expected: L${correctLevel}B${correctBlock}`);
        
        const errorMessage = `Wrong location: scanned L${level}B${block}, should be L${correctLevel}B${correctBlock}`;
        const errorJob = { 
            ...activeJob, 
            error: true, 
            errorType: 'WRONG_LOCATION', 
            errorMessage 
        };
        
        ShelfState.setActiveJob(errorJob);
        renderAll();
        
        ShelfNotifications.showNotification(errorMessage, 'error', { persistent: true });
        
        // ควบคุมไฟ LED แสดง error
        controlLEDByActiveJob();
    }
}

/**
 * ส่งคำสั่ง Complete Job
 */
async function completeCurrentJob() {
    let activeJob = ShelfState.getActiveJob();
    if (!activeJob) {
        console.warn('⚠️ No active job to complete');
        return;
    }

    // ตรวจสอบและเคลียร์ error state ถ้ามี
    if (activeJob.error) {
        console.log('🔄 Clearing error state before completion');
        delete activeJob.error;
        delete activeJob.errorType;
        delete activeJob.errorMessage;
        ShelfState.setActiveJob(activeJob);
    }

    console.log('🚀 Completing job:', activeJob.jobId, 'Lot:', activeJob.lot_no);

    // Clear loggedCells so next render logs new state
    ShelfState.clearLoggedCells();

    // ใช้ HTTP API เป็นหลักเพื่อความเสถียร
    console.log('📤 Sending complete job request via HTTP API...');
    
    const result = await ShelfServices.completeJob(activeJob.jobId);
    
    if (result.success) {
        console.log('✅ Job completed successfully');
        ShelfNotifications.showNotification(`งาน ${activeJob.lot_no} เสร็จสิ้นแล้ว`, 'success');
        
        // ลบ active job
        ShelfState.removeActiveJob();
        
        // รีเฟรช shelf state
        await ShelfServices.refreshShelfStateFromServer();
        
        // ไปหน้าต่อไป
        renderAll();
    } else {
        console.error('❌ Job completion failed:', result.error);
        ShelfNotifications.showNotification(`เกิดข้อผิดพลาด: ${result.error}`, 'error');
    }
}

/**
 * ===================
 * LED CONTROL
 * ===================
 */

/**
 * ควบคุมไฟ LED ตาม active job
 */
async function controlLEDByActiveJob(wrongLocation = null) {
    const activeJob = ShelfState.getActiveJob();
    if (!activeJob) {
        console.log('💡 No active job - clearing LEDs');
        return await ShelfServices.clearLED();
    }

    const level = Number(activeJob.level);
    const block = Number(activeJob.block);
    
    // ช่องเป้าหมาย: สีฟ้าสำหรับ target position
    let targetColor = { r: 0, g: 100, b: 255 }; // สีฟ้าชัดเจน
    if (activeJob.place_flg === '0') {
        targetColor = { r: 255, g: 165, b: 0 }; // สีส้มสำหรับ Pick
    }

    console.log(`💡 LED Control: Active job L${level}B${block}, Place=${activeJob.place_flg}`);

    // ถ้าอยู่ใน error state และมี wrong location
    if (activeJob.error && activeJob.errorType === 'WRONG_LOCATION' && activeJob.errorMessage) {
        const match = activeJob.errorMessage.match(/L(\d+)B(\d+)/);
        if (match) {
            const wrongLevel = parseInt(match[1], 10);
            const wrongBlock = parseInt(match[2], 10);
            
            // แสดงไฟแดงที่ตำแหน่งผิด และไฟเขียวที่ตำแหน่งถูก
            const positions = [
                { position: `L${wrongLevel}B${wrongBlock}`, r: 255, g: 0, b: 0 }, // แดงที่ตำแหน่งผิด
                { position: `L${level}B${block}`, r: 0, g: 255, b: 0 } // เขียวที่ตำแหน่งถูก
            ];
            
            return await ShelfServices.setBatchLED(positions, true);
        }
    }
    
    // โหมดปกติ - จุดไฟเฉพาะช่องเป้าหมาย
    return await ShelfServices.setLED(`L${level}B${block}`, targetColor.r, targetColor.g, targetColor.b);
}

/**
 * ควบคุมไฟ LED ตาม queue
 */
async function controlLEDByQueue() {
    const queue = ShelfState.getQueue();
    if (!queue || queue.length === 0) {
        console.log('💡 No queue items - clearing LEDs');
        return await ShelfServices.clearLED();
    }
    
    console.log(`💡 LED Queue Mode: ${queue.length} jobs`);
    
    // เตรียม batch สำหรับทุก job ใน queue
    const positions = queue.map(job => ({
        position: `L${Number(job.level)}B${Number(job.block)}`,
        r: 0, g: 150, b: 255 // ฟ้าสว่างสำหรับ queue
    }));
    
    return await ShelfServices.setBatchLED(positions, true);
}

/**
 * ===================
 * TIMER FUNCTIONS
 * ===================
 */

/**
 * เริ่ม Auto Return Timer (7 วินาที)
 */
function startAutoReturnTimer() {
    const uiState = ShelfState.getUIState();
    if (uiState.autoReturnTimer) {
        stopAutoReturnTimer();
    }
    
    console.log('⏱️ Starting auto-return timer (7 seconds)');
    ShelfState.startAutoReturnTimer(() => {
        console.log('⏰ Auto-return timer expired - going to queue selection');
        goToQueueSelection();
    }, 7000);
}

/**
 * หยุด Auto Return Timer
 */
function stopAutoReturnTimer() {
    ShelfState.stopAutoReturnTimer();
    console.log('🛑 Auto-return timer stopped');
}

/**
 * Reset Auto Return Timer (เมื่อมีกิจกรรม)
 */
function resetAutoReturnTimer() {
    const uiState = ShelfState.getUIState();
    if (uiState.showMainWithQueue && uiState.autoReturnTimer) {
        console.log('🔄 Resetting auto-return timer');
        ShelfState.resetAutoReturnTimer(() => {
            goToQueueSelection();
        }, 7000);
    }
}

/**
 * เริ่มตรวจจับกิจกรรมของผู้ใช้
 */
function startActivityDetection() {
    const uiState = ShelfState.getUIState();
    if (uiState.activityDetectionActive) return;
    
    ShelfState.setActivityDetectionActive(true);
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
    const uiState = ShelfState.getUIState();
    if (!uiState.activityDetectionActive) return;
    
    ShelfState.setActivityDetectionActive(false);
    console.log('🛑 Stopping activity detection');
    
    const activityEvents = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
    
    activityEvents.forEach(event => {
        document.removeEventListener(event, resetAutoReturnTimer);
    });
}

/**
 * ===================
 * UI HELPER FUNCTIONS
 * ===================
 */

/**
 * อัปเดตปุ่ม Queue Notification และ Back to Queue
 */
function updateQueueNotificationButton() {
    const queueBtn = document.getElementById('queueNotificationBtn');
    const queueCountBadge = document.getElementById('queueCountBadge');
    const backToQueueBtn = document.getElementById('backToQueueBtn');
    
    if (!queueBtn || !queueCountBadge) return;
    
    const queue = ShelfState.getQueue();
    const queueCount = queue.length;
    const activeJob = ShelfState.getActiveJob();
    const uiState = ShelfState.getUIState();
    
    // จัดการปุ่ม Queue Notification (แสดงในหน้า main เมื่อมี queue)
    if (uiState.showMainWithQueue && queueCount > 0) {
        queueBtn.style.display = 'block';
        queueCountBadge.textContent = queueCount;
        queueBtn.onclick = goToQueueSelection;
        
        // อัปเดต tooltip
        queueBtn.title = `${queueCount} job${queueCount > 1 ? 's' : ''} in queue`;
    } else {
        queueBtn.style.display = 'none';
    }
    
    // จัดการปุ่ม Back to Queue (แสดงเมื่อมี active job และไม่อยู่ใน mainView)
    if (backToQueueBtn) {
        if (activeJob && !uiState.showMainWithQueue) {
            backToQueueBtn.style.display = 'block';
            backToQueueBtn.onclick = goBackToQueue;
        } else {
            backToQueueBtn.style.display = 'none';
        }
    }
}

/**
 * ดึงค่าจากช่อง input แล้วส่งไปให้ฟังก์ชันค้นหา
 */
function handleLotSearch() {
    const lotInput = document.getElementById('lot-no-input');
    if (lotInput) {
        const lotNo = lotInput.value.trim();
        if (lotNo) {
            console.log(`🔍 Manual LOT search: ${lotNo}`);
            findAndSelectJobByLot(lotNo);
            
            // เคลียร์ค่าหลังการค้นหา
            lotInput.value = '';
        } else {
            console.warn('⚠️ Empty LOT input');
            ShelfNotifications.showNotification('กรุณาใส่หมายเลข LOT', 'warning');
        }
    }
}

/**
 * ===================
 * EXPORT FUNCTIONS (Global Scope)
 * ===================
 */

if (typeof window !== 'undefined') {
    // Export all functions to ShelfQueue module
    window.ShelfQueue = {
        renderAll,
        renderQueueSelectionView,
        renderActiveJob,
        updateActiveJobDisplay,
        showView,
        goBackToMain,
        goToQueueSelection,
        goBackToQueue,
        selectJob,
        findAndSelectJobByLot,
        handleUnknownLotScanned,
        setupBarcodeScanner,
        handleBarcodeScanned,
        completeCurrentJob,
        controlLEDByActiveJob,
        controlLEDByQueue,
        startAutoReturnTimer,
        stopAutoReturnTimer,
        resetAutoReturnTimer,
        startActivityDetection,
        stopActivityDetection,
        updateQueueNotificationButton,
        handleLotSearch
    };
    
    // Expose functions that HTML needs to call directly
    window.selectJob = selectJob;
    window.goBackToMain = goBackToMain;
    window.goToQueueSelection = goToQueueSelection;
    window.goBackToQueue = goBackToQueue;
    window.handleLotSearch = handleLotSearch;
    window.findAndSelectJobByLot = findAndSelectJobByLot;
}