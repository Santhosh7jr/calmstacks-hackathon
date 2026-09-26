from __future__ import annotations

from io import BytesIO
import zipfile
import xml.etree.ElementTree as ET
from typing import Any

from ..models import Finding
from ..scoring import healthy_assessment, make_recovery


def analyze_zip(data: bytes, is_docx: bool = False) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    details: dict[str, Any] = {}
    required = {"[Content_Types].xml", "word/document.xml"} if is_docx else set()

    try:
        with zipfile.ZipFile(BytesIO(data), "r") as archive:
            entries = archive.infolist()
            total_uncompressed = sum(max(0, item.file_size) for item in entries)
            total_compressed = sum(max(0, item.compress_size) for item in entries)
            bad_entry = archive.testzip()
            names = set(archive.namelist())
            missing = sorted(required - names)

            details.update({
                "entries": len(entries),
                "firstCorruptEntry": bad_entry,
                "compressedSize": total_compressed,
                "uncompressedSize": total_uncompressed,
            })

            if missing:
                findings.append(Finding(
                    code="DOCX_REQUIRED_PART_MISSING",
                    severity="high",
                    message="Required DOCX package parts are missing.",
                    evidence={"missing": missing},
                ))

            if bad_entry:
                bad_size = next((item.file_size for item in entries if item.filename == bad_entry), 0)
                affected = (bad_size / total_uncompressed * 100.0) if total_uncompressed else 100.0
                findings.append(Finding(
                    code="ZIP_ENTRY_CRC_FAILURE",
                    severity="high",
                    message="An archive member failed CRC validation.",
                    evidence={"entry": bad_entry, "entryUncompressedBytes": bad_size},
                ))
            else:
                affected = 0.0

            if is_docx:
                try:
                    document_xml = archive.read("word/document.xml")
                    content_types_xml = archive.read("[Content_Types].xml")
                    root = ET.fromstring(document_xml)
                    ET.fromstring(content_types_xml)
                    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                    text_nodes = root.findall(".//w:t", namespaces)
                    details.update({
                        "paragraphs": len(root.findall(".//w:p", namespaces)),
                        "tables": len(root.findall(".//w:tbl", namespaces)),
                        "textCharacters": sum(len(node.text or "") for node in text_nodes),
                        "packageEntries": len(names),
                    })
                except (KeyError, ET.ParseError, OSError) as exc:
                    findings.append(Finding(
                        code="DOCX_XML_CORRUPTION",
                        severity="high",
                        message=str(exc),
                    ))
                    xml_size = 0
                    try:
                        xml_size = len(archive.read("word/document.xml"))
                    except Exception:
                        pass
                    affected = max(affected, (xml_size / total_uncompressed * 100.0) if total_uncompressed else 100.0)

            if not findings:
                recovery = healthy_assessment()
                return {
                    "status": "healthy",
                    "corrupted": False,
                    "signatureValid": True,
                    "details": details,
                    "assessment": {
                        "classification": "none",
                        "corruptionPercent": 0.0,
                        "recovery": {
                        "corruptionPercent": recovery.corruption_percent,
                        "recoverablePercent": recovery.recoverable_percent,
                        "unrecoverablePercent": recovery.unrecoverable_percent,
                        "confidence": recovery.confidence,
                        "basis": recovery.basis,
                    },
                        "findings": [],
                        "regions": [],
                    },
                }, findings

    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        findings.append(Finding(
            code="ZIP_CONTAINER_FAILURE",
            severity="high",
            message=str(exc),
        ))
        details["error"] = str(exc)
        affected = 100.0

    # If a CRC/XML member is damaged, the rest of the archive remains
    # independently recoverable. The damaged member itself is not byte-exactly
    # recoverable from this file without an external source.
    recoverable = max(0.0, 100.0 - affected)
    unrecoverable = affected
    recovery = make_recovery(
        corruption_percent=affected,
        recoverable_percent=recoverable,
        unrecoverable_percent=unrecoverable,
        confidence="high" if affected < 100 else "medium",
        basis=[
            "Archive members are assessed independently where the ZIP container remains readable.",
            "CRC/XML failures identify damaged members but cannot recreate their missing bytes.",
        ],
    )
    return {
        "status": "corrupted",
        "corrupted": True,
        "signatureValid": True,
        "details": details,
        "assessment": {
            "classification": "confirmed",
            "corruptionPercent": recovery.corruption_percent,
            "recovery": {
                        "corruptionPercent": recovery.corruption_percent,
                        "recoverablePercent": recovery.recoverable_percent,
                        "unrecoverablePercent": recovery.unrecoverable_percent,
                        "confidence": recovery.confidence,
                        "basis": recovery.basis,
                    },
            "findings": [f.__dict__ for f in findings],
            "regions": [],
        },
    }, findings
