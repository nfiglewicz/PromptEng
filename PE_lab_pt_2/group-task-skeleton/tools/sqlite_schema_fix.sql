-- ==================================================
-- WARNING: BACK UP YOUR DATABASE BEFORE RUNNING THIS SCRIPT!
-- ==================================================

-- Fix column names in the 'trips' table
ALTER TABLE main.trips RENAME COLUMN "﻿route_id" TO route_id;

-- Fix column names in the 'stops' table
ALTER TABLE main.stops RENAME COLUMN "﻿stop_id" TO stop_id;

-- Fix column names in the 'stop_times' table
ALTER TABLE main.stop_times RENAME COLUMN "﻿trip_id" TO trip_id;

--
-- ==================================================
-- Verification (Optional but Recommended)
-- ==================================================
-- PRAGMA table_info(trips);
-- PRAGMA table_info(stops);
-- PRAGMA table_info(stop_times);
-- ==================================================