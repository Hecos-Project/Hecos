"""
End-to-end pipeline test for net_search clear mode engines.
Run with: c:\Hecos\python_env\python.exe c:\Hecos\hecos\scratch\test_pipeline.py
"""
import sys, time
sys.path.insert(0, r'c:\Hecos')

try:
    from hecos.modules.net_search.search.engines import get_engines_for_mode
    from hecos.modules.net_search.search.models import SearchQuery
    print('[OK] Imports successful')
except Exception as e:
    print(f'[ERR] Import failed: {e}')
    sys.exit(1)

query = SearchQuery(query='open source news 2024', mode='clear', limit=50, safe_search=False)
engines = get_engines_for_mode('clear')
print(f'\nActive engines for clear mode: {[e.id for e in engines]}')
print('=' * 60)

total = 0
for eng in engines:
    t0 = time.time()
    try:
        results = eng.search(query)
        elapsed = time.time() - t0
        print(f'  [{eng.id}]: {len(results)} results ({elapsed:.1f}s)')
        total += len(results)
    except Exception as e:
        elapsed = time.time() - t0
        print(f'  [{eng.id}]: ERROR ({elapsed:.1f}s) - {type(e).__name__}: {e}')

print('=' * 60)
print(f'TOTAL pre-dedup: {total} results')

