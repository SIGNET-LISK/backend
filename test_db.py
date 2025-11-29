#!/usr/bin/env python3
"""
Test script to verify database and indexer
"""
import os
from dotenv import load_dotenv

load_dotenv()

from indexer.db import SessionLocal, engine
from models.content import Base, Content

print("=" * 60)
print("DATABASE & INDEXER TEST")
print("=" * 60)

# Test 1: Database connection
print("\n1️⃣  Testing database connection...")
try:
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Database connection successful!")
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    exit(1)

# Test 2: Create tables
print("\n2️⃣  Creating tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created/verified!")
except Exception as e:
    print(f"❌ Failed to create tables: {e}")
    exit(1)

# Test 3: Check existing content
print("\n3️⃣  Checking existing content in database...")
try:
    db = SessionLocal()
    count = db.query(Content).count()
    db.close()
    print(f"✅ Found {count} content records in database")
    
    if count > 0:
        db = SessionLocal()
        contents = db.query(Content).limit(5).all()
        for c in contents:
            print(f"  - phash: {c.phash[:16]}... | title: {c.title}")
        db.close()
except Exception as e:
    print(f"❌ Failed to query database: {e}")
    exit(1)

# Test 4: Check indexer
print("\n4️⃣  Checking indexer...")
try:
    from indexer.search import get_verifier
    verifier = get_verifier()
    element_count = verifier.p.element_count
    print(f"✅ Indexer has {element_count} items indexed")
    
    if element_count != count:
        print(f"⚠️  WARNING: Index count ({element_count}) != DB count ({count})")
        print("   This means indexer and database are out of sync!")
except Exception as e:
    print(f"❌ Failed to check indexer: {e}")
    exit(1)

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
