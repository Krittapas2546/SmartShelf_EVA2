

/**
 * สร้างโครงสร้าง shelf grid
 */
function createShelfGridStructure() {
    const shelfGrid = document.getElementById('shelfGrid');
    if (!shelfGrid) return;

    const config = ShelfState.getShelfConfig();
    const totalLevels = ShelfState.getTotalLevels();
    
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
    for (let level = totalLevels; level >= 1; level--) {
        const blocksInThisLevel = config[level];
        
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
            cell.className = 'shelf-cell';
            cell.id = `cell-${level}-${block}`;
            cell.dataset.level = level;
            cell.dataset.block = block;
            
            // กำหนดขนาด cell ให้กระจายเต็มความกว้าง
            const totalGaps = (blocksInThisLevel - 1) * gapSize;
            const cellWidth = (availableWidth - totalGaps) / blocksInThisLevel;
            
            cell.style.flex = `0 0 ${cellWidth}px`;
            cell.style.height = '100%';
            cell.style.border = '2px solid #dee2e6';
            cell.style.borderRadius = '8px';
            cell.style.background = 'linear-gradient(135deg, #ffffff, #f8f9fa)';
            cell.style.display = 'flex';
            cell.style.flexDirection = 'column';
            cell.style.alignItems = 'center';
            cell.style.justifyContent = 'flex-end'; // จัดให้อยู่ด้านล่าง (LIFO)
            cell.style.padding = '4px';
            cell.style.fontSize = '11px';
            cell.style.fontWeight = 'bold';
            cell.style.color = '#495057';
            cell.style.position = 'relative';
            cell.style.overflow = 'hidden';
            
            levelContainer.appendChild(cell);
        }
        
        shelfGrid.appendChild(levelContainer);
    }
    
    console.log(`📐 Created flexible shelf grid: ${totalLevels} levels with configuration:`, config);
    console.log(`📏 Shelf frame: ${shelfFrameWidth}×${shelfFrameHeight}px | Available width: ${availableWidth}px | Cell height: ${cellHeight}px | Gap: ${gapSize}px`);
}

/**
 * แสดงรายละเอียดช่องที่เลือก (Cell Preview)
 */
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
    
    html += `<div class="block-preview">`;

    if (previewLots.length > 0) {
        // สร้างรายการ lot แนวตั้ง (จากล่างขึ้นบน)
        for (let i = previewLots.length - 1; i >= 0; i--) {
            const lot = previewLots[i];
            const isNewLot = isPlaceJob && lot.lot_no === targetLotNo;
            
            html += `<div class="lot-item ${isNewLot ? 'new-lot' : ''}">`;
            html += `<span class="lot-name">${lot.lot_no}</span>`;
            html += `<span class="lot-tray-count">${lot.tray_count} trays</span>`;
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

/**
 * แสดงผล shelf grid พร้อมข้อมูล lots
 */
function renderShelfGrid() {
    // Expect shelfState as array of {level, block, lots}
    const shelfState = ShelfState.getShelfState();
    const activeJob = ShelfState.getActiveJob();
    
    console.log(`🔄 renderShelfGrid called with activeJob:`, activeJob);
    if (activeJob) {
        console.log(`🎯 Active job: L${activeJob.level}B${activeJob.block} - ${activeJob.lot_no} (${activeJob.place_flg === '1' ? 'Place' : 'Pick'})`);
    }

    // เตรียมตำแหน่ง error (ถ้ามี)
    let wrongLevel = null, wrongBlock = null;
    if (activeJob && activeJob.error && activeJob.errorType === 'WRONG_LOCATION' && activeJob.errorMessage) {
        const match = activeJob.errorMessage.match(/L(\d+)B(\d+)/);
        if (match) {
            wrongLevel = parseInt(match[1], 10);
            wrongBlock = parseInt(match[2], 10);
        }
    }

    // Clear all cells first
    const totalLevels = ShelfState.getTotalLevels();
    const config = ShelfState.getShelfConfig();
    for (let level = 1; level <= totalLevels; level++) {
        const blocksInLevel = config[level] || 0;
        for (let block = 1; block <= blocksInLevel; block++) {
            const cell = document.getElementById(`cell-${level}-${block}`);
            if (cell) {
                cell.innerHTML = '';
                cell.className = 'shelf-cell'; // Reset classes
            }
        }
    }

    // Render stacked lots in each cell (bottom-to-top: index 0 = bottom)
    const loggedCells = ShelfState.hasLoggedCell;
    if (Array.isArray(shelfState)) {
        shelfState.forEach(cellData => {
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
            
            const cell = document.getElementById(`cell-${cellLevel}-${cellBlock}`);
            if (!cell) return;

            // เพิ่ม label L{level}B{block}
            const labelDiv = document.createElement('div');
            labelDiv.textContent = `L${cellLevel}B${cellBlock}`;
            labelDiv.style.cssText = `
                position: absolute;
                top: 2px;
                left: 4px;
                font-size: 8px;
                font-weight: bold;
                color: #6c757d;
                z-index: 1;
            `;
            cell.appendChild(labelDiv);

            // แสดง lots (ถ้ามี)
            if (Array.isArray(cellLots) && cellLots.length > 0) {
                // Log เฉพาะครั้งแรกที่มี lots
                const cellKey = `${cellLevel}-${cellBlock}`;
                if (!loggedCells(cellKey)) {
                    console.log(`📦 Cell L${cellLevel}B${cellBlock} has ${cellLots.length} lots:`, cellLots);
                    ShelfState.addLoggedCell(cellKey);
                }

                // สร้าง container สำหรับ lots
                const lotsContainer = document.createElement('div');
                lotsContainer.style.cssText = `
                    display: flex;
                    flex-direction: column-reverse;
                    align-items: center;
                    justify-content: flex-end;
                    height: calc(100% - 16px);
                    width: 100%;
                    gap: 1px;
                    margin-top: 12px;
                `;

                // แสดง lots (จากล่างขึ้นบน: index 0 = ล่างสุด)
                cellLots.forEach((lot, index) => {
                    const lotDiv = document.createElement('div');
                    lotDiv.style.cssText = `
                        background: linear-gradient(135deg, #007bff, #0056b3);
                        color: white;
                        padding: 2px 4px;
                        border-radius: 3px;
                        font-size: 9px;
                        font-weight: bold;
                        text-align: center;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        width: calc(100% - 8px);
                        min-height: 16px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                        border: 1px solid rgba(255,255,255,0.3);
                    `;
                    
                    // แสดงข้อมูล lot
                    const lotText = lot.lot_no || lot;
                    const trayCount = lot.tray_count || '';
                    lotDiv.textContent = trayCount ? `${lotText} (${trayCount})` : lotText;
                    
                    lotsContainer.appendChild(lotDiv);
                });

                cell.appendChild(lotsContainer);
            }
        });
    } else {
        console.warn('⚠️ Shelf state is not an array:', shelfState);
    }

    // --- Apply activeJob และ error state classes ให้ทุก cell หลังจาก render lots แล้ว ---
    console.log(`🔍 Checking activeJob:`, activeJob);
    if (activeJob) {
        const targetLevel = Number(activeJob.level);
        const targetBlock = Number(activeJob.block);
        const targetCell = document.getElementById(`cell-${targetLevel}-${targetBlock}`);
        
        if (targetCell) {
            // เพิ่ม active-job class
            targetCell.classList.add('active-job');
            console.log(`🎯 Applied active-job class to L${targetLevel}B${targetBlock}`);
            
            // ถ้ามี error state
            if (activeJob.error && activeJob.errorType === 'WRONG_LOCATION') {
                targetCell.classList.add('error-target');
                console.log(`❌ Applied error-target class to L${targetLevel}B${targetBlock}`);
                
                // เพิ่ม class error-source ให้ตำแหน่งที่สแกนผิด
                if (wrongLevel && wrongBlock) {
                    const wrongCell = document.getElementById(`cell-${wrongLevel}-${wrongBlock}`);
                    if (wrongCell) {
                        wrongCell.classList.add('error-source');
                        console.log(`🚨 Applied error-source class to L${wrongLevel}B${wrongBlock}`);
                    }
                }
            }
        }
    }
}

/**
 * อัปเดตขนาด cell เมื่อมีการเปลี่ยนแปลง
 */
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
        // เก็บ classes เดิมไว้
        const currentClasses = cell.className;
        
        // อัปเดต style
        cell.style.height = '100%';
        
        // คืน classes
        cell.className = currentClasses;
    });
}

/**
 * รีเฟรช shelf grid structure
 */
function refreshShelfGrid() {
    console.log('🔄 Force refreshing shelf grid with config:', ShelfState.getShelfConfig());
    
    // เคลียร์ localStorage เพื่อให้สร้าง state ใหม่
    localStorage.removeItem(ShelfState.GLOBAL_SHELF_STATE_KEY);
    
    const shelfGrid = document.getElementById('shelfGrid');
    if (shelfGrid) {
        createShelfGridStructure();
        ShelfState.initializeShelfState(); // สร้าง state ใหม่ตาม config ปัจจุบัน
        renderShelfGrid();
        console.log('✅ Shelf grid refreshed successfully');
    }
}

/**
 * Export functions for module usage
 */
if (typeof window !== 'undefined') {
    window.ShelfUI = {
        createShelfGridStructure,
        renderCellPreview,
        renderShelfGrid,
        updateCellSizes,
        refreshShelfGrid
    };
}