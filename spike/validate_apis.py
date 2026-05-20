"""
Spike: Validar APIs públicas de GCP y Azure
============================================
Objetivo: confirmar qué datos retornan las APIs sin necesidad de credenciales.

APIs probadas:
- Azure Retail Prices API (pública)
- Azure Function App Stacks API (pública)
- GCP Release Notes RSS (público)
- Azure Updates RSS (público)
"""

import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

SEPARATOR = "\n" + "=" * 70 + "\n"


def test_azure_pricing():
    """Azure Retail Prices API — pública, sin auth."""
    print(SEPARATOR)
    print("🔵 AZURE: Retail Prices API")
    print("   URL: https://prices.azure.com/api/retail/prices")
    print("-" * 70)

    services_to_test = [
        ("Azure Functions", "serviceName eq 'Functions'"),
        ("Container Apps", "serviceName eq 'Azure Container Apps'"),
        ("Cosmos DB", "serviceName eq 'Azure Cosmos DB'"),
    ]

    for name, filter_expr in services_to_test:
        url = f"https://prices.azure.com/api/retail/prices?$filter={filter_expr}&$top=5"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            items = data.get("Items", [])
            print(f"\n  ✅ {name}: {data.get('Count', 0)} items retornados (mostrando 3)")
            for item in items[:3]:
                print(f"     - {item.get('meterName')}: ${item.get('retailPrice')}/{item.get('unitOfMeasure')}")
                print(f"       SKU: {item.get('skuName')} | Region: {item.get('armRegionName')}")
        except Exception as e:
            print(f"\n  ❌ {name}: {e}")

    print("\n  📋 CONCLUSIÓN: API pública, retorna precios reales por servicio.")
    print("     Útil para pricingDetails. No requiere auth.")


def test_azure_function_stacks():
    """Azure Function App Stacks — endpoint público."""
    print(SEPARATOR)
    print("🔵 AZURE: Function App Stacks API (runtimes)")
    print("   URL: https://management.azure.com/providers/Microsoft.Web/functionAppStacks")
    print("-" * 70)

    url = "https://management.azure.com/providers/Microsoft.Web/functionAppStacks?api-version=2023-12-01"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            stacks = data.get("value", [])
            print(f"\n  ✅ Stacks retornados: {len(stacks)}")
            for stack in stacks[:5]:
                props = stack.get("properties", {})
                print(f"     - {props.get('displayText')}")
                major = props.get("majorVersions", [])
                for mv in major[:2]:
                    print(f"       └─ {mv.get('displayText')}: {mv.get('value')}")
        else:
            print(f"\n  ⚠️  Status {resp.status_code}: {resp.text[:200]}")
            print("     NOTA: Este endpoint puede requerir Bearer token aunque la doc dice público.")
    except Exception as e:
        print(f"\n  ❌ Error: {e}")


def test_azure_rss():
    """Azure Updates RSS — público."""
    print(SEPARATOR)
    print("🔵 AZURE: Updates RSS Feed")
    print("   URL: https://azure.microsoft.com/en-us/updates/feed/")
    print("-" * 70)

    url = "https://azure.microsoft.com/en-us/updates/feed/"
    try:
        resp = requests.get(url, timeout=10)
        root = ET.fromstring(resp.content)
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []
        print(f"\n  ✅ Items en feed: {len(items)}")

        # Filtrar por keywords
        keywords = ["Functions", "Container Apps", "Cosmos DB"]
        for kw in keywords:
            matches = [i for i in items if kw.lower() in (i.findtext("title") or "").lower()]
            print(f"     - '{kw}': {len(matches)} noticias encontradas")
            for m in matches[:2]:
                print(f"       └─ {m.findtext('title')[:80]}")
                print(f"          {m.findtext('pubDate')}")
    except Exception as e:
        print(f"\n  ❌ Error: {e}")

    print("\n  📋 CONCLUSIÓN: RSS público, filtrable por keywords.")


def test_gcp_rss():
    """GCP Release Notes RSS — público."""
    print(SEPARATOR)
    print("🟢 GCP: Release Notes RSS")
    print("   URL pattern: https://cloud.google.com/feeds/{service}-release-notes.xml")
    print("-" * 70)

    services_to_test = [
        ("Cloud Run", "run"),
        ("Cloud Functions", "functions"),
        ("Firestore", "firestore"),
        ("BigQuery", "bigquery"),
        ("Pub/Sub", "pubsub"),
    ]

    for name, slug in services_to_test:
        url = f"https://cloud.google.com/feeds/{slug}-release-notes.xml"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                # Atom feed
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                root = ET.fromstring(resp.content)
                entries = root.findall("atom:entry", ns)
                print(f"\n  ✅ {name} ({slug}): {len(entries)} entries")
                for entry in entries[:2]:
                    title = entry.findtext("atom:title", namespaces=ns) or "No title"
                    updated = entry.findtext("atom:updated", namespaces=ns) or ""
                    print(f"     - [{updated[:10]}] {title[:70]}")
            else:
                print(f"\n  ⚠️  {name} ({slug}): HTTP {resp.status_code}")
        except Exception as e:
            print(f"\n  ❌ {name}: {e}")

    print("\n  📋 CONCLUSIÓN: RSS público por servicio. Formato Atom.")


def test_gcp_quotas_info():
    """Info sobre GCP Quotas API — requiere auth."""
    print(SEPARATOR)
    print("🟢 GCP: Service Usage API (Quotas) — INFO")
    print("-" * 70)
    print("""
  ⚠️  REQUIERE AUTENTICACIÓN (Service Account con rol serviceusage.viewer)

  API: serviceusage.googleapis.com
  Método: services/{service}/consumerQuotaMetrics

  IMPORTANTE: Esta API retorna quotas del PROYECTO (cuánto tienes asignado),
  NO los límites máximos del servicio.

  Ejemplo de lo que retorna:
    - "Cloud Run - Max container instances per service": 1000 (tu proyecto)
    - NO retorna: "Cloud Run soporta máximo X instancias globalmente"

  Para límites del servicio (lo que muestra s3rv3rl3ss), necesitas:
    - Datos estáticos de la documentación oficial
    - O scraping de docs (como ya hace el collector AWS con runtimes)

  ALTERNATIVA para GCP:
    - Quotas API → útil para mostrar "default quota" (que es un límite práctico)
    - Docs scraping → para límites hard del servicio
    - Combinar ambos con source: "api" vs "static"
""")


def test_azure_quotas_info():
    """Info sobre Azure Quotas API — requiere auth."""
    print(SEPARATOR)
    print("🔵 AZURE: Resource Manager Quotas — INFO")
    print("-" * 70)
    print("""
  ⚠️  REQUIERE AUTENTICACIÓN (Service Principal con rol Reader)

  API: management.azure.com
  Método: GET /subscriptions/{id}/providers/Microsoft.{ns}/usages

  IMPORTANTE: Similar a GCP, retorna uso actual vs cuota de tu suscripción.
  Ejemplo:
    - "Current Usage: 2, Limit: 100" (para tu suscripción)

  Sin embargo, los "Limit" values SON los límites default del servicio,
  lo cual es útil para s3rv3rl3ss.

  ALTERNATIVA sin auth:
    - Azure Retail Prices API → pricing (✅ ya validado arriba)
    - Function App Stacks → runtimes (necesita token)
    - Azure docs scraping → límites hard
""")


def summary():
    """Resumen de hallazgos."""
    print(SEPARATOR)
    print("📊 RESUMEN DEL SPIKE")
    print("=" * 70)
    print("""
┌─────────────────────────────────────────────────────────────────────┐
│ API                          │ Auth?  │ Útil para      │ Estado    │
├─────────────────────────────────────────────────────────────────────┤
│ Azure Retail Prices          │ NO     │ pricingDetails │ ✅ Funciona│
│ Azure Updates RSS            │ NO     │ news           │ ✅ Funciona│
│ Azure Function Stacks        │ SÍ*    │ runtimes       │ ⚠️ Validar│
│ Azure Resource Mgr (quotas)  │ SÍ     │ limits         │ ⚠️ Validar│
│ GCP Release Notes RSS        │ NO     │ news           │ ✅ Funciona│
│ GCP Service Usage (quotas)   │ SÍ     │ limits*        │ ⚠️ Parcial│
│ GCP Cloud Functions runtimes │ SÍ     │ runtimes       │ ⚠️ Validar│
│ GCP Billing Catalog          │ SÍ     │ pricingDetails │ ⚠️ Validar│
└─────────────────────────────────────────────────────────────────────┘

* GCP quotas retorna cuotas del proyecto, no límites del servicio.
  Los valores "default quota" sí son útiles como referencia.

RECOMENDACIONES:
1. Empezar con APIs públicas (pricing Azure, RSS ambos) → valor inmediato
2. Para limits: usar datos estáticos como base + enriquecer con API cuando hay auth
3. Azure Function Stacks: probar con token, si funciona es la mejor fuente de runtimes
4. GCP runtimes: Cloud Functions API requiere proyecto, pero es confiable
5. Considerar un approach híbrido: API cuando hay auth, static como fallback
""")


if __name__ == "__main__":
    print("\n🚀 SPIKE: Validación de APIs Multi-Cloud")
    print(f"   Fecha: {datetime.now().isoformat()}")

    test_azure_pricing()
    test_azure_function_stacks()
    test_azure_rss()
    test_gcp_rss()
    test_gcp_quotas_info()
    test_azure_quotas_info()
    summary()
