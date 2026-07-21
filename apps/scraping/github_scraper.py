import os

import requests

GITHUB_API = "https://api.github.com/search/code"


def search_kicad_files(query="extension:kicad_pcb", per_page=5):
    headers = {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
    }

    params = {
        "q": query,
        "per_page": per_page,
    }

    response = requests.get(GITHUB_API, headers=headers, params=params)
    response.raise_for_status()

    return response.json()["items"]


def download_file(download_url, output_path):
    response = requests.get(download_url)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)


if __name__ == "__main__":
    results = search_kicad_files()

    os.makedirs("data/raw", exist_ok=True)

    for i, item in enumerate(results):
        url = item["html_url"]
        raw_url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        output = f"data/raw/file_{i}.kicad_pcb"

        download_file(raw_url, output)
        print(f"Downloaded: {output}")
