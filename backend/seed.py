"""
Seed script to populate database with test data
Run with: python seed.py
"""
from app.database import SessionLocal, init_db
from app.models.user import Organization, User
from app.models.site import Site
from app.models.worker import Worker
from app.models.event import Device
from app.routes.auth import get_password_hash


def seed_database():
    """Create test data"""
    db = SessionLocal()
    
    try:
        # Initialize database (create tables)
        print("Creating database tables...")
        init_db()
        
        # Create organization
        print("Creating organization...")
        org = Organization(name="Test Farm")
        db.add(org)
        db.commit()
        db.refresh(org)
        
        # Create admin user
        print("Creating admin user...")
        admin = User(
            email="admin@clockout.com",
            hashed_password=get_password_hash("password123"),
            full_name="Admin User",
            role="admin",
            organization_id=org.id
        )
        db.add(admin)
        db.commit()
        
        # Create sites
        print("Creating test sites...")
        # Site 1: Lagos Farm (example coordinates)
        site1 = Site(
            name="Lagos Farm",
            organization_id=org.id,
            gps_lat=6.5244,
            gps_lon=3.3792,
            radius_m=100.0
        )
        
        # Site 2: Abuja Farm
        site2 = Site(
            name="Abuja Farm",
            organization_id=org.id,
            gps_lat=9.0765,
            gps_lon=7.3986,
            radius_m=150.0
        )
        
        db.add(site1)
        db.add(site2)
        db.commit()
        db.refresh(site1)
        db.refresh(site2)
        
        # Create workers
        print("Creating test workers...")
        workers_data = [
            ("John Doe", "+2348012345678", site1.id),
            ("Jane Smith", "+2348023456789", site1.id),
            ("Samuel Obi", "+2348034567890", site1.id),
            ("Mary Johnson", "+2348045678901", site2.id),
            ("David Williams", "+2348056789012", site2.id),
        ]
        
        for name, phone, site_id in workers_data:
            worker = Worker(
                name=name,
                phone=phone,
                organization_id=org.id,
                site_id=site_id
            )
            db.add(worker)
        
        db.commit()
        
        # Create test device
        print("Creating test device...")
        device = Device(
            device_id="test-device-001",
            device_name="Manager Phone - Test",
            organization_id=org.id,
            site_id=site1.id
        )
        db.add(device)
        db.commit()
        
        print("\n✅ Database seeded successfully!")
        print(f"\n📊 Created:")
        print(f"   - 1 Organization: {org.name}")
        print(f"   - 1 Admin User: admin@clockout.com (password: password123)")
        print(f"   - 2 Sites: {site1.name}, {site2.name}")
        print(f"   - 5 Workers")
        print(f"   - 1 Device: {device.device_id}")
        print(f"\n🚀 Start the API: uvicorn app.main:app --reload")
        print(f"📖 View docs: http://localhost:8000/docs")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()