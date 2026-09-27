## Build & test

```bash
python -m pytest -q                                   # 456 tests, keep green
cd chunkscan && ./gradlew build test -q                # 384 tests; writes build/libs/chunkscan-<ver>.jar
python chunkscan/verify_synthetic.py                   # Java writer vs Python reader, block for block
```
Jack uploads the jar through the launcher himself — **do not copy it into `custom_mods/`**, that
creates a duplicate mod id and Fabric refuses to start.

