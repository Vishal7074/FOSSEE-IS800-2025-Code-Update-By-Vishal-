# Osdag screening submission — Draft IS 800:2025

The partial implementation is in [is800_2025.py](src/osdag_core/utils/common/is800_2025.py). The [short report](Screening_Report.pdf) explains the selected changes, assumptions, coverage and outstanding engineering checks. The [migration register](IS800_Migration_Register.pdf) provides the longer inventory.

[Watch the 3:12 silent demonstration](https://vishal-is800-draft-calculator.fearlesspony2.chatgpt.site/screening-demo.mp4) or open [the included MP4](screening-demo.mp4).

From the repository root, run the tests with:

```sh
python -m pip install pytest
python -m pytest -q
```

To try the example in Git Bash:

```sh
PYTHONPATH=src python -c "from osdag_core.utils.common.is800_2025 import IS800_2025 as D; print(D.web_class(750, 10, 250, loading='mid-depth'))"
```

Expected output: `Compact`. The test suite covers selected provisions. Consult the report for limitations before interpreting results.
