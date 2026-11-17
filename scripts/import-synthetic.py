#!/usr/bin/env python3
"""Submit a synthetic proposal through the same limited API used by importers."""

import os
import sys

import httpx

base = os.environ["CRM_URL"].rstrip("/") + "/api/v1/workspaces/" + os.environ["CRM_WORKSPACE"]
token = os.environ["CRM_AGENT_TOKEN"]
with httpx.Client(headers={"Authorization": "Bearer " + token}, timeout=20) as client:
    source = client.post(
        base + "/sources",
        json={"name": "Синтетический демонстрационный импорт", "reference": "synthetic://demo-v1"},
    )
    source.raise_for_status()
    result = client.post(
        base + "/suggestions",
        json={
            "operation": "create_person",
            "source_id": source.json()["id"],
            "job_key": sys.argv[1] if len(sys.argv) > 1 else "synthetic-demo-v1",
            "record_key": "person-001",
            "confidence": 90,
            "payload": {
                "display_name": "Демо Специалист",
                "city": "Уфа",
                "profession": "Стоматолог",
                "tags": ["Медицина"],
                "notes": "Полностью синтетические сведения для проверки AI Inbox.",
            },
        },
    )
    result.raise_for_status()
    print(result.json())
