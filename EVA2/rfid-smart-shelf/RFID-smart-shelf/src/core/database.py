# SHELF_CONFIG สำหรับ backward compatibility
SHELF_CONFIG = {
    1: 6, 
    2: 6, 
    3: 6,
    4: 6, 
}

def create_initial_shelf_state():
    """สร้างสถานะเริ่มต้นของชั้นวางตาม SHELF_CONFIG (stacked lots)"""
    shelf_state = []
    for level, num_blocks in SHELF_CONFIG.items():
        for block in range(1, num_blocks + 1):
            shelf_state.append([level, block, []])  # [level, block, lots]
    return shelf_state

DB = {
    "jobs": [],
    "shelf_state": create_initial_shelf_state(),
    "job_counter": 0
}

# --- Helper Functions ---
def get_job_by_id(job_id: str):
    """ค้นหา Job จาก ID ใน DB"""
    return next((job for job in DB["jobs"] if job.get("jobId") == job_id), None)


# --- Stacked Lots Helper Functions ---
MAX_TRAY_PER_CELL = 24

def get_cell(level: int, block: int):
    for cell in DB["shelf_state"]:
        if cell[0] == level and cell[1] == block:
            return cell
    return None

def get_lots_in_position(level: int, block: int):
    cell = get_cell(level, block)
    if cell:
        return cell[2]
    return []

def add_lot_to_position(level: int, block: int, lot_no: str, tray_count: int):
    cell = get_cell(level, block)
    if not cell:
        return False
    lots = cell[2]
    total_tray = sum(lot['tray_count'] for lot in lots) + tray_count
    if total_tray > MAX_TRAY_PER_CELL:
        return False  # overflow
    # ถ้ามี lot_no เดิมใน cell ให้เพิ่ม tray_count ไปที่ lot เดิม
    for lot in lots:
        if lot['lot_no'] == lot_no:
            lot['tray_count'] += tray_count
            return True
    # ถ้าไม่มี lot_no เดิม ให้เพิ่มใหม่ (วางบนสุด: append)
    lots.append({"lot_no": lot_no, "tray_count": tray_count})
    return True

def remove_lot_from_position(level: int, block: int, lot_no: str):
    cell = get_cell(level, block)
    if not cell:
        return False
    lots = cell[2]
    for i, lot in enumerate(lots):
        if lot['lot_no'] == lot_no:
            lots.pop(i)
            return True
    return False

def update_lot_quantity(level: int, block: int, lot_no: str, new_tray_count: int):
    cell = get_cell(level, block)
    if not cell:
        return False
    lots = cell[2]
    for lot in lots:
        if lot['lot_no'] == lot_no:
            lot['tray_count'] = new_tray_count
            return True
    return False

def find_lot_location(lot_no: str):
    """ค้นหาว่า lot_no นี้อยู่ cell ไหน (คืน (level, block) หรือ None)"""
    for cell in DB["shelf_state"]:
        for lot in cell[2]:
            if lot['lot_no'] == lot_no:
                return (cell[0], cell[1])
    return None

def get_lot_in_position(level: int, block: int):
    """ดึง lot_no ที่อยู่ในตำแหน่งที่กำหนด"""
    for cell in DB["shelf_state"]:
        if cell[0] == level and cell[1] == block:
            return cell[3]  # ส่งคืน lot_no
    return None

def validate_position(level: int, block: int):
    """ตรวจสอบว่าตำแหน่งที่กำหนดมีอยู่จริงในชั้นวางหรือไม่"""
    return level in SHELF_CONFIG and 1 <= block <= SHELF_CONFIG[level]

def get_shelf_info():
    """ส่งคืนข้อมูลการกำหนดค่าของชั้นวาง"""
    return {
        "config": SHELF_CONFIG,
        "total_levels": len(SHELF_CONFIG),
        "max_blocks": max(SHELF_CONFIG.values()) if SHELF_CONFIG else 0
    }