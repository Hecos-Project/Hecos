import os, json, subprocess

os.makedirs('c:\\Hecos\\test_pkg', exist_ok=True)
with open('c:\\Hecos\\test_pkg\\hpkg_manifest.json', 'w') as f:
    json.dump({'id':'test_pkg','name':'Test','version':'1.0.0','type':'plugin','hecos_min_version':'0.1.0','target_dir':'plugins'}, f)
with open('c:\\Hecos\\test_pkg\\main.py', 'w') as f:
    f.write('print("Hello")')

print('Generating keys...')
subprocess.run(['python', 'c:\\Hecos\\scripts\\hpm_cli.py', 'keygen', '--out-dir', 'c:\\Hecos\\test_keys'], check=True)

print('Packing...')
subprocess.run(['python', 'c:\\Hecos\\scripts\\hpm_cli.py', 'pack', '--src', 'c:\\Hecos\\test_pkg', '--key', 'c:\\Hecos\\test_keys\\private.pem', '--out', 'c:\\Hecos\\test_pkg.hpkg'], check=True)
