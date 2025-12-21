#!/usr/bin/env python3
"""
Fix subscription plan constraint
"""
from app.database import SessionLocal
from sqlalchemy import text

def fix_constraint():
    db = SessionLocal()
    
    try:
        print("Dropping old constraint...")
        db.execute(text("""
            ALTER TABLE organizations 
            DROP CONSTRAINT IF EXISTS chk_org_subscription_plan
        """))
        
        print("Adding new constraint with all plan values...")
        db.execute(text("""
            ALTER TABLE organizations 
            ADD CONSTRAINT chk_org_subscription_plan 
            CHECK (subscription_plan IN ('free', 'trial', 'starter', 'pro', 'enterprise'))
        """))
        
        print("Updating subscription_status constraint...")
        db.execute(text("""
            ALTER TABLE organizations 
            DROP CONSTRAINT IF EXISTS chk_org_subscription_status
        """))
        
        db.execute(text("""
            ALTER TABLE organizations 
            ADD CONSTRAINT chk_org_subscription_status 
            CHECK (subscription_status IN ('trial', 'active', 'suspended', 'cancelled', 'expired'))
        """))
        
        db.commit()
        print("\n✅ Constraints updated successfully!")
        print("   - subscription_plan now allows: free, trial, starter, pro, enterprise")
        print("   - subscription_status now allows: trial, active, suspended, cancelled, expired")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_constraint()