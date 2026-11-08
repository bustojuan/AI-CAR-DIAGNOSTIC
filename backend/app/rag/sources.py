"""Researched source registry. Listing does not authorize ingestion."""

import json
from pathlib import Path

from app.models.vehicle import MVP_IDENTITY

SOURCES = [
    {
        "id": "internal_demo",
        "publisher": "AI Car Diagnostic project",
        "url": None,
        "applicability": "Generic automotive systems only",
        "license_status": "authorized",
        "verification_status": "internally_reviewed",
        "automatically_indexed": False,
        "note": "Locally authored demo corpus; never manufacturer evidence.",
    },
    {
        "id": "volkswagen_erwin",
        "publisher": "Volkswagen",
        "url": "https://volkswagen.erwin-store.com/erwin/showTermsOfBusiness.do",
        "applicability": "Vehicle-specific coverage must be checked with authorized access",
        "license_status": "unknown",
        "verification_status": "access_not_verified",
        "automatically_indexed": False,
        "note": "Access terms/registration apply; no credentials or indexing license held.",
    },
    {
        "id": "volkswagen_owners",
        "publisher": "Volkswagen UK",
        "url": "https://www.volkswagen.co.uk/en/owners-and-services/my-car/manuals-landing.html",
        "applicability": "Pre-2018 manuals: retailer assistance; 2009 manual not acquired",
        "license_status": "unknown",
        "verification_status": "not_acquired",
        "automatically_indexed": False,
        "note": "Owner literature differs from workshop procedures.",
    },
    {
        "id": "volkswagen_golf_plus_facts_2006",
        "publisher": "Volkswagen Sweden",
        "url": "https://www.volkswagen.se/idhub/content/dam/onehub_pkw/importers/se/"
        "hjalp-och-support/broschyrer/golf-plus/"
        "000.Golf_Plus_Fakta_2006_-_tryck_060620_-_VW535.download.pdf",
        "applicability": "June 2006 Swedish Golf Plus range; not verified for this vehicle",
        "license_status": "unknown",
        "verification_status": "publisher_download_verified",
        "automatically_indexed": False,
        "note": "Eight-page sales/specification brochure acquired for local reference review. "
        "Not an owner/workshop manual. No RAG permission established; not ingested or indexed.",
    },
    {
        "id": "volkswagen_golf_plus_facts_2005",
        "publisher": "Volkswagen Sweden",
        "url": "https://www.volkswagen.se/idhub/content/dam/onehub_pkw/importers/se/"
        "hjalp-och-support/broschyrer/golf-plus/"
        "000.Golf_Plus_Fakta_2005_-_tryck_050620.download.pdf",
        "applicability": "2005 Swedish Golf Plus range; reference comparison only",
        "license_status": "unknown",
        "verification_status": "publisher_download_verified",
        "automatically_indexed": False,
        "note": "Eight-page sales/specification brochure. Archive label and PDF filename dates "
        "differ. No RAG permission established; not ingested or indexed.",
    },
    {
        "id": "haynes_golf_plus_2005_2009",
        "publisher": "Haynes",
        "url": "https://us.haynes.com/products/"
        "vw-golf-04-sept-08-golf-plus-05-mar-09-jetta-06-09-haynes-repair-manual",
        "applicability": "Publisher lists Golf Plus 2005-March 2009, including 1968 cc diesel; "
        "UK/European specifications; exact engine variant unverified",
        "license_status": "restricted",
        "verification_status": "publisher_listing_checked_not_acquired",
        "automatically_indexed": False,
        "note": "Paid account-based online manual, not a free downloadable PDF. "
        "No purchase or RAG license obtained; separate publisher permission is needed.",
    },
    {
        "id": "volkswagen_golf_plus_facts_2009",
        "publisher": "Volkswagen Sweden",
        "url": "https://www.volkswagen.se/idhub/content/dam/onehub_pkw/importers/se/"
        "hjalp-och-support/broschyrer/golf-plus/"
        "000.Golf_Plus_Fakta_2009_-_tryck_090520_-_VW719.download.pdf",
        "applicability": "May 2009 Swedish Golf Plus range; exact CFFB applicability unverified",
        "license_status": "unknown",
        "verification_status": "publisher_download_verified",
        "automatically_indexed": False,
        "note": "Eight-page range brochure acquired after the owner corrected the year to 2009. "
        "Not a workshop manual; no RAG permission established and not ingested or indexed.",
    },
    {
        "id": "haynes_golf_plus_2009_2014",
        "publisher": "Haynes UK",
        "url": "https://uk.haynes.com/products/volkswagen-golf-plus-mk6-52-from-2009-to-2014",
        "applicability": "Publisher lists Golf Plus Mk6 (52), 2009-2014; "
        "public page does not confirm CFFB-specific coverage",
        "license_status": "restricted",
        "verification_status": "publisher_listing_checked_not_acquired",
        "automatically_indexed": False,
        "note": "Paid online diagnostics/service guide. Not an acquired PDF or verified full "
        "workshop manual. Exact engine coverage and RAG rights require publisher confirmation.",
    },
    {
        "id": "kfz_golf_plus_cffb_engine_manual",
        "publisher": "KFZ-Verlag",
        "url": "https://www.kfz-verlag.de/"
        "golf-plus-2009-2014-dieselmotor-reparaturanleitung-ebook/p-13349.html",
        "applicability": "Publisher explicitly lists Golf Plus 2009-2014 and CFFB among "
        "EA189 Gen II engine variants; exact vehicle build not independently verified",
        "license_status": "restricted",
        "verification_status": "publisher_listing_and_public_preview_checked",
        "automatically_indexed": False,
        "note": "418-page German workshop engine manual, paid PDF. Only the public index "
        "preview was acquired. Paid PDF advertises copy protection; no RAG license obtained.",
    },
    {
        "id": "tec_golf_plus_cffb_fuel_supply",
        "publisher": "TEC VERLAG",
        "url": "https://www.originalanleitungen.de/"
        "vw-golf-6-plus-08-14-reparaturleitfaden-kraftstoffversorgung-dieselmotoren",
        "applicability": "Publisher lists Golf Plus 2009 onward and explicitly includes CFFB",
        "license_status": "restricted",
        "verification_status": "publisher_listing_and_public_preview_checked",
        "automatically_indexed": False,
        "note": "70-page German fuel-supply workshop volume, paid PDF. The four-page "
        "public preview is an older edition; it is not the complete book. No RAG permission.",
    },
    {
        "id": "laser_5130_timing_tool_instructions",
        "publisher": "Laser Tools",
        "url": "https://www.lasertools.co.uk/items/pdf/products/5130_Instructions.pdf",
        "applicability": "Tool instructions list CFFB and Golf Plus 2009-2014 in separate "
        "application tables; exact installed configuration still requires checking",
        "license_status": "unknown",
        "verification_status": "publisher_download_verified",
        "automatically_indexed": False,
        "note": "Five-page English tool-use guide acquired for reference. Not a diagnostic "
        "or complete timing-belt workshop manual. No RAG permission established.",
    },
    {
        "id": "ross_tech",
        "publisher": "Ross-Tech LLC",
        "url": "https://wiki.ross-tech.com/wiki/index.php/Copyright",
        "applicability": "VW/Audi diagnostic references; exact vehicle applicability varies",
        "license_status": "restricted",
        "verification_status": "permission_not_obtained",
        "automatically_indexed": False,
        "note": "Reproduction/mirroring requires prior written permission.",
    },
    {
        "id": "sae_obd_reference",
        "publisher": "SAE International",
        "url": "https://saemobilus.sae.org/standards/j2012_201612-diagnostic-trouble-code-definitions",
        "applicability": "Generic OBD concepts only",
        "license_status": "unknown",
        "verification_status": "indexing_permission_not_obtained",
        "automatically_indexed": False,
        "note": "No third-party DTC catalog copied; use internal generic demonstration text.",
    },
    {
        "id": "user_supplied_vw_workshop_volumes",
        "publisher": "Volkswagen AG; copies supplied by project owner",
        "url": None,
        "applicability": "Brake System 05.2012 for Golf/Golf Plus 2009 onward (144 pages); "
        "0A4 gearbox 04.2010 for Golf/Golf Plus/Passat (319 pages). "
        "Installed variants unconfirmed.",
        "license_status": "authorized",
        "verification_status": "source_and_readability_reviewed_for_private_learning",
        "automatically_indexed": False,
        "note": "Owner-directed private processing, not a publisher redistribution license. "
        "Eight PDF parts / 686 text chunks ingested. Embeddings pending. "
        "Actual titles and original physical page positions retained.",
    },
    {
        "id": "ifixit_related_volkswagen_learning_guides",
        "publisher": "iFixit community",
        "url": "https://www.ifixit.com/Device/Volkswagen_Jetta",
        "applicability": "Jetta 2005-2011 cabin filter, Jetta 2009 key fob, Jetta 2008 radio, "
        "Passat 2013 rear indicator; related Volkswagen learning references",
        "license_status": "authorized",
        "verification_status": "source_and_completeness_reviewed_for_learning",
        "automatically_indexed": False,
        "note": "Four complete guides / 21 pages / 22 chunks privately ingested under "
        "CC BY-NC-SA 3.0 with attribution. Actual source vehicles preserved. "
        "No Golf Plus fitment claim, model training or embedding call.",
    },
    {
        "id": "ifixit_vw_component_gap_guides",
        "publisher": "iFixit community",
        "url": "https://www.ifixit.com/Device/Volkswagen_Jetta",
        "applicability": "Golf 1999-2004, Jetta 2002/2011-2018 and Passat 2001-2005; "
        "alternator, blower resistor, mirror, wipers, air filter, rain tray, camshaft sensor "
        "and power-window module",
        "license_status": "authorized",
        "verification_status": "source_and_completeness_reviewed_for_learning",
        "automatically_indexed": False,
        "note": "Eight complete component guides / 50 PDF pages / 52 text chunks ingested "
        "under CC BY-NC-SA 3.0 with attribution. Actual source models/years retained. "
        "No full-system coverage, Golf Plus fitment verification or embedding generation. "
        "The rain-tray PDF includes one verified blank final page.",
    },
    {
        "id": "vw_system_manuals_private_learning",
        "publisher": "Volkswagen AG; publicly hosted third-party copies",
        "url": "https://vwts.ru/vw_golf6_5k.html",
        "applicability": "SSP 403 uses the Tiguan/CBAB 2.0 TDI example; Golf VII 2015 "
        "suspension/steering and interior/airbags; Golf VI wiring diagrams and locations. "
        "Related-vehicle learning references, not verified Golf Plus fitment.",
        "license_status": "authorized",
        "verification_status": "source_and_readability_reviewed_for_private_learning",
        "automatically_indexed": False,
        "note": "Owner explicitly requested private ingestion. Five source PDFs / 1835 pages "
        "/ 22 stored parts / 2906 text chunks. Copyright notices and source identity retained; "
        "no publisher redistribution license asserted. No password/copy restriction bypassed. "
        "Public VWTS copies replaced login/403-blocked links. Embeddings pending.",
    },
    {
        "id": "ifixit_vw_golf_guides",
        "publisher": "iFixit community",
        "url": "https://www.ifixit.com/Device/Volkswagen_Golf",
        "applicability": "Community guides for Golf 2006, Golf 2008-2013 and Golf 2010-2013; "
        "not verified Golf Plus/CFFB procedures",
        "license_status": "authorized",
        "verification_status": "acquired_golf_plus_fitment_unverified",
        "automatically_indexed": False,
        "note": "Four complete community guides acquired under CC BY-NC-SA 3.0 for private "
        "noncommercial use, with attribution retained. No model training/fine-tuning. "
        "Uploaded OEM attachments are excluded. Text ingested; vectors/review pending.",
    },
]

# This catalogue contains acquisition candidates, never retrieval evidence.
existing_ids = {source["id"] for source in SOURCES}
for candidate in json.loads(Path(__file__).with_name("candidate_manuals.json").read_text("utf-8")):
    if candidate["id"] not in existing_ids:
        SOURCES.append(
            {
                **candidate,
                "verification_status": "candidate_not_acquired_or_verified",
                "automatically_indexed": False,
            }
        )
        existing_ids.add(candidate["id"])


# Acquisition registry only: this does not change indexed documents, retrieval
# filters, embeddings, or the PostgreSQL/pgvector architecture.
DOCUMENTATION_TARGET = {
    **MVP_IDENTITY,
    "gearbox_code": None,
    "pr_codes": None,
}

PRIMARY_SOURCES = {
    "volkswagen_erwin": (
        "Volkswagen erWin",
        "Workshop, wiring, maintenance and technical information",
        "Publisher portal and terms checked; exact vehicle documents not acquired",
        "Restricted access; indexing rights not established",
    ),
    "volkswagen_owners": (
        "Volkswagen owner documentation",
        "Owner manual and warning-light guidance",
        "Publisher route checked; pre-2018 vehicles require retailer assistance",
        "Copyrighted; indexing permission not established",
    ),
    "ross_tech": (
        "Ross-Tech Wiki",
        "VAG diagnostic and DTC reference",
        "Publisher copyright checked; individual ECU/engine applicability unverified",
        "All rights reserved; prior written permission required for reproduction/mirroring",
    ),
    "sae_obd_reference": (
        "SAE J2012 (2016 edition)",
        "Authorized publisher OBD-II DTC reference",
        "Publisher scope listing checked; not an acquired standards document",
        "Licensed publication; local indexing rights not established",
    ),
}

for source in SOURCES:
    source.setdefault("source_name", source["id"].replace("_", " "))
    source.setdefault("document_type", "Candidate technical reference; review required")
    source.setdefault("applicable_vehicle", source.get("applicability", "Unverified"))
    source.setdefault(
        "applicable_engine", "Unverified; do not assume 2.0 TDI variant compatibility"
    )
    source.setdefault("local_indexing_permission", source["id"] == "internal_demo")
    source["registry_review_date"] = "2026-11-05"
    if source["id"] in PRIMARY_SOURCES:
        name, document_type, verification, license_status = PRIMARY_SOURCES[source["id"]]
        source.update(
            source_name=name,
            document_type=document_type,
            applicable_vehicle=(
                f"Target: Volkswagen Golf Plus {MVP_IDENTITY['model_year']} "
                "diesel/manual; coverage unverified"
            ),
            applicable_engine=(
                "Target: 2.0 TDI, owner-reported CFFB; exact document coverage unverified"
            ),
            verification_status=verification,
            license_status=license_status,
            local_indexing_permission=False,
        )
    if source["id"] == "volkswagen_owners":
        source["applicability"] = (
            "Pre-2018 vehicles: request correct owner manual from Volkswagen retailer"
        )
    if source["id"] in {"vw_system_manuals_private_learning", "user_supplied_vw_workshop_volumes"}:
        # A project owner's request alone does not establish a publisher's license.
        source["license_status"] = "publisher_indexing_permission_not_verified"
