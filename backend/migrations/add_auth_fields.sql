-- 1. Add mode field to users table
ALTER TABLE users 
ADD COLUMN mode VARCHAR(20) DEFAULT 'manager' CHECK (mode IN ('manager', 'receiver', 'admin'));

-- 2. Create user_sites junction table (managers can have multiple sites)
CREATE TABLE user_sites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, site_id)
);

-- 3. Add NFC-ready fields to clock_events (for future Stage 4)
ALTER TABLE clock_events 
ADD COLUMN checkpoint_id INTEGER REFERENCES checkpoints(id),
ADD COLUMN nfc_tag_id VARCHAR(50);

-- 4. Create checkpoints table (NFC locations - future use)
CREATE TABLE checkpoints (
    id SERIAL PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    checkpoint_type VARCHAR(20) CHECK (checkpoint_type IN ('entry', 'exit', 'task')),
    nfc_tag_id VARCHAR(50),
    location_lat DECIMAL(10,8),
    location_lng DECIMAL(11,8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Update existing admin user to have mode
UPDATE users SET mode = 'admin' WHERE role = 'admin';

-- 6. Add device_mode to devices table
ALTER TABLE devices 
ADD COLUMN device_mode VARCHAR(20) DEFAULT 'manager' CHECK (device_mode IN ('manager', 'receiver'));

-- 7. Create indexes for performance
CREATE INDEX idx_user_sites_user ON user_sites(user_id);
CREATE INDEX idx_user_sites_site ON user_sites(site_id);
CREATE INDEX idx_events_checkpoint ON clock_events(checkpoint_id);
CREATE INDEX idx_events_nfc_tag ON clock_events(nfc_tag_id);