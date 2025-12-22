#!/usr/bin/env python3
"""
Seed attendance data for testing Reports API
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timedelta, time
import random
from app.database import SessionLocal
from app.models.worker import Worker
from app.models.site import Site
from app.models.event import Device, ClockEvent


def generate_attendance_data():
    """Generate realistic attendance data for last 7 days"""
    db = SessionLocal()
    
    try:
        print("🌱 Seeding attendance data...")
        print("="*70)
        
        # Get all active workers and sites
        workers = db.query(Worker).filter(
            Worker.is_active == True,
            Worker.deleted_at.is_(None)
        ).all()
        
        sites = db.query(Site).filter(Site.deleted_at.is_(None)).all()
        
        if not workers:
            print("❌ No workers found! Run seed.py first.")
            return
        
        if not sites:
            print("❌ No sites found! Run seed.py first.")
            return
        
        print(f"📊 Found {len(workers)} workers and {len(sites)} sites")
        
        # Get or create device
        device = db.query(Device).first()
        if not device:
            device = Device(
                device_id="test-device-seed",
                device_name="Seed Device",
                organization_id=1,
                is_active=True
            )
            db.add(device)
            db.commit()
            db.refresh(device)
        
        # Generate data for last 7 days
        today = datetime.utcnow().date()
        events_created = 0
        
        for day_offset in range(7, 0, -1):
            target_date = today - timedelta(days=day_offset)
            print(f"\n📅 Generating data for {target_date}...")
            
            for worker in workers:
                # 80% chance worker shows up
                shows_up = random.random() < 0.8
                
                if not shows_up:
                    print(f"   ⚪ {worker.name}: Absent")
                    continue
                
                # Get worker's site
                site = db.query(Site).filter(Site.id == worker.site_id).first()
                if not site:
                    site = sites[0]
                
                # Determine check-in time
                if random.random() < 0.7:
                    # On time
                    check_in_hour = 6
                    check_in_minute = random.randint(0, 15)
                    status = "on time"
                else:
                    # Late
                    check_in_hour = random.randint(6, 7)
                    check_in_minute = random.randint(15, 59)
                    status = "late"
                
                check_in_dt = datetime.combine(
                    target_date,
                    time(check_in_hour, check_in_minute, random.randint(0, 59))
                )
                
                # Create check-in event
                check_in_event = ClockEvent(
                    worker_id=worker.id,
                    site_id=site.id,
                    device_id=device.id,
                    event_type="IN",
                    event_timestamp=check_in_dt,
                    gps_lat=site.gps_lat + random.uniform(-0.0001, 0.0001),
                    gps_lon=site.gps_lon + random.uniform(-0.0001, 0.0001),
                    accuracy_m=random.uniform(5, 20),
                    is_valid=True,
                    distance_m=random.uniform(0, 50)
                )
                db.add(check_in_event)
                events_created += 1
                
                # 90% chance they check out
                if random.random() < 0.9:
                    check_out_hour = random.randint(14, 17)
                    check_out_minute = random.randint(0, 59)
                    
                    check_out_dt = datetime.combine(
                        target_date,
                        time(check_out_hour, check_out_minute, random.randint(0, 59))
                    )
                    
                    check_out_event = ClockEvent(
                        worker_id=worker.id,
                        site_id=site.id,
                        device_id=device.id,
                        event_type="OUT",
                        event_timestamp=check_out_dt,
                        gps_lat=site.gps_lat + random.uniform(-0.0001, 0.0001),
                        gps_lon=site.gps_lon + random.uniform(-0.0001, 0.0001),
                        accuracy_m=random.uniform(5, 20),
                        is_valid=True,
                        distance_m=random.uniform(0, 50)
                    )
                    db.add(check_out_event)
                    events_created += 1
                    
                    hours = (check_out_dt - check_in_dt).total_seconds() / 3600
                    print(f"   ✅ {worker.name}: {status}, worked {hours:.1f}h")
                else:
                    print(f"   ⚠️  {worker.name}: {status}, no check-out")
        
        db.commit()
        
        print()
        print("="*70)
        print(f"✅ Successfully created {events_created} attendance events!")
        print()
        print("🚀 Ready to test Reports API!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    generate_attendance_data()
