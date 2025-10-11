# SHELF_CONFIG - ยังคงจำเป็น! ใช้งานใน:
# 1. Fallback เมื่อ Gateway ไม่พร้อมใช้งาน
# 2. LED Controller สำหรับคำนวณ pixel positions  
# 3. Frontend grid creation และ validation
# 4. API endpoints สำหรับ backward compatibility
# 5. Database initialization และ state management
# *** จะถูกอัปเดตโดยอัตโนมัติเมื่อดึงข้อมูลจาก Gateway ***
SHELF_CONFIG = {
    1: 6,  # Level 1: 6 blocks (fallback)
    2: 6,  # Level 2: 6 blocks (fallback)
    3: 6,  # Level 3: 6 blocks (fallback)
    4: 6,  # Level 4: 6 blocks (fallback)
}

# === Dynamic Layout Configuration ===
# จะถูกอัปเดตจาก Gateway API แทนการ hardcode

# CELL_CAPACITIES - ความจุรายช่อง (จะถูกอัปเดตจาก Gateway)
CELL_CAPACITIES = {
    # ค่าเริ่มต้น - จะถูก override จาก Gateway
    '1-1': 24,  
    '1-2': 24,
    '1-3': 24,
    '1-4': 24,
    '1-5': 24,
    '1-6': 24,
}

# DYNAMIC_LAYOUT - เก็บข้อมูล layout จาก Gateway
DYNAMIC_LAYOUT = {}

# ค่าเริ่มต้นสำหรับช่องที่ไม่ได้กำหนดใน CELL_CAPACITIES
DEFAULT_CELL_CAPACITY = 24

def update_layout_from_gateway(gateway_layout: dict):
    """
    อัปเดต local configuration จากข้อมูล layout ที่ได้จาก Gateway
    
    Args:
        gateway_layout: dict ที่มี key เป็น position (เช่น "L1-B1") และ value เป็นข้อมูลช่อง
        
    Returns:
        bool: True ถ้าอัปเดตสำเร็จ
        
    Example Gateway Layout:
    {
        "L1-B1": {"capacity": 40, "active": true, "level": "1", "block": "1"},
        "L1-B2": {"capacity": 40, "active": true, "level": "1", "block": "2"},
        ...
    }
    """
    try:
        global CELL_CAPACITIES, SHELF_CONFIG, DYNAMIC_LAYOUT
        
        # เก็บข้อมูลดิบจาก Gateway
        DYNAMIC_LAYOUT = gateway_layout.copy()
        
        # อัปเดต CELL_CAPACITIES
        new_capacities = {}
        new_shelf_config = {}
        
        for position_key, slot_info in gateway_layout.items():
            if not slot_info.get("active", True):
                continue  # ข้าม slot ที่ไม่ active
                
            level = int(slot_info.get("level", "1"))
            block = int(slot_info.get("block", "1"))
            capacity = int(slot_info.get("capacity", DEFAULT_CELL_CAPACITY))
            
            # อัปเดต capacity
            cell_key = f"{level}-{block}"
            new_capacities[cell_key] = capacity
            
            # อัปเดต shelf config
            if level not in new_shelf_config:
                new_shelf_config[level] = 0
            new_shelf_config[level] = max(new_shelf_config[level], block)
        
        # อัปเดต global variables
        CELL_CAPACITIES.update(new_capacities)
        SHELF_CONFIG.update(new_shelf_config)
        
        # อัปเดต shelf_state structure ถ้าจำเป็น
        current_state = DB.get("shelf_state", [])
        new_state = []
        
        # สร้าง state structure ใหม่ตาม Gateway layout
        for level in sorted(new_shelf_config.keys()):
            for block in range(1, new_shelf_config[level] + 1):
                # หา existing data
                existing_lots = []
                for cell in current_state:
                    if len(cell) >= 3 and cell[0] == level and cell[1] == block:
                        existing_lots = cell[2]
                        break
                
                new_state.append([level, block, existing_lots])
        
        DB["shelf_state"] = new_state
        
        print(f"✅ Layout updated from Gateway:")
        print(f"   📊 SHELF_CONFIG: {new_shelf_config}")
        print(f"   📦 CELL_CAPACITIES: {len(new_capacities)} positions")
        print(f"   🏗️  SHELF_STATE: {len(new_state)} cells")
        
        # เพิ่ม detailed logging สำหรับ layout ปัจจุบัน
        log_current_layout()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update layout from Gateway: {e}")
        return False

def get_layout_info():
    """
    ดึงข้อมูล layout ปัจจุบัน (รวม Gateway data ถ้ามี)
    """
    return {
        "shelf_config": SHELF_CONFIG,
        "cell_capacities": CELL_CAPACITIES,
        "dynamic_layout": DYNAMIC_LAYOUT,
        "total_positions": len(CELL_CAPACITIES),
        "default_capacity": DEFAULT_CELL_CAPACITY
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

def get_cell_capacity(level: int, block: int):
    """ดึงความจุของช่องตาม level และ block"""
    cell_key = f"{level}-{block}"
    return CELL_CAPACITIES.get(cell_key, DEFAULT_CELL_CAPACITY)

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

def add_lot_to_position(level: int, block: int, lot_no: str, tray_count: int, biz: str = "Unknown"):
    cell = get_cell(level, block)
    if not cell:
        return False
    lots = cell[2]
    total_tray = sum(lot['tray_count'] for lot in lots) + tray_count
    max_capacity = get_cell_capacity(level, block)
    if total_tray > max_capacity:
        print(f"⚠️ Cell L{level}B{block} overflow: {total_tray} > {max_capacity}")
        return False  # overflow
    # ถ้ามี lot_no เดิมใน cell ให้เพิ่ม tray_count ไปที่ lot เดิม
    for lot in lots:
        if lot['lot_no'] == lot_no:
            lot['tray_count'] += tray_count
            # อัปเดต biz ถ้าไม่มีหรือเป็น Unknown
            if 'biz' not in lot or lot['biz'] == "Unknown":
                lot['biz'] = biz
            return True
    # ถ้าไม่มี lot_no เดิม ให้เพิ่มใหม่ (วางบนสุด: append)
    lots.append({"lot_no": lot_no, "tray_count": tray_count, "biz": biz})
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

def update_lot_biz(lot_no: str, biz: str):
    """อัปเดต biz ของ lot_no ทุกตำแหน่งที่พบ"""
    updated_count = 0
    for cell in DB["shelf_state"]:
        for lot in cell[2]:
            if lot['lot_no'] == lot_no:
                lot['biz'] = biz
                updated_count += 1
    return updated_count
def migrate_existing_lots_add_biz():
    """เพิ่ม biz field ให้กับ lots ที่มีอยู่แล้วโดยไม่มี biz"""
    updated_count = 0
    for cell in DB["shelf_state"]:
        for lot in cell[2]:
            if 'biz' not in lot:
                lot['biz'] = "Unknown"
                updated_count += 1
    if updated_count > 0:
        print(f"🔄 Migrated {updated_count} existing lots to include biz field")
    return updated_count

def get_shelf_info():
    """ส่งคืนข้อมูลการกำหนดค่าของชั้นวาง"""
    return {
        "config": SHELF_CONFIG,
        "total_levels": len(SHELF_CONFIG),
        "max_blocks": max(SHELF_CONFIG.values()) if SHELF_CONFIG else 0,
        "cell_capacities": CELL_CAPACITIES,
        "dynamic_layout": DYNAMIC_LAYOUT
    }

def is_layout_loaded_from_gateway():
    """ตรวจสอบว่าได้โหลด layout จาก Gateway แล้วหรือยัง"""
    return bool(DYNAMIC_LAYOUT)

def get_active_positions():
    """ดึงรายการตำแหน่งที่ active จาก Gateway layout"""
    active_positions = []
    for position_key, slot_info in DYNAMIC_LAYOUT.items():
        if slot_info.get("active", True):
            level = int(slot_info.get("level", "1"))
            block = int(slot_info.get("block", "1"))
            active_positions.append((level, block))
    return active_positions

def get_layout_status():
    """ดึงสถานะ layout แบบ compact สำหรับ API response"""
    return {
        "shelf_config": SHELF_CONFIG,
        "cell_capacities_count": len(CELL_CAPACITIES),
        "dynamic_layout_count": len(DYNAMIC_LAYOUT), 
        "gateway_loaded": bool(DYNAMIC_LAYOUT),
        "total_cells": len(DB.get("shelf_state", [])),
        "occupied_cells": len([cell for cell in DB.get("shelf_state", []) if len(cell) >= 3 and cell[2]]),
        "default_capacity": DEFAULT_CELL_CAPACITY
    }

def log_current_layout():
    """แสดง log รายละเอียดของ layout ปัจจุบัน"""
    print("\n" + "="*50)
    print("📋 CURRENT LAYOUT SUMMARY")
    print("="*50)
    
    # 1. SHELF_CONFIG
    print(f"🏗️  SHELF_CONFIG (Current): {SHELF_CONFIG}")
    total_positions = sum(SHELF_CONFIG.values()) if SHELF_CONFIG else 0
    print(f"   Total positions: {total_positions}")
    
    # 2. CELL_CAPACITIES  
    print(f"📦 CELL_CAPACITIES ({len(CELL_CAPACITIES)} positions):")
    if CELL_CAPACITIES:
        for level in sorted(set(int(k.split('-')[0]) for k in CELL_CAPACITIES.keys())):
            level_capacities = {k: v for k, v in CELL_CAPACITIES.items() if k.startswith(f"{level}-")}
            print(f"   Level {level}: {level_capacities}")
    else:
        print("   (Empty)")
    
    # 3. DYNAMIC_LAYOUT from Gateway
    print(f"🌐 DYNAMIC_LAYOUT from Gateway ({len(DYNAMIC_LAYOUT)} positions):")
    if DYNAMIC_LAYOUT:
        for level in sorted(set(int(info.get('level', '1')) for info in DYNAMIC_LAYOUT.values())):
            level_layout = {k: v for k, v in DYNAMIC_LAYOUT.items() if int(v.get('level', '1')) == level}
            print(f"   Level {level}:")
            for pos_key, slot_info in sorted(level_layout.items()):
                status = "✅" if slot_info.get("active", True) else "❌"
                capacity = slot_info.get("capacity", "?")
                print(f"     {pos_key}: {status} Cap={capacity}")
    else:
        print("   (Empty - using fallback SHELF_CONFIG)")
    
    # 4. Current DB state summary
    print(f"💾 DATABASE SHELF_STATE ({len(DB.get('shelf_state', []))} cells):")
    if DB.get("shelf_state"):
        occupied_count = 0
        for cell in DB["shelf_state"]:
            if len(cell) >= 3 and cell[2]:  # มี lots
                occupied_count += 1
        print(f"   Total cells: {len(DB['shelf_state'])}")
        print(f"   Occupied cells: {occupied_count}")
        print(f"   Empty cells: {len(DB['shelf_state']) - occupied_count}")
        
        # แสดงรายละเอียดช่องที่มีของ
        if occupied_count > 0:
            print("   📦 Occupied positions:")
            for cell in DB["shelf_state"]:
                if len(cell) >= 3 and cell[2]:
                    level, block, lots = cell[0], cell[1], cell[2]
                    total_trays = sum(lot.get("tray_count", 0) for lot in lots)
                    capacity = get_cell_capacity(level, block)
                    usage_pct = round((total_trays / capacity) * 100, 1) if capacity > 0 else 0
                    print(f"     L{level}B{block}: {len(lots)} lots, {total_trays}/{capacity} trays ({usage_pct}%)")
    else:
        print("   (Empty)")
    
    # 5. Summary
    gateway_loaded = bool(DYNAMIC_LAYOUT)
    print(f"\n📊 SUMMARY:")
    print(f"   Gateway Layout Loaded: {'✅ Yes' if gateway_loaded else '❌ No (using fallback)'}")
    print(f"   Active Layout Source: {'Gateway' if gateway_loaded else 'Fallback SHELF_CONFIG'}")
    print(f"   Default Cell Capacity: {DEFAULT_CELL_CAPACITY}")
    print("="*50 + "\n")