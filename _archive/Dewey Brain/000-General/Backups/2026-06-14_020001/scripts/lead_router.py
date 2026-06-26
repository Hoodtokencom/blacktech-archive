#!/usr/bin/env python3
"""
lead_router.py — Unified Lead Intake Module
Blacktech Solutions Corp Pi System

Shared module that ANY server can import to write a lead into blacktech_core.db.

Usage:
    import sys
    sys.path.insert(0, '/home/allenai/scripts')
    from lead_router import intake_lead

    result = intake_lead(
        source='telegram',
        name='John Smith',
        phone='7735551234',
        email='john@example.com',
        address='1234 S MLK Dr',
        city='Chicago',
        state='IL',
        services=['panel upgrade'],
        notes='Referred by Mike',
        raw=None
    )
    # Returns: {'contact_id': 'BSC-CUST-XXXXXXXX', 'job_id': 'BSC-JOB-XXXXXXXX', 'ok': True}
"""

import sqlite3
import uuid
import json
import logging
from datetime import datetime

DB_PATH = '/home/allenai/data/blacktech_core.db'

log = logging.getLogger('lead_router')


def _gen_id(prefix):
    """Generate a BSC-style ID: prefix-XXXXXXXX (8 uppercase hex chars)."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def _determine_job_type(source):
    """Determine job type from source string."""
    if source == 'comed':
        return 'comed'
    elif 'think' in source.lower():
        return 'think_energy'
    else:
        return 'electrical'


def intake_lead(
    source,
    name,
    phone='',
    email='',
    address='',
    city='Chicago',
    state='IL',
    services=None,
    notes='',
    raw=None
):
    """
    Write a new lead into blacktech_core.db.

    Parameters:
        source   : str  — 'telegram' | 'comed' | 'web-form' | 'kanban' | 'think-energy' | 'manual'
        name     : str  — Customer full name
        phone    : str  — Customer phone number
        email    : str  — Customer email address
        address  : str  — Street address
        city     : str  — City (default: 'Chicago')
        state    : str  — State abbreviation (default: 'IL')
        services : list — List of service strings (e.g. ['panel upgrade', 'rewire'])
        notes    : str  — Free-form notes
        raw      : any  — Original raw payload (stored as JSON string in notes if provided)

    Returns:
        dict — {'contact_id': 'BSC-CUST-XXXXXXXX', 'job_id': 'BSC-JOB-XXXXXXXX', 'ok': True}
              or {'ok': False, 'error': '...'} on failure
    """
    if services is None:
        services = []

    try:
        contact_id = _gen_id('BSC-CUST')
        job_id     = _gen_id('BSC-JOB')
        now        = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        job_type   = _determine_job_type(source)

        # Build scope from services list
        scope = ', '.join(services) if services else ''

        # Append raw payload to notes if provided
        full_notes = notes or ''
        if raw is not None:
            try:
                raw_str = json.dumps(raw) if not isinstance(raw, str) else raw
                full_notes = (full_notes + '\n\nraw: ' + raw_str).strip()
            except Exception:
                pass

        # Build job title
        title = f"Lead — {name}" if name else "Lead"

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        try:
            with conn:
                # 1. Insert contact
                conn.execute(
                    """
                    INSERT INTO contacts
                        (id, name, phone, email, address, city, state,
                         type, source, status, notes, created_at, updated_at)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?,
                         'lead', ?, 'new', ?, ?, ?)
                    """,
                    (contact_id, name, phone, email, address, city, state,
                     source, full_notes, now, now)
                )

                # 2. Insert job
                conn.execute(
                    """
                    INSERT INTO jobs
                        (id, contact_id, title, scope, address, city, state,
                         type, status, source, notes, created_at, updated_at)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?,
                         ?, 'lead', ?, ?, ?, ?)
                    """,
                    (job_id, contact_id, title, scope, address, city, state,
                     job_type, source, full_notes, now, now)
                )

                # 3. Audit log
                conn.execute(
                    """
                    INSERT INTO audit_log
                        (entity, entity_id, action, new_value, created_at)
                    VALUES
                        ('job', ?, 'lead_intake', ?, ?)
                    """,
                    (
                        job_id,
                        json.dumps({
                            'contact_id': contact_id,
                            'name': name,
                            'source': source,
                            'type': job_type
                        }),
                        now
                    )
                )

        finally:
            conn.close()

        log.info(f"[lead_router] intake_lead OK — {job_id} ({name}, source={source})")
        return {'contact_id': contact_id, 'job_id': job_id, 'ok': True}

    except Exception as e:
        log.error(f"[lead_router] intake_lead FAILED — {e}")
        return {'ok': False, 'error': str(e)}
