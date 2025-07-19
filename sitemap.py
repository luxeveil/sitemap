import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

SHOPIFY_DOMAIN = "theluxeveil.com"
STOREFRONT_TOKEN = os.getenv("STOREFRONT_TOKEN")
STATIC_URL_JSON = "https://raw.githubusercontent.com/luxeveil/sitemap/refs/heads/main/static.json"

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"


def fetch_products_from_shopify():
    url = f"https://{SHOPIFY_DOMAIN}/api/2023-07/graphql.json"
    headers = {
        "X-Shopify-Storefront-Access-Token": STOREFRONT_TOKEN,
        "Content-Type": "application/json",
    }
    query = """
    {
      products(first: 250) {
        edges {
          node {
            handle
            images(first: 10) {
              edges {
                node {
                  originalSrc
                  altText
                }
              }
            }
          }
        }
      }
    }
    """
    response = requests.post(url, json={"query": query}, headers=headers)
    data = response.json()
    products = []

    for edge in data["data"]["products"]["edges"]:
        product = edge["node"]
        product_url = f"https://{SHOPIFY_DOMAIN}/products/{product['handle']}"
        images = []

        for img in product["images"]["edges"]:
            node = img["node"]
            images.append({
                "src": node["originalSrc"],
                "title": node["altText"] or "Product Image"
            })

        products.append({
            "loc": product_url,
            "priority": 0.8,
            "changefreq": "weekly",
            "images": images
        })

    return products


def fetch_collections_from_shopify():
    url = f"https://{SHOPIFY_DOMAIN}/api/2023-07/graphql.json"
    headers = {
        "X-Shopify-Storefront-Access-Token": STOREFRONT_TOKEN,
        "Content-Type": "application/json",
    }
    query = """
    {
      collections(first: 100) {
        edges {
          node {
            handle
          }
        }
      }
    }
    """
    response = requests.post(url, json={"query": query}, headers=headers)
    data = response.json()
    collections = []

    for edge in data["data"]["collections"]["edges"]:
        handle = edge["node"]["handle"]
        collections.append({
            "loc": f"https://{SHOPIFY_DOMAIN}/collections/{handle}",
            "priority": 0.9,
            "changefreq": "weekly"
        })

    return collections


def fetch_static_urls():
    try:
        response = requests.get(STATIC_URL_JSON)
        response.raise_for_status()
        static_urls = response.json()

        # Set default priority and changefreq if missing
        for entry in static_urls:
            entry.setdefault("priority", 0.3)
            entry.setdefault("changefreq", "monthly")

        return static_urls

    except Exception as e:
        print("Failed to fetch static URLs:", e)
        return []


def build_url_element(entry):
    url_el = ET.Element("url")
    ET.SubElement(url_el, "loc").text = entry["loc"]
    ET.SubElement(url_el, "priority").text = str(entry.get("priority", 0.5))
    ET.SubElement(url_el, "changefreq").text = entry.get("changefreq", "monthly")

    for image in entry.get("images", []):
        img_el = ET.SubElement(url_el, f"{{{IMAGE_NS}}}image")
        ET.SubElement(img_el, f"{{{IMAGE_NS}}}loc").text = image["src"]
        ET.SubElement(img_el, f"{{{IMAGE_NS}}}title").text = image["title"]

    return url_el


def generate_sitemap_xml(products, collections, static_pages):
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("image", IMAGE_NS)
    urlset = ET.Element("urlset", {
        "xmlns": SITEMAP_NS,
        "xmlns:image": IMAGE_NS
    })

    for entry in static_pages + collections + products:
        urlset.append(build_url_element(entry))

    rough_string = ET.tostring(urlset, "utf-8")
    print(rough_string)
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def write_sitemap_file(xml_content, filename="sitemap.xml"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"Sitemap written to {filename}")


def main():
    print("Fetching static URLs...")
    static_urls = fetch_static_urls()

    print("Fetching collections from Shopify...")
    collections = fetch_collections_from_shopify()

    print("Fetching products from Shopify...")
    products = fetch_products_from_shopify()

    print("Generating sitemap...")
    sitemap_xml = generate_sitemap_xml(products, collections, static_urls)

    print("Writing sitemap.xml...")
    write_sitemap_file(sitemap_xml)


if __name__ == "__main__":
    main()
