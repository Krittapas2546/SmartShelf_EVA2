-- =====================================================
-- Smart Shelf Management Database Schema (Team Version)
-- =====================================================
-- Version: Team Standard v1.0
-- Date: September 9, 2025
-- Description: Updated schema based on team requirements

-- Drop existing tables if they exist (for clean recreation)
DROP TABLE IF EXISTS IoTShelfLog CASCADE;
DROP TABLE IF EXISTS IoTJobComplete CASCADE;
DROP TABLE IF EXISTS IoTJobQueue CASCADE;
DROP TABLE IF EXISTS IoTShelfPosition CASCADE;
DROP TABLE IF EXISTS IoTShelfConfig CASCADE;
DROP TABLE IF EXISTS IoTSystemLog CASCADE;
DROP TABLE IF EXISTS IoTShelfMaster CASCADE;

-- =====================================================
-- 1. MASTER TABLE
-- =====================================================
CREATE TABLE IoTShelfMaster (
    ShelfID VARCHAR NOT NULL,
    ShelfName VARCHAR NOT NULL,
    Ip VARCHAR NOT NULL,
    IsActive BOOLEAN DEFAULT TRUE,
    PRIMARY KEY(ShelfID)
);

-- =====================================================
-- 2. SYSTEM LOG TABLE
-- =====================================================
CREATE TABLE IoTSystemLog (
    SysLogID VARCHAR NOT NULL UNIQUE,
    ShelfID VARCHAR NOT NULL,
    EventType VARCHAR NOT NULL,
    Description TEXT,
    LotNo VARCHAR NOT NULL,
    Level VARCHAR NOT NULL,
    Block VARCHAR NOT NULL,
    PlaceFlg VARCHAR NOT NULL,
    TrayCount VARCHAR NOT NULL,
    ResponseStatus VARCHAR,
    LmsRequest JSON,
    ShelfResponse JSON,
    CreateDate TIMESTAMP,
    PRIMARY KEY(SysLogID)
);

-- =====================================================
-- 3. SHELF CONFIGURATION TABLE
-- =====================================================
CREATE TABLE IoTShelfConfig (
    ConfigID VARCHAR NOT NULL UNIQUE,
    ShelfID VARCHAR NOT NULL,
    Level VARCHAR NOT NULL,
    Block VARCHAR NOT NULL,
    ShowLotName VARCHAR,
    ShowTrayCount VARCHAR,
    EmptyColor VARCHAR,
    HasItemColor VARCHAR NOT NULL,
    SelectedColor VARCHAR,
    ErrorColor VARCHAR,
    PRIMARY KEY(ConfigID)
);

-- =====================================================
-- 4. SHELF POSITION TABLE
-- =====================================================
CREATE TABLE IoTShelfPosition (
    PositionID VARCHAR NOT NULL UNIQUE,
    ShelfID VARCHAR NOT NULL,
    Level VARCHAR NOT NULL,
    Block VARCHAR NOT NULL,
    Capacity VARCHAR NOT NULL,
    Position_Status VARCHAR,
    CurrentLotNo VARCHAR,
    CurrentTrayCount INTEGER,
    Last_Updated TIMESTAMP,
    Create_At TIMESTAMP,
    PRIMARY KEY(PositionID)
);

-- =====================================================
-- 5. JOB QUEUE TABLE
-- =====================================================
CREATE TABLE IoTJobQueue (
    JobID VARCHAR NOT NULL UNIQUE,
    ShelfID VARCHAR NOT NULL,
    LotNo VARCHAR NOT NULL,
    Level VARCHAR NOT NULL,
    Block VARCHAR NOT NULL,
    PlaceFlg VARCHAR NOT NULL,
    TrayCount VARCHAR NOT NULL,
    Status VARCHAR,
    CreateAt TIMESTAMP,
    ErrorMessage TEXT,
    PRIMARY KEY(JobID)
);

-- =====================================================
-- 6. JOB COMPLETE TABLE
-- =====================================================
CREATE TABLE IoTJobComplete (
    CompleteID VARCHAR NOT NULL UNIQUE,
    JobID VARCHAR NOT NULL,
    LotNo VARCHAR NOT NULL,
    Level VARCHAR NOT NULL,
    Block VARCHAR NOT NULL,
    PlaceFlg VARCHAR NOT NULL,
    TrayCount VARCHAR NOT NULL,
    Status VARCHAR,
    CompleteAt TIMESTAMP,
    PRIMARY KEY(CompleteID)
);

-- =====================================================
-- 7. SHELF LOG TABLE (UPDATED)
-- =====================================================
CREATE TABLE IoTShelfLog (
    ShelfLogID VARCHAR NOT NULL UNIQUE,
    ShelfID VARCHAR,
    EventType VARCHAR,
    Level VARCHAR,
    Block VARCHAR,
    LotNo VARCHAR,
    EventData JSON,
    Status VARCHAR,
    Create_At TIMESTAMP,
    PRIMARY KEY(ShelfLogID)
);

-- =====================================================
-- 8. FOREIGN KEY CONSTRAINTS
-- =====================================================

-- IoTShelfConfig foreign key
ALTER TABLE IoTShelfConfig
ADD FOREIGN KEY(ShelfID) REFERENCES IoTShelfMaster(ShelfID)
ON UPDATE NO ACTION ON DELETE NO ACTION;

-- IoTSystemLog foreign key
ALTER TABLE IoTSystemLog
ADD FOREIGN KEY(ShelfID) REFERENCES IoTShelfMaster(ShelfID)
ON UPDATE NO ACTION ON DELETE NO ACTION;

-- IoTShelfPosition foreign key
ALTER TABLE IoTShelfPosition
ADD FOREIGN KEY(ShelfID) REFERENCES IoTShelfMaster(ShelfID)
ON UPDATE NO ACTION ON DELETE NO ACTION;

-- IoTJobQueue foreign key
ALTER TABLE IoTJobQueue
ADD FOREIGN KEY(ShelfID) REFERENCES IoTShelfMaster(ShelfID)
ON UPDATE NO ACTION ON DELETE NO ACTION;

-- IoTJobComplete foreign key
ALTER TABLE IoTJobComplete
ADD FOREIGN KEY(JobID) REFERENCES IoTJobQueue(JobID)
ON UPDATE NO ACTION ON DELETE NO ACTION;

-- IoTShelfLog foreign key (เฉพาะที่จำเป็น)
ALTER TABLE IoTShelfLog
ADD FOREIGN KEY(ShelfID) REFERENCES IoTShelfMaster(ShelfID)
ON UPDATE NO ACTION ON DELETE NO ACTION;

-- =====================================================
-- 9. SAMPLE DATA (Optional)
-- =====================================================

-- Insert sample shelf master
INSERT INTO IoTShelfMaster (ShelfID, ShelfName, Ip, IsActive) VALUES 
('SHELF_001', 'Smart Shelf 01', 'localhost', TRUE),
('SHELF_002', 'Smart Shelf 02', '192.168.1.101', TRUE);

-- Insert sample configurations with color settings
INSERT INTO IoTShelfConfig (ConfigID, ShelfID, Level, Block, ShowLotName, ShowTrayCount, EmptyColor, HasItemColor, SelectedColor, ErrorColor) VALUES 
('CFG_S001_L1B1', 'SHELF_001', '1', '1', 'Y', 'Y', '#E5E5E5', '#28A745', '#007BFF', '#DC3545'),
('CFG_S001_L1B2', 'SHELF_001', '1', '2', 'Y', 'Y', '#E5E5E5', '#28A745', '#007BFF', '#DC3545'),
('CFG_S001_L2B1', 'SHELF_001', '2', '1', 'Y', 'Y', '#E5E5E5', '#28A745', '#007BFF', '#DC3545'),
('CFG_S001_L2B2', 'SHELF_001', '2', '2', 'Y', 'Y', '#E5E5E5', '#28A745', '#007BFF', '#DC3545');

-- Insert sample positions
INSERT INTO IoTShelfPosition (PositionID, ShelfID, Level, Block, Capacity, Position_Status, Create_At) VALUES 
('POS_SHELF_001_L1B1', 'SHELF_001', '1', '1', '24', 'AVAILABLE', CURRENT_TIMESTAMP),
('POS_SHELF_001_L1B2', 'SHELF_001', '1', '2', '24', 'AVAILABLE', CURRENT_TIMESTAMP),
('POS_SHELF_001_L2B1', 'SHELF_001', '2', '1', '24', 'OCCUPIED', CURRENT_TIMESTAMP),
('POS_SHELF_001_L2B2', 'SHELF_001', '2', '2', '24', 'AVAILABLE', CURRENT_TIMESTAMP);

-- Update occupied position with sample data
UPDATE IoTShelfPosition 
SET CurrentLotNo = 'A123456AA.01', CurrentTrayCount = 12, Last_Updated = CURRENT_TIMESTAMP
WHERE PositionID = 'POS_SHELF_001_L2B1';

-- Insert sample job queue
INSERT INTO IoTJobQueue (JobID, ShelfID, LotNo, Level, Block, PlaceFlg, TrayCount, Status, CreateAt) VALUES 
('JOB_001', 'SHELF_001', 'A111111AA.11', '1', '1', '1', '15', 'PENDING', CURRENT_TIMESTAMP),
('JOB_002', 'SHELF_001', 'B222222BB.22', '1', '2', '0', '8', 'PENDING', CURRENT_TIMESTAMP);

-- =====================================================
-- 10. VALIDATION QUERIES
-- =====================================================

-- Check all tables and record counts
SELECT 'IoTShelfMaster' as TableName, COUNT(*) as RecordCount FROM IoTShelfMaster
UNION ALL
SELECT 'IoTSystemLog' as TableName, COUNT(*) as RecordCount FROM IoTSystemLog  
UNION ALL
SELECT 'IoTShelfConfig' as TableName, COUNT(*) as RecordCount FROM IoTShelfConfig
UNION ALL
SELECT 'IoTShelfPosition' as TableName, COUNT(*) as RecordCount FROM IoTShelfPosition
UNION ALL
SELECT 'IoTJobQueue' as TableName, COUNT(*) as RecordCount FROM IoTJobQueue
UNION ALL
SELECT 'IoTJobComplete' as TableName, COUNT(*) as RecordCount FROM IoTJobComplete
UNION ALL
SELECT 'IoTShelfLog' as TableName, COUNT(*) as RecordCount FROM IoTShelfLog;

-- =====================================================
-- 11. SUCCESS MESSAGE
-- =====================================================

SELECT '🎉 Team Database Schema Created Successfully!' as Status,
       '📋 Tables: 7 tables created with foreign key constraints' as Details,
       '🚀 Ready for Smart Shelf System Integration' as ReadyState;
-- =====================================================
-- Smart Shelf Management Database Schema (Test Version)
-- =====================================================
-- Version: Test v1.0
-- Date: September 9, 2025
-- Description: Simple table for testing with SHELF_CONFIG = {1:6, 2:6, 3:6, 4:6}

-- Drop existing tables if they exist
DROP TABLE IF EXISTS IoTShelfLayout CASCADE;
DROP TABLE IF EXISTS IoTShelfMaster CASCADE;

-- =====================================================
-- 1. SHELF MASTER TABLE
-- =====================================================
CREATE TABLE IoTShelfMaster (
    ShelfID VARCHAR NOT NULL,
    ShelfName VARCHAR NOT NULL,
    Ip VARCHAR NOT NULL,
    IsActive BOOLEAN DEFAULT TRUE,
    CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(ShelfID)
);

-- =====================================================
-- 2. SHELF LAYOUT TABLE
-- =====================================================
CREATE TABLE IoTShelfLayout (
    LayoutID VARCHAR NOT NULL UNIQUE,
    ShelfID VARCHAR NOT NULL,
    Level VARCHAR NOT NULL,
    Block VARCHAR NOT NULL,
    PositionName VARCHAR,
    Capacity INTEGER DEFAULT 40,
    IsActive BOOLEAN DEFAULT TRUE,
    PRIMARY KEY(LayoutID)
);

-- =====================================================
-- 3. FOREIGN KEY CONSTRAINT
-- =====================================================
ALTER TABLE IoTShelfLayout
ADD FOREIGN KEY(ShelfID) REFERENCES IoTShelfMaster(ShelfID)
ON UPDATE NO ACTION ON DELETE CASCADE;

-- =====================================================
-- 4. SAMPLE DATA - SHELF MASTER
-- =====================================================
INSERT INTO IoTShelfMaster (ShelfID, ShelfName, Ip, IsActive) VALUES 
('SHELF_001', 'Test Shelf 001', '192.168.1.101', TRUE);

-- =====================================================
-- 5. SAMPLE DATA - SHELF LAYOUT (4 Levels, 6 Blocks each, 40 Tray Capacity)
-- =====================================================

-- Level 1: 6 Blocks
INSERT INTO IoTShelfLayout (LayoutID, ShelfID, Level, Block, PositionName, Capacity) VALUES 
('LAY_S001_L1B1', 'SHELF_001', '1', '1', 'L1-B1', 40),
('LAY_S001_L1B2', 'SHELF_001', '1', '2', 'L1-B2', 40),
('LAY_S001_L1B3', 'SHELF_001', '1', '3', 'L1-B3', 40),
('LAY_S001_L1B4', 'SHELF_001', '1', '4', 'L1-B4', 40),
('LAY_S001_L1B5', 'SHELF_001', '1', '5', 'L1-B5', 40),
('LAY_S001_L1B6', 'SHELF_001', '1', '6', 'L1-B6', 40);

-- Level 2: 6 Blocks  
INSERT INTO IoTShelfLayout (LayoutID, ShelfID, Level, Block, PositionName, Capacity) VALUES 
('LAY_S001_L2B1', 'SHELF_001', '2', '1', 'L2-B1', 40),
('LAY_S001_L2B2', 'SHELF_001', '2', '2', 'L2-B2', 40),
('LAY_S001_L2B3', 'SHELF_001', '2', '3', 'L2-B3', 40),
('LAY_S001_L2B4', 'SHELF_001', '2', '4', 'L2-B4', 40),
('LAY_S001_L2B5', 'SHELF_001', '2', '5', 'L2-B5', 40),
('LAY_S001_L2B6', 'SHELF_001', '2', '6', 'L2-B6', 40);

-- Level 3: 6 Blocks
INSERT INTO IoTShelfLayout (LayoutID, ShelfID, Level, Block, PositionName, Capacity) VALUES 
('LAY_S001_L3B1', 'SHELF_001', '3', '1', 'L3-B1', 40),
('LAY_S001_L3B2', 'SHELF_001', '3', '2', 'L3-B2', 40),
('LAY_S001_L3B3', 'SHELF_001', '3', '3', 'L3-B3', 40),
('LAY_S001_L3B4', 'SHELF_001', '3', '4', 'L3-B4', 40),
('LAY_S001_L3B5', 'SHELF_001', '3', '5', 'L3-B5', 40),
('LAY_S001_L3B6', 'SHELF_001', '3', '6', 'L3-B6', 40);

-- Level 4: 6 Blocks
INSERT INTO IoTShelfLayout (LayoutID, ShelfID, Level, Block, PositionName, Capacity) VALUES 
('LAY_S001_L4B1', 'SHELF_001', '4', '1', 'L4-B1', 40),
('LAY_S001_L4B2', 'SHELF_001', '4', '2', 'L4-B2', 40),
('LAY_S001_L4B3', 'SHELF_001', '4', '3', 'L4-B3', 40),
('LAY_S001_L4B4', 'SHELF_001', '4', '4', 'L4-B4', 40),
('LAY_S001_L4B5', 'SHELF_001', '4', '5', 'L4-B5', 40),
('LAY_S001_L4B6', 'SHELF_001', '4', '6', 'L4-B6', 40);

-- =====================================================
-- 6. TEST FUNCTIONS
-- =====================================================

-- Function: Get shelf layout as JSON for JavaScript  
CREATE OR REPLACE FUNCTION get_shelf_layout_json(shelf_id VARCHAR)
RETURNS JSON AS $$
DECLARE
    layout_data JSON;
BEGIN
    SELECT json_object_agg(Level, block_count) INTO layout_data
    FROM (
        SELECT Level, COUNT(Block) as block_count
        FROM IoTShelfLayout 
        WHERE ShelfID = shelf_id AND IsActive = TRUE
        GROUP BY Level
        ORDER BY Level::INTEGER
    ) grouped;
    
    RETURN COALESCE(layout_data, '{}'::JSON);
END;
$$ LANGUAGE plpgsql;

-- Function: Get all positions for a shelf
CREATE OR REPLACE FUNCTION get_shelf_positions(shelf_id VARCHAR)
RETURNS TABLE(
    layout_id VARCHAR,
    level VARCHAR,
    block VARCHAR,
    position_name VARCHAR,
    capacity INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT sl.LayoutID, sl.Level, sl.Block, sl.PositionName, sl.Capacity
    FROM IoTShelfLayout sl
    WHERE sl.ShelfID = shelf_id AND sl.IsActive = TRUE
    ORDER BY sl.Level::INTEGER, sl.Block::INTEGER;
END;
$$ LANGUAGE plpgsql;

-- Function: Get capacity for specific position
CREATE OR REPLACE FUNCTION get_position_capacity(shelf_id VARCHAR, level VARCHAR, block VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    capacity_value INTEGER;
BEGIN
    SELECT Capacity INTO capacity_value
    FROM IoTShelfLayout
    WHERE ShelfID = shelf_id AND Level = level AND Block = block AND IsActive = TRUE;
    
    RETURN COALESCE(capacity_value, 0);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 7. TEST QUERIES
-- =====================================================

-- Test 1: Check layout JSON (should return {"1":6, "2":6, "3":6, "4":6})
SELECT 'Test 1: Layout JSON' as TestName, get_shelf_layout_json('SHELF_001') as Result;

-- Test 2: Count positions per level
SELECT 'Test 2: Positions per Level' as TestName;
SELECT 
    Level,
    COUNT(Block) as TotalBlocks,
    SUM(Capacity) as TotalCapacity
FROM IoTShelfLayout 
WHERE ShelfID = 'SHELF_001' AND IsActive = TRUE
GROUP BY Level
ORDER BY Level::INTEGER;

-- Test 3: All positions summary
SELECT 'Test 3: All Positions Summary' as TestName;
SELECT 
    Level || '-' || Block as Position,
    PositionName,
    Capacity || ' Tray' as MaxCapacity
FROM IoTShelfLayout
WHERE ShelfID = 'SHELF_001' AND IsActive = TRUE
ORDER BY Level::INTEGER, Block::INTEGER;

-- Test 4: Verify structure matches SHELF_CONFIG
SELECT 'Test 4: Verify SHELF_CONFIG' as TestName;
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM IoTShelfLayout WHERE ShelfID = 'SHELF_001' AND Level = '1') = 6 AND
             (SELECT COUNT(*) FROM IoTShelfLayout WHERE ShelfID = 'SHELF_001' AND Level = '2') = 6 AND
             (SELECT COUNT(*) FROM IoTShelfLayout WHERE ShelfID = 'SHELF_001' AND Level = '3') = 6 AND
             (SELECT COUNT(*) FROM IoTShelfLayout WHERE ShelfID = 'SHELF_001' AND Level = '4') = 6
        THEN '✅ SHELF_CONFIG {1:6, 2:6, 3:6, 4:6} VERIFIED'
        ELSE '❌ SHELF_CONFIG MISMATCH'
    END as Verification;

-- Test 5: Test capacity function
SELECT 'Test 5: Capacity Test' as TestName;
SELECT 
    'L1B1 Capacity: ' || get_position_capacity('SHELF_001', '1', '1') || ' Tray' as CapacityTest1,
    'L4B6 Capacity: ' || get_position_capacity('SHELF_001', '4', '6') || ' Tray' as CapacityTest2;

-- Test 6: Total shelf statistics
SELECT 'Test 6: Shelf Statistics' as TestName;
SELECT 
    COUNT(*) as TotalPositions,
    COUNT(DISTINCT Level) as TotalLevels,
    MAX(Capacity) as MaxCapacityPerPosition,
    SUM(Capacity) as TotalShelfCapacity
FROM IoTShelfLayout 
WHERE ShelfID = 'SHELF_001' AND IsActive = TRUE;

-- =====================================================
-- 8. SUCCESS MESSAGE  
-- =====================================================
SELECT '🎉 Test Database Created Successfully!' as Status,
       '📊 Configuration: 4 Levels × 6 Blocks = 24 Positions' as Layout,
       '📦 Capacity: 40 Tray per Position' as Capacity,
       '🔢 Total: 960 Tray capacity' as TotalCapacity;