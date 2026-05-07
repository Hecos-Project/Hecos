"""
MODULE: Calendar Sync Manager
DESCRIPTION: Handles fetching and parsing of external iCal feeds (Google, Apple, Outlook).
"""

import requests
from icalendar import Calendar
from datetime import datetime, date
import pytz
from hecos.core.logging import logger
from hecos.plugins.calendar import store

def sync_all(sync_urls):
    """Syncs all configured external calendar URLs."""
    if not sync_urls:
        return 0
    
    total_new = 0
    for url in sync_urls:
        try:
            logger.info("CALENDAR", f"Syncing external feed: {url[:30]}...")
            data = fetch_ics(url)
            if data:
                count = parse_and_store(data, url)
                total_new += count
                logger.info("CALENDAR", f"Sync complete for {url[:30]}. Events processed: {count}")
        except Exception as e:
            logger.error(f"Failed to sync {url}: {e}")
            
    return total_new

def fetch_ics(url):
    """Fetches the .ics data from a URL."""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error fetching ICS from {url}: {e}")
        return None

def parse_and_store(ics_data, source_url):
    """Parses ICS data and updates the local store."""
    try:
        cal = Calendar.from_ical(ics_data)
        count = 0
        
        # Get all existing external events from this source to identify deletions (optional, but good for cleanliness)
        # For now, we focus on Upsert (Add/Update)
        
        for component in cal.walk():
            if component.name == "VEVENT":
                uid = str(component.get('uid'))
                title = str(component.get('summary'))
                start = component.get('dtstart').dt
                end = component.get('dtend').dt if component.get('dtend') else None
                notes = str(component.get('description')) if component.get('description') else None
                
                # Handle date vs datetime
                start_iso = _to_iso(start)
                end_iso = _to_iso(end) if end else None
                all_day = isinstance(start, date) and not isinstance(start, datetime)
                
                # Check if exists
                existing = _find_by_external_id(uid)
                if existing:
                    # Update if changed (simple check for title/start)
                    if existing['title'] != title or existing['start_iso'] != start_iso:
                        store.update(existing['id'], title=title, start_iso=start_iso, end_iso=end_iso, all_day=all_day, notes=notes)
                else:
                    # Add new
                    store.add(
                        title=title,
                        start_iso=start_iso,
                        end_iso=end_iso,
                        all_day=all_day,
                        external_id=uid,
                        sync_source=source_url,
                        notes=notes,
                        color="#3498db" # Default sync color (Blue-ish)
                    )
                    count += 1
        return count
    except Exception as e:
        logger.error(f"Error parsing ICS data: {e}")
        return 0

def _to_iso(dt_obj):
    """Converts date/datetime to ISO string."""
    if isinstance(dt_obj, datetime):
        # Ensure it's in UTC or naive for the store
        if dt_obj.tzinfo:
            dt_obj = dt_obj.astimezone(pytz.UTC).replace(tzinfo=None)
        return dt_obj.isoformat()
    elif isinstance(dt_obj, date):
        return datetime.combine(dt_obj, datetime.min.time()).isoformat()
    return str(dt_obj)

def _find_by_external_id(uid):
    """Helper to find an event by its external UID."""
    conn = store._get_conn()
    try:
        row = conn.execute("SELECT * FROM calendar_events WHERE external_id = ?", (uid,)).fetchone()
        return store._row_to_dict(row) if row else None
    finally:
        conn.close()
