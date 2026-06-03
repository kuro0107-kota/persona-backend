import importlib.metadata

for dist in importlib.metadata.distributions():
    try:
        eps = dist.entry_points
    except Exception as e:
        print(f"FAILED on {dist.metadata.get('Name')}: {e}")
        if hasattr(dist, '_path'):
            print(dist._path)
