#!/usr/bin/env python3
"""Export the catalog into a single JSON payload for the knowledge-base builder.

The catalog in `build/rfp-automation-kit/rfpkit/catalog_data.py` stays the source of
truth. This pulls it — plus the vendor profile and past-performance case studies
from the generator's company profile — into one file the Node/docx builder reads,
so the Word documents can never disagree with what the skill and samples use.

    python build/tools/export_knowledge_data.py   # -> build/knowledge-data.json
"""

import json
import sys
from pathlib import Path

SAMPLE = Path(__file__).resolve().parents[2]
REPO = SAMPLE
sys.path.insert(0, str(SAMPLE / "build" / "rfp-automation-kit"))
sys.path.insert(0, str(SAMPLE / "build" / "rfp-sample-generator"))


def main():
    from rfpkit.catalog_data import (OFFERINGS, PRODUCT_LINES, RESPONSE_LIBRARY,
                                     VENDOR)
    # Case studies and capability blurbs live with the original sample generator.
    from rfpgen.company import VENDOR as PROFILE

    payload = {
        "vendor": {
            **VENDOR,
            "overview": PROFILE.overview,
            "capabilities": list(PROFILE.capabilities),
            "differentiators": list(PROFILE.differentiators),
            "tech_stack": list(PROFILE.tech_stack),
            "case_studies": {k: list(v) for k, v in PROFILE.case_studies.items()},
        },
        "product_lines": PRODUCT_LINES,
        "offerings": OFFERINGS,
        "response_library_topics": [
            {"key": k, "title": v["title"]} for k, v in RESPONSE_LIBRARY.items()
        ],
    }

    out = SAMPLE / "build" / "knowledge-data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)}  "
          f"({len(OFFERINGS)} offerings, {len(PRODUCT_LINES)} product lines, "
          f"{sum(len(v) for v in payload['vendor']['case_studies'].values())} case studies)")


if __name__ == "__main__":
    main()
